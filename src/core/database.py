from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from src.core.config import settings

# Async Engine (echo=True prints raw SQL queries)
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DATABASE_ECHO,
    future=True,
)

# Async Session Factory
AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)

class Base(AsyncAttrs, DeclarativeBase):
    '''Base declarative class with async relationship loading attributes.'''
    pass

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    '''FastAPI Dependency providing an async database session.'''
    async with AsyncSessionFactory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
