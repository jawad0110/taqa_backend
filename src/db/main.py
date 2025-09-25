import logging
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, create_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from src.config import Config

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

from sqlalchemy.ext.asyncio import create_async_engine

async_engine = create_async_engine(
    Config.DATABASE_URL,
    echo=False,
    future=True,
    pool_size=10,
    max_overflow=20,
    pool_timeout=60
)


async def init_db() -> None:
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncSession: # type: ignore
    Session = sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with Session() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Session error: {e}")
            raise
