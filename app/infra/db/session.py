from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.application_config import settings
from app.infra.db.base import Base


connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def seed_initial_data() -> None:
    from app.domains.control_contract.infrastructure.conveyor_repository import ConveyorRepository

    db = SessionLocal()
    try:
        ConveyorRepository(db).ensure_container_board("container-01")
        ConveyorRepository(db).ensure_straight_board("straight-01")
    finally:
        db.close()
