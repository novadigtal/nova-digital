from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel, EmailStr, Field
from core import db, BaseDocument, now_iso

router = APIRouter(prefix="/api")


class ContactMessage(BaseDocument):
    name: str
    email: EmailStr
    message: str
    created_at: str = Field(default_factory=now_iso)


class ContactIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    message: str = Field(min_length=1, max_length=4000)


class Review(BaseDocument):
    name: str
    rating: int
    text: str
    product_slug: Optional[str] = None
    approved: bool = False
    created_at: str = Field(default_factory=now_iso)


class ReviewIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    rating: int = Field(ge=1, le=5)
    text: str = Field(min_length=3, max_length=1500)
    product_slug: Optional[str] = None


class NewsletterIn(BaseModel):
    email: EmailStr


@router.get("/")
async def root():
    return {"message": "NOVA DIGITAL API"}


@router.post("/contact")
async def create_contact(payload: ContactIn):
    res = await db.contact_messages.insert_one(ContactMessage(**payload.model_dump()).to_mongo())
    return {"ok": True, "id": str(res.inserted_id)}


@router.post("/newsletter")
async def subscribe(payload: NewsletterIn):
    await db.subscribers.update_one({"email": payload.email.lower()},
                                    {"$setOnInsert": {"email": payload.email.lower(), "created_at": now_iso()}},
                                    upsert=True)
    return {"ok": True}


@router.get("/reviews")
async def list_reviews(product: Optional[str] = None):
    q = {"approved": True}
    if product:
        q["product_slug"] = product
    docs = await db.reviews.find(q).sort("created_at", -1).to_list(100)
    return [Review.from_mongo(d).model_dump(include={"id", "name", "rating", "text", "product_slug", "created_at"}) for d in docs]


@router.post("/reviews")
async def submit_review(payload: ReviewIn):
    await db.reviews.insert_one(Review(**payload.model_dump()).to_mongo())
    return {"ok": True, "pending": True}
