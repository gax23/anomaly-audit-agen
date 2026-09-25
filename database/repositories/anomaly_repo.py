from typing import Tuple, List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from database.models import AnomalyModel

class AnomalyRepository:
    """Repositorio para gestionar anomalías."""
    
    async def create(self, session: AsyncSession, anomaly_data: dict) -> AnomalyModel:
        """Crea una nueva anomalía."""
        anomaly = AnomalyModel(**anomaly_data)
        session.add(anomaly)
        await session.flush()
        return anomaly
        
    async def get_by_id(self, session: AsyncSession, anomaly_id: str) -> Optional[AnomalyModel]:
        """Obtiene una anomalía por su ID."""
        stmt = select(AnomalyModel).where(AnomalyModel.id == anomaly_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
        
    async def get_paginated(
        self, session: AsyncSession, page: int = 1, page_size: int = 50,
        severity: Optional[str] = None, status: Optional[str] = None,
        date_from: Optional[datetime] = None, date_to: Optional[datetime] = None
    ) -> Tuple[List[AnomalyModel], int]:
        """Obtiene anomalías paginadas con filtros."""
        stmt = select(AnomalyModel)
        count_stmt = select(func.count()).select_from(AnomalyModel)
        
        if severity:
            stmt = stmt.where(AnomalyModel.severity == severity)
            count_stmt = count_stmt.where(AnomalyModel.severity == severity)
        if status:
            stmt = stmt.where(AnomalyModel.status == status)
            count_stmt = count_stmt.where(AnomalyModel.status == status)
        if date_from:
            stmt = stmt.where(AnomalyModel.detected_at >= date_from)
            count_stmt = count_stmt.where(AnomalyModel.detected_at >= date_from)
        if date_to:
            stmt = stmt.where(AnomalyModel.detected_at <= date_to)
            count_stmt = count_stmt.where(AnomalyModel.detected_at <= date_to)
            
        offset = (page - 1) * page_size
        stmt = stmt.limit(page_size).offset(offset)
        
        total_result = await session.execute(count_stmt)
        total = total_result.scalar_one()
        
        items_result = await session.execute(stmt)
        items = list(items_result.scalars().all())
        
        return items, total
        
    async def update_status(self, session: AsyncSession, anomaly_id: str, status: str, reviewer_id: str, notes: str) -> Optional[AnomalyModel]:
        """Actualiza el estado de una anomalía."""
        anomaly = await self.get_by_id(session, anomaly_id)
        if anomaly:
            anomaly.status = status
            anomaly.reviewer_id = reviewer_id
            anomaly.reviewer_notes = notes
            anomaly.reviewed_at = datetime.utcnow()
            await session.flush()
        return anomaly
