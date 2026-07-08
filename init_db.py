"""Inicializa o banco de dados manualmente (útil após docker compose up)."""

from sqlmodel import Session

from app.database import create_db_and_tables, engine
from app.services.family_service import ensure_family_account

if __name__ == "__main__":
    create_db_and_tables()
    with Session(engine) as session:
        ensure_family_account(session)
    print("Banco inicializado com sucesso.")
