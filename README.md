# Money Control — Backend

API REST para controle financeiro familiar compartilhado. Permite registrar despesas divididas entre membros, acompanhar contribuições ao caixa coletivo, definir limites de gasto, gerenciar pagamentos recorrentes e visualizar um dashboard mensal com saldos e sugestões de transferência.

## Sumário

- [Funcionalidades](#funcionalidades)
- [Stack](#stack)
- [Pré-requisitos](#pré-requisitos)
- [Configuração local](#configuração-local)
- [Variáveis de ambiente](#variáveis-de-ambiente)
- [Autenticação](#autenticação)
- [Conceitos do domínio](#conceitos-do-domínio)
- [API](#api)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Banco de dados](#banco-de-dados)
- [Produção](#produção)

## Funcionalidades

- **Autenticação JWT** com setup inicial da conta familiar e rate limit em login/setup
- **Membros da família** — cadastro de pessoas que participam das despesas
- **Cartões de pagamento** — vinculados a cada membro (ou ao caixa coletivo)
- **Transações** — despesas com parcelamento, divisão entre membros (splits) e edição/exclusão com escopo (parcela única, futuras ou todas)
- **Pagamentos recorrentes** — despesas fixas mensais geradas automaticamente por mês
- **Contribuições recorrentes** — valores esperados de aporte ao caixa por membro
- **Orçamento mensal** — registro da contribuição efetiva de cada membro no mês
- **Limites de gasto** — teto por categoria (e opcionalmente por membro), com alertas no dashboard
- **Dashboard mensal** — totais, gastos por categoria/cartão, progresso dos limites, saldos entre membros e sugestões de transferência

## Stack

| Tecnologia | Uso |
|---|---|
| [FastAPI](https://fastapi.tiangolo.com/) | Framework HTTP |
| [SQLModel](https://sqlmodel.tiangolo.com/) | ORM / modelos |
| [PostgreSQL](https://www.postgresql.org/) | Banco de dados |
| [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) | Configuração via `.env` |
| [python-jose](https://github.com/mpdavis/python-jose) + [bcrypt](https://github.com/pyca/bcrypt/) | JWT e hash de senha |

## Pré-requisitos

- Python 3.11+
- PostgreSQL 14+ (local ou remoto)

## Configuração local

1. Clone o repositório e entre na pasta do backend:

```bash
cd backend
```

2. Crie e ative um ambiente virtual:

```bash
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate    # Windows
```

3. Instale as dependências:

```bash
pip install -r requirements.txt
```

4. Configure o ambiente:

```bash
cp .env.example .env
```

Ajuste `DATABASE_URL` conforme seu PostgreSQL local.

5. Crie o banco (se ainda não existir):

```bash
createdb money_control
```

6. Inicie a API:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Na primeira subida, a aplicação aguarda o PostgreSQL ficar disponível, cria as tabelas, aplica migrações leves de schema e garante os registros iniciais (pagador **Família**, cartão **Caixa** e, se configurado, a conta admin).

Alternativa para inicializar o banco manualmente:

```bash
python init_db.py
```

### Documentação interativa

Em ambiente de desenvolvimento (`ENVIRONMENT=development`), a documentação fica disponível em:

- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

Em produção, `/docs`, `/redoc` e `/openapi.json` ficam desabilitados.

### Health check

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

## Variáveis de ambiente

| Variável | Padrão | Descrição |
|---|---|---|
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/money_control` | URL de conexão PostgreSQL |
| `ENVIRONMENT` | `development` | `development` ou `production` |
| `API_HOST` | `0.0.0.0` | Host do servidor |
| `API_PORT` | `8000` | Porta do servidor |
| `CORS_ORIGINS` | `http://localhost:5173` | Origens permitidas, separadas por vírgula |
| `JWT_SECRET_KEY` | *(inseguro)* | Chave para assinar tokens JWT |
| `JWT_ALGORITHM` | `HS256` | Algoritmo JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | Validade do token em minutos (24 h) |
| `LOGIN_RATE_LIMIT_ATTEMPTS` | `5` | Tentativas de login/setup por IP |
| `LOGIN_RATE_LIMIT_WINDOW_SECONDS` | `300` | Janela do rate limit em segundos |
| `INITIAL_ADMIN_EMAIL` | — | E-mail da conta criada automaticamente se o banco estiver vazio |
| `INITIAL_ADMIN_PASSWORD` | — | Senha da conta inicial (requer e-mail configurado) |

Gere uma chave segura para produção:

```bash
openssl rand -hex 32
```

## Autenticação

O fluxo usa **Bearer JWT**. Todas as rotas exceto `/auth/*` e `/health` exigem autenticação.

1. Verifique se o setup é necessário:

```http
GET /api/v1/auth/status
```

Resposta: `{ "setup_required": true }` quando não há nenhuma conta cadastrada.

2. Crie a primeira conta (apenas uma vez):

```http
POST /api/v1/auth/setup
Content-Type: application/json

{
  "email": "familia@exemplo.com",
  "password": "SenhaSegura1"
}
```

A senha deve ter no mínimo 8 caracteres, com letras e números.

3. Faça login nas próximas sessões:

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "familia@exemplo.com",
  "password": "SenhaSegura1"
}
```

4. Use o token retornado nas requisições protegidas:

```http
Authorization: Bearer <access_token>
```

5. Consulte a conta autenticada:

```http
GET /api/v1/auth/me
Authorization: Bearer <access_token>
```

Login e setup possuem **rate limit por IP** para mitigar brute force.

## Conceitos do domínio

### Conta vs. membros

- **Account** — credencial de acesso à API (e-mail/senha). Existe uma conta por instalação familiar.
- **User** — membro da família que participa das despesas e contribuições. Não possui login próprio.

### Família e Caixa

O sistema cria automaticamente:

- Pagador **Família** (`is_family: true`) — representa o caixa coletivo
- Cartão **Caixa** — usado para despesas pagas com dinheiro comum

Despesas no cartão da Família são debitadas integralmente do caixa coletivo, sem splits manuais.

### Splits (divisão de despesas)

Cada transação em cartão pessoal define quem consumiu e quanto (`splits`). A soma dos splits deve ser igual ao valor total da transação.

### Parcelamento

Transações podem ter até 48 parcelas. Cada parcela gera um registro com `current_installment` e `total_installments`. Atualizações e exclusões aceitam escopo:

- `single` — apenas a parcela atual
- `future` — parcela atual e as seguintes
- `all` — todas as parcelas

### Pagamentos e contribuições recorrentes

- **RecurringPayment** — despesa fixa (ex.: aluguel) gerada automaticamente no mês consultado
- **RecurringContribution** — valor esperado de aporte mensal de um membro ao caixa

Ao listar orçamentos ou o dashboard de um mês, as contribuições recorrentes ativas são materializadas automaticamente.

### Dashboard e acertos

O endpoint de dashboard calcula, para um mês (`YYYY-MM`):

- Total gasto, contribuições e saldo do caixa familiar
- Gastos por categoria e por cartão
- Progresso dos limites (`ok`, `warning` a partir de 80%, `exceeded` a partir de 100%)
- Saldo de cada membro (contribuição − gastos individuais − gastos no cartão de outros)
- Sugestões de transferência entre membros para equilibrar dívidas

## API

Base URL: `/api/v1`

### Autenticação (público)

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/auth/status` | Indica se o setup inicial é necessário |
| `POST` | `/auth/setup` | Cria a primeira conta |
| `POST` | `/auth/login` | Retorna token JWT |
| `GET` | `/auth/me` | Dados da conta autenticada |

### Membros

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/users` | Lista membros (Família primeiro) |
| `POST` | `/users` | Cria membro |
| `PATCH` | `/users/{user_id}` | Atualiza nome |
| `DELETE` | `/users/{user_id}` | Remove membro |

### Cartões

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/cards` | Lista cartões (`user_id`, `active_only`) |
| `POST` | `/cards` | Cria cartão para um membro |
| `PATCH` | `/cards/{card_id}` | Atualiza cartão |
| `DELETE` | `/cards/{card_id}` | Remove cartão |

### Transações

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/transactions?month_year=YYYY-MM` | Lista transações do mês |
| `POST` | `/transactions` | Cria transação (com parcelas) |
| `GET` | `/transactions/{id}` | Detalhe com splits |
| `PATCH` | `/transactions/{id}` | Atualiza (`installments_scope`, `recurring_scope`) |
| `DELETE` | `/transactions/{id}` | Remove (`all_installments`, `recurring_scope`) |

### Orçamento mensal

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/budgets?month_year=YYYY-MM` | Lista contribuições do mês |
| `POST` | `/budgets` | Registra/atualiza contribuição efetiva |
| `DELETE` | `/budgets/{budget_id}` | Remove registro |

### Limites de gasto

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/spending-limits?month_year=YYYY-MM` | Lista limites do mês |
| `POST` | `/spending-limits` | Cria ou atualiza limite por categoria |
| `PATCH` | `/spending-limits/{limit_id}` | Atualiza limite |
| `DELETE` | `/spending-limits/{limit_id}` | Remove limite |

### Pagamentos recorrentes

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/recurring-payments` | Lista pagamentos recorrentes |
| `GET` | `/recurring-payments/{id}` | Detalhe |
| `POST` | `/recurring-payments` | Cria (`month_year` opcional para gerar no mês) |
| `PATCH` | `/recurring-payments/{id}` | Atualiza |
| `DELETE` | `/recurring-payments/{id}` | Remove |

### Contribuições recorrentes

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/recurring-contributions` | Lista contribuições recorrentes |
| `GET` | `/recurring-contributions/{id}` | Detalhe |
| `POST` | `/recurring-contributions` | Cria (`month_year` opcional) |
| `PATCH` | `/recurring-contributions/{id}` | Atualiza |
| `DELETE` | `/recurring-contributions/{id}` | Remove |

### Dashboard

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/dashboard/{month_year}` | Dashboard completo do mês (`YYYY-MM`) |

## Estrutura do projeto

```
backend/
├── app/
│   ├── api/
│   │   ├── deps.py              # Dependências (autenticação)
│   │   └── routes/              # Endpoints REST
│   ├── models/                  # Tabelas SQLModel
│   ├── schemas/                 # Schemas Pydantic (request/response)
│   ├── services/                # Regras de negócio
│   ├── config.py                # Configuração via variáveis de ambiente
│   ├── database.py              # Engine, sessão e bootstrap do schema
│   └── main.py                  # Aplicação FastAPI
├── init_db.py                   # Inicialização manual do banco
├── requirements.txt
├── .env.example
└── README.md
```

## Banco de dados

### Modelo principal

```
Account          → credencial de acesso (e-mail/senha)
User             → membro da família
PaymentCard      → cartão vinculado a um User
Transaction      → despesa (com parcelas e vínculo a recorrente)
TransactionSplit → parte da despesa atribuída a um membro
MonthlyBudget    → contribuição efetiva de um membro no mês
RecurringPayment → template de despesa mensal
RecurringContribution → template de aporte mensal
RecurringPaymentSkip    → mês ignorado de um pagamento recorrente
SpendingLimit    → teto de gasto por categoria/mês
```

### Inicialização automática

Ao subir a API:

1. Aguarda conexão com o PostgreSQL (até 30 tentativas)
2. Cria tabelas ausentes via `SQLModel.metadata.create_all`
3. Aplica ajustes incrementais de schema (colunas renomeadas/removidas em versões anteriores)
4. Garante o pagador **Família** e o cartão **Caixa**
5. Cria a conta admin se `INITIAL_ADMIN_EMAIL` e `INITIAL_ADMIN_PASSWORD` estiverem definidos e não houver contas

Não há sistema de migrações formal (Alembic); mudanças de schema são tratadas de forma incremental em `database.py`.

## Produção

Checklist mínimo:

- Defina `ENVIRONMENT=production`
- Configure `JWT_SECRET_KEY` com valor forte (a aplicação recusa subir com a chave padrão em produção)
- Aponte `DATABASE_URL` para um PostgreSQL gerenciado ou dedicado
- Ajuste `CORS_ORIGINS` para a URL do frontend
- Desabilite `--reload` e use um process manager (systemd, Docker, etc.)
- Configure HTTPS na camada reversa (nginx, Caddy, load balancer)

Exemplo de start:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

Parte do ecossistema **Money Control**. Este repositório contém apenas o backend; o frontend consome a API em `/api/v1`.
