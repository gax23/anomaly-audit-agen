from typing import List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.models import TransactionModel

class TransactionRepository:
    """Repositorio para acceder a transacciones financieras."""
    
    async def create(self, session: AsyncSession, transaction_data: dict) -> TransactionModel:
        """Crea una nueva transacción."""
        transaction = TransactionModel(**transaction_data)
        session.add(transaction)
        await session.flush()
        return transaction
        
    async def get_by_id(self, session: AsyncSession, transaction_id: str) -> Optional[TransactionModel]:
        """Obtiene una transacción por su ID."""
        stmt = select(TransactionModel).where(TransactionModel.id == transaction_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
        
    async def get_by_date_range(self, session: AsyncSession, date_from: datetime, date_to: datetime, limit: int = 1000, offset: int = 0) -> List[TransactionModel]:
        """Obtiene transacciones en un rango de fechas."""
        stmt = select(TransactionModel).where(
            TransactionModel.date >= date_from,
            TransactionModel.date <= date_to
        ).limit(limit).offset(offset)
        result = await session.execute(stmt)
        return list(result.scalars().all())
        
    async def get_unprocessed(self, session: AsyncSession, limit: int = 100) -> List[TransactionModel]:
        """Obtiene transacciones que no han sido procesadas."""
        stmt = select(TransactionModel).where(TransactionModel.is_processed == False).limit(limit)
        result = await session.execute(stmt)
        return list(result.scalars().all())
        
    async def mark_as_processed(self, session: AsyncSession, transaction_id: str) -> None:
        """Marca una transacción como procesada."""
        transaction = await self.get_by_id(session, transaction_id)
        if transaction:
            transaction.is_processed = True
            await session.flush()
