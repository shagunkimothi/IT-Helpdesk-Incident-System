from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy import inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DATABASE_PATH = Path(__file__).resolve().parents[2] / "data" / "helpdesk.db"
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from . import models

    Base.metadata.create_all(bind=engine)
    migrate_incident_priority_inputs()
    seed_data()


def migrate_incident_priority_inputs() -> None:
    columns = {column["name"] for column in inspect(engine).get_columns("incidents")}
    with engine.begin() as connection:
        if "impact" not in columns:
            connection.execute(text("ALTER TABLE incidents ADD COLUMN impact VARCHAR(20)"))
        if "urgency" not in columns:
            connection.execute(text("ALTER TABLE incidents ADD COLUMN urgency VARCHAR(20)"))


def seed_data() -> None:
    from .models import Category, User

    with SessionLocal() as db:
        if db.query(User).count() == 0:
            db.add_all(
                [
                    User(name="Aisha Khan", email="aisha@example.com", role="agent"),
                    User(name="Daniel Lee", email="daniel@example.com", role="agent"),
                    User(name="Maya Patel", email="maya@example.com", role="requester"),
                ]
            )
        if db.query(Category).count() == 0:
            db.add_all(
                [
                    Category(name="Hardware"),
                    Category(name="Software"),
                    Category(name="Network"),
                    Category(name="Access"),
                ]
            )
        db.commit()
