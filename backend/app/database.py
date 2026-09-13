from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
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
    seed_data()


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
