"""
Database module for payment record persistence
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, DateTime
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _ssl_for_asyncpg(ssl_mode: str):
    """Return ssl argument for asyncpg: False when disable, True otherwise."""
    return ssl_mode.strip().lower() != "disable"


class Base(DeclarativeBase):
    """SQLAlchemy declarative base"""
    pass


class PaymentRecord(Base):
    """Payment record model"""
    
    __tablename__ = "payment_records"
    
    payment_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tx_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class APIKey(Base):
    """API Key Model"""
    
    __tablename__ = "api_keys"
    
    key: Mapped[str] = mapped_column(String(64), primary_key=True)


# Global engine and session maker
_engine = None
_async_session_maker = None


async def init_database(
    database_url: str,
    *,
    pool_size: int,
    max_overflow: int,
    pool_recycle: int,
    pool_pre_ping: bool = True,
    ssl_mode: str,
) -> None:
    """
    Initialize the database connection and create tables.
    """
    global _engine, _async_session_maker

    engine_kw = dict(
        echo=False,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_recycle=pool_recycle,
        pool_pre_ping=pool_pre_ping,
    )
    if _ssl_for_asyncpg(ssl_mode) is False:
        engine_kw["connect_args"] = {"ssl": False}

    _engine = create_async_engine(database_url, **engine_kw)

    _async_session_maker = async_sessionmaker(_engine, expire_on_commit=False)
    
    # Create tables
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def get_session() -> AsyncSession:
    """
    Get a new database session.
    
    Returns:
        AsyncSession instance
        
    Raises:
        RuntimeError: If database is not initialized
    """
    if _async_session_maker is None:
        raise RuntimeError("Database not initialized. Call init_database first.")
    return _async_session_maker()


async def get_all_api_keys() -> list[str]:
    """
    Get all active API keys from database.
    
    Returns:
        List of API key strings
    """
    from sqlalchemy import select
    async with get_session() as session:
        result = await session.execute(select(APIKey.key))
        return [row[0] for row in result.all()]


async def insert_payment_record_pending(session: AsyncSession, payment_id: str) -> PaymentRecord:
    """
    Insert a payment record with status 'pending' in the current transaction.
    Does not commit; caller must commit after settle succeeds or rollback on failure.

    Args:
        session: Active AsyncSession (transaction in progress)
        payment_id: Unique payment identifier

    Returns:
        The added PaymentRecord (tx_hash='', status='pending')
    """
    record = PaymentRecord(
        payment_id=payment_id,
        tx_hash="",
        status="pending",
    )
    session.add(record)
    await session.flush()
    return record


async def save_payment_record(
    payment_id: str,
    tx_hash: str,
    status: str,
) -> PaymentRecord:
    """
    Save a payment record to the database.
    
    Args:
        payment_id: Unique payment identifier
        tx_hash: Transaction hash
        status: Payment status (success/failed)
        
    Returns:
        The created PaymentRecord
    """
    async with get_session() as session:
        record = PaymentRecord(
            payment_id=payment_id,
            tx_hash=tx_hash,
            status=status,
        )
        session.add(record)
        await session.commit()
        await session.refresh(record)
        return record


async def get_payment_by_id(payment_id: str) -> Optional[PaymentRecord]:
    """
    Get a payment record by payment_id.
    
    Args:
        payment_id: The payment ID to look up
        
    Returns:
        PaymentRecord if found, None otherwise
    """
    async with get_session() as session:
        return await session.get(PaymentRecord, payment_id)