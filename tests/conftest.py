"""Test configuration and reusable test fixtures.

This file sets up an isolated testing environment for Codoric FastAPI E-Commerce Core:
- An in-memory SQLite database (sqlite+aiosqlite:///:memory:) that runs entirely in RAM.
- A `db_session` fixture that creates clean tables before each test and drops them afterward.
- A `client` fixture that sends asynchronous HTTP requests to our FastAPI app using httpx.
"""

from typing import AsyncGenerator
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from src.api.main import app
from src.core.database import Base, get_db

# "sqlite+aiosqlite:///:memory:" creates a database inside RAM (fast & no leftover files).
# StaticPool ensures that all connections use the exact same in-memory database instance.
# check_same_thread=False allows SQLite to be accessed across async worker threads.
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# Async session factory configured specifically for our test database engine
TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    autoflush=False,
    expire_on_commit=False,
)


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a fresh, isolated database session for each test function.

    1. Before test: create all tables (Base.metadata.create_all).
    2. During test: yield the active database session.
    3. After test: drop all tables (Base.metadata.drop_all) to leave a clean slate.
    """
    # Bước 1: Tạo toàn bộ bảng trong CSDL trước khi test bắt đầu
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Bước 2: Cung cấp session cho test function sử dụng
    async with TestingSessionLocal() as session:
        yield session

    # Bước 3: Xóa sạch toàn bộ bảng sau khi test xong (dọn dẹp dữ liệu)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide an HTTP test client connected to the FastAPI application.

    - Uses httpx.AsyncClient with ASGITransport to talk directly to FastAPI in-memory (no network port opened).
    - Overrides the get_db dependency so endpoints use the isolated in-memory test database.
    """
    # Ghi đè (override) get_db để FastAPI tự động sử dụng test db_session thay vì database thật
    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    # ASGITransport cho phép gửi request trực tiếp đến app FastAPI trong RAM mà không cần mở cổng mạng thật
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    # Dọn dẹp override để tránh ảnh hưởng đến các bài test khác
    app.dependency_overrides.clear()
