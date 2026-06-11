from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select

from app.api.deps import DbDep
from app.core.security import verify_password, create_access_token, hash_password
from app.models.orm import User


router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: DbDep):
    user = await db.scalar(select(User).where(User.email == body.email))
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    user.last_login_at = datetime.now(timezone.utc)
    db.add(user)
    await db.commit()

    token = create_access_token(subject=user.email)
    return TokenResponse(
        access_token=token,
        user={"id": str(user.id), "email": user.email, "name": user.full_name, "role": user.role},
    )


@router.post("/register", response_model=TokenResponse)
async def register(body: RegisterRequest, db: DbDep):
    existing = await db.scalar(select(User).where(User.email == body.email))
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        role="analyst",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(subject=user.email)
    return TokenResponse(
        access_token=token,
        user={"id": str(user.id), "email": user.email, "name": user.full_name, "role": user.role},
    )
