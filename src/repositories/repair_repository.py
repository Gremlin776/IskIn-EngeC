# -*- coding: utf-8 -*-
"""
Репозиторий для ремонтных работ
"""

from datetime import date
from sqlalchemy import select, func, Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.repair import (
    RepairRequest,
    RepairPhoto,
    RepairComment,
    RepairType,
)
from src.repositories.base import BaseRepository


class RepairRepository(BaseRepository[RepairRequest]):
    """Репозиторий для работы с заявками на ремонт"""

    model = RepairRequest

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_with_relations(self, id: int) -> RepairRequest | None:
        """Получить заявку с фото и комментариями"""
        result = await self.session.execute(
            select(RepairRequest)
            .options(
                selectinload(RepairRequest.photos),
                selectinload(RepairRequest.comments).selectinload(RepairComment.user),
                selectinload(RepairRequest.premise),
                selectinload(RepairRequest.repair_type),
            )
            .where(RepairRequest.id == id)
        )
        return result.scalar_one_or_none()

    async def get_by_status(
        self,
        status: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[RepairRequest]:
        """Получить заявки по статусу"""
        result = await self.session.execute(
            select(RepairRequest)
            .where(RepairRequest.status == status)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_premise(
        self,
        premise_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> list[RepairRequest]:
        """Получить заявки по помещению"""
        result = await self.session.execute(
            select(RepairRequest)
            .where(RepairRequest.premise_id == premise_id)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_user(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> list[RepairRequest]:
        """Получить заявки по пользователю"""
        result = await self.session.execute(
            select(RepairRequest)
            .where(RepairRequest.user_id == user_id)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_stats_by_status(self) -> dict[str, int]:
        """Получить статистику по статусам"""
        result = await self.session.execute(
            select(RepairRequest.status, func.count())
            .group_by(RepairRequest.status)
        )
        return {row[0]: row[1] for row in result.all()}

    async def get_stats_by_priority(self) -> dict[str, int]:
        """Получить статистику по приоритетам"""
        result = await self.session.execute(
            select(RepairRequest.priority, func.count())
            .group_by(RepairRequest.priority)
        )
        return {row[0]: row[1] for row in result.all()}

    async def add_photo(
        self,
        repair_request_id: int,
        file_path: str,
        file_name: str,
        **kwargs,
    ) -> RepairPhoto:
        """Добавить фото к заявке"""
        photo = RepairPhoto(
            repair_request_id=repair_request_id,
            file_path=file_path,
            file_name=file_name,
            **kwargs,
        )
        self.session.add(photo)
        await self.session.flush()
        await self.session.refresh(photo)
        return photo

    async def add_comment(
        self,
        repair_request_id: int,
        user_id: int,
        comment_text: str,
    ) -> RepairComment:
        """Добавить комментарий к заявке"""
        comment = RepairComment(
            repair_request_id=repair_request_id,
            user_id=user_id,
            comment_text=comment_text,
        )
        self.session.add(comment)
        await self.session.flush()
        await self.session.refresh(comment)
        return comment


class RepairTypeRepository(BaseRepository[RepairType]):
    """Репозиторий для типов ремонтов"""

    model = RepairType

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_code(self, code: str) -> RepairType | None:
        """Получить тип по коду"""
        result = await self.session.execute(
            select(RepairType).where(RepairType.code == code)
        )
        return result.scalar_one_or_none()
