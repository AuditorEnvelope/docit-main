from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.org_member import OrgMember
from app.models.user import User


@dataclass
class OrgMemberDTO:
    org_id: str
    user_id: Optional[str]
    github_username: Optional[str]
    github_user_id: Optional[int]
    role: str
    is_owner: bool
    is_active: bool
    last_synced_at: Optional[str]


class OrgMembershipService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def upsert_member(
        self,
        *,
        org_id: str,
        user: User,
        role: str = "member",
        is_owner: bool = False,
        is_active: bool = True,
    ) -> None:
        stmt = (
            insert(OrgMember)
            .values(
                org_id=org_id,
                user_id=user.id,
                github_username=user.username,
                github_user_id=user.github_id,
                role=role,
                is_owner=is_owner,
                is_active=is_active,
                last_synced_at=datetime.utcnow(),
            )
            .on_conflict_do_update(
                index_elements=[OrgMember.org_id, OrgMember.user_id],
                set_={
                    "github_username": user.username,
                    "github_user_id": user.github_id,
                    "role": role,
                    "is_owner": is_owner,
                    "is_active": is_active,
                    "last_synced_at": datetime.utcnow(),
                },
            )
        )

        await self.db.execute(stmt)

    async def list_members(self, org_id: str) -> List[OrgMemberDTO]:
        result = await self.db.execute(
            select(OrgMember).where(OrgMember.org_id == org_id, OrgMember.is_active.is_(True))
        )
        members = result.scalars().all()
        return [
            OrgMemberDTO(
                org_id=member.org_id,
                user_id=str(member.user_id) if member.user_id else None,
                github_username=member.github_username,
                github_user_id=member.github_user_id,
                role=member.role or "member",
                is_owner=member.is_owner,
                is_active=member.is_active,
                last_synced_at=member.last_synced_at.isoformat() if member.last_synced_at else None,
            )
            for member in members
        ]

    async def ensure_member(self, org_id: str, user: User) -> bool:
        result = await self.db.execute(
            select(OrgMember).where(OrgMember.org_id == org_id, OrgMember.user_id == user.id)
        )
        member = result.scalar_one_or_none()

        return bool(member and member.is_active)
