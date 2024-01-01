import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Mapped, declarative_base, relationship, sessionmaker

from settings import DB_NAME


STMT_NOW_TIMESTAMP = sa.sql.func.now()  # pylint: disable=not-callable

engine_lite = create_async_engine(f"sqlite+aiosqlite:///{DB_NAME}")
async_session = sessionmaker(  # noqa
    bind=engine_lite,
    class_=AsyncSession,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)
Base = declarative_base()  # Yes, without alembic


class BaseModel:
    __table_args__ = {"sqlite_autoincrement": True}

    def __setattr__(self, key: str, value: Any):
        if not key.startswith("_") and key not in self.__class__.__dict__:
            raise AttributeError(f"Unknown field `{self.__class__.__name__}.{key}`")

        super().__setattr__(key, value)


class User(BaseModel, Base):
    __tablename__ = "user"

    id: Mapped[int] = sa.Column(sa.INT, primary_key=True, nullable=False, unique=True, autoincrement=True)
    external_id: Mapped[int] = sa.Column(sa.BIGINT, nullable=False)
    created_at: Mapped[datetime.datetime] = sa.Column(sa.TIMESTAMP, nullable=False, server_default=STMT_NOW_TIMESTAMP)
    updated_at: Mapped[datetime.datetime] = sa.Column(sa.TIMESTAMP, nullable=False, server_default=STMT_NOW_TIMESTAMP)


class Repository(BaseModel, Base):
    __tablename__ = "repository"

    id: Mapped[int] = sa.Column(sa.INT, primary_key=True, nullable=False, unique=True, autoincrement=True)
    url: Mapped[str] = sa.Column(sa.VARCHAR(100), nullable=False, unique=True)
    short_name: Mapped[str] = sa.Column(sa.VARCHAR(50), nullable=False, unique=True)
    latest_tag: Mapped[str] = sa.Column(sa.VARCHAR(50), nullable=True)
    created_at: Mapped[datetime.datetime] = sa.Column(sa.TIMESTAMP, nullable=False, server_default=STMT_NOW_TIMESTAMP)
    updated_at: Mapped[datetime.datetime] = sa.Column(sa.TIMESTAMP, nullable=False, server_default=STMT_NOW_TIMESTAMP)


class UserRepository(BaseModel, Base):
    __tablename__ = "user_repository"

    id: Mapped[int] = sa.Column(sa.INT, primary_key=True, nullable=False, unique=True, autoincrement=True)
    user_id: Mapped[int] = sa.Column(sa.BIGINT, sa.ForeignKey("user.id"), nullable=False)
    repository_id: Mapped[int] = sa.Column(sa.BIGINT, sa.ForeignKey("repository.id"), nullable=False)
    created_at: Mapped[datetime.datetime] = sa.Column(sa.TIMESTAMP, nullable=False, server_default=STMT_NOW_TIMESTAMP)
    updated_at: Mapped[datetime.datetime] = sa.Column(sa.TIMESTAMP, nullable=False, server_default=STMT_NOW_TIMESTAMP)

    user: Mapped["User"] = relationship("User")
    repository: Mapped["Repository"] = relationship("Repository")


Base.metadata.create_all(create_engine(f"sqlite:///{DB_NAME}"))
