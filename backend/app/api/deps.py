from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db


DbDep = Annotated[AsyncSession, Depends(get_db)]


# Auth disabled — platform is open access.
# CurrentUser is kept as a type alias so all route signatures stay unchanged;
# it resolves to None and routes simply ignore it.
async def _no_auth() -> None:
    return None


CurrentUser = Annotated[None, Depends(_no_auth)]
