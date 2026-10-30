from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from core import db, oid
from auth import get_admin
from catalog import Product, CATEGORIES
from orders import Order
from content import Review, ContactMessage

router = APIRouter(prefix="/api/admin", dependencies=[Depends(get_admin)])


class ProductUpdate(BaseModel):
    name_en: Optional[str] = None
    name_ar: Optional[str] = None
    desc_en: Optional[str] = None
    desc_ar: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = Field(default=None, gt=0)
    sale_price: Optional[float] = Field(default=None, ge=0)
    featured: Optional[bool] = None
    active: Optional[bool] = None


class ProductCreate(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9-]{3,60}$")
    name_en: str
    name_ar: str
    desc_en: str
    desc_ar: str
    category: str
    price: float = Field(gt=0)
    sale_price: Optional[float] = None


@router.get("/stats")
async def stats():
    paid = await db.orders.find({"status": "paid"}, {"total": 1}).to_list(10000)
    return {
        "orders": await db.orders.count_documents({}),
        "paid_orders": len(paid),
        "revenue": round(sum(o.get("total", 0) for o in paid), 2),
        "products": await db.products.count_documents({}),
        "subscribers": await db.subscribers.count_documents({}),
        "messages": await db.contact_messages.count_documents({}),
        "pending_reviews": await db.reviews.count_documents({"approved": False}),
    }


@router.get("/products")
async def products():
    docs = await db.products.find({}).sort("sort", 1).to_list(500)
    return [Product.from_mongo(d).out() for d in docs]


@router.post("/products")
async def create_product(payload: ProductCreate):
    if payload.category not in CATEGORIES:
        raise HTTPException(400, "Invalid category")
    if await db.products.find_one({"slug": payload.slug}):
        raise HTTPException(400, "Slug already exists")
    count = await db.products.count_documents({})
    p = Product(**payload.model_dump(), image="/img/planner-cover.jpg", sort=count + 1)
    res = await db.products.insert_one(p.to_mongo())
    p.id = str(res.inserted_id)
    return p.out()


@router.patch("/products/{slug}")
async def update_product(slug: str, payload: ProductUpdate):
    data = payload.model_dump(exclude_unset=True)
    if "category" in data and data["category"] not in CATEGORIES:
        raise HTTPException(400, "Invalid category")
    if data.get("sale_price") == 0:
        data["sale_price"] = None
    res = await db.products.find_one_and_update({"slug": slug}, {"$set": data}, return_document=True)
    if not res:
        raise HTTPException(404, "Product not found")
    return Product.from_mongo(res).out()


@router.get("/orders")
async def orders():
    docs = await db.orders.find({}).sort("created_at", -1).to_list(500)
    return [Order.from_mongo(d).model_dump(exclude={"access_token"}) for d in docs]


@router.get("/reviews")
async def reviews():
    docs = await db.reviews.find({}).sort("created_at", -1).to_list(500)
    return [Review.from_mongo(d).out() for d in docs]


class ReviewModerate(BaseModel):
    approved: bool


@router.patch("/reviews/{review_id}")
async def moderate(review_id: str, payload: ReviewModerate):
    await db.reviews.update_one({"_id": oid(review_id)}, {"$set": {"approved": payload.approved}})
    return {"ok": True}


@router.delete("/reviews/{review_id}")
async def delete_review(review_id: str):
    await db.reviews.delete_one({"_id": oid(review_id)})
    return {"ok": True}


@router.get("/messages")
async def messages():
    docs = await db.contact_messages.find({}).sort("created_at", -1).to_list(500)
    return [ContactMessage.from_mongo(d).out() for d in docs]


@router.get("/subscribers")
async def subscribers() -> List[dict]:
    docs = await db.subscribers.find({}, {"_id": 0}).sort("created_at", -1).to_list(5000)
    return docs
