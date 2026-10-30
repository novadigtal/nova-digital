import os
from datetime import datetime, timezone, timedelta
import bcrypt
import jwt
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, EmailStr
from core import db, oid

router = APIRouter(prefix="/api/auth")
JWT_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(user_id: str, email: str) -> str:
    payload = {"sub": user_id, "email": email, "type": "access",
               "exp": datetime.now(timezone.utc) + timedelta(hours=8)}
    return jwt.encode(payload, os.environ["JWT_SECRET"], algorithm=JWT_ALGORITHM)


async def get_admin(request: Request) -> dict:
    auth = request.headers.get("Authorization", "")
    token = auth[7:] if auth.startswith("Bearer ") else None
    if not token:
        raise HTTPException(401, "Not authenticated")
    try:
        payload = jwt.decode(token, os.environ["JWT_SECRET"], algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Session expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")
    if payload.get("type") != "access":
        raise HTTPException(401, "Invalid token type")
    user = await db.users.find_one({"_id": oid(payload["sub"])})
    if not user or user.get("role") != "admin":
        raise HTTPException(403, "Admin only")
    return {"id": str(user["_id"]), "email": user["email"], "name": user.get("name", "Admin"), "role": "admin"}


class LoginIn(BaseModel):
    email: EmailStr
    password: str


@router.post("/login")
async def login(payload: LoginIn, request: Request):
    email = payload.email.lower()
    ip = request.client.host if request.client else "unknown"
    ident = f"{ip}:{email}"
    attempt = await db.login_attempts.find_one({"identifier": ident})
    now = datetime.now(timezone.utc)
    if attempt and attempt.get("locked_until") and datetime.fromisoformat(attempt["locked_until"]) > now:
        raise HTTPException(429, "Too many attempts. Try again in 15 minutes.")
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(payload.password, user["password_hash"]):
        count = (attempt or {}).get("count", 0) + 1
        update = {"count": count}
        if count >= 5:
            update = {"count": 0, "locked_until": (now + timedelta(minutes=15)).isoformat()}
        await db.login_attempts.update_one({"identifier": ident}, {"$set": update}, upsert=True)
        raise HTTPException(401, "Invalid email or password")
    await db.login_attempts.delete_one({"identifier": ident})
    uid = str(user["_id"])
    return {"token": create_access_token(uid, email),
            "user": {"id": uid, "email": email, "name": user.get("name", "Admin"), "role": user.get("role")}}


@router.get("/me")
async def me(admin: dict = Depends(get_admin)):
    return admin


async def seed_admin():
    await db.users.create_index("email", unique=True)
    await db.login_attempts.create_index("identifier")
    email = os.environ["ADMIN_EMAIL"].lower()
    if await db.users.find_one({"email": email}) is None:
        await db.users.insert_one({"email": email, "password_hash": hash_password(os.environ["ADMIN_PASSWORD"]),
                                   "name": "Admin", "role": "admin",
                                   "created_at": datetime.now(timezone.utc).isoformat()})
