import os
import secrets
import logging
from typing import List, Optional
import stripe
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr, Field
from core import db, BaseDocument, now_iso, oid, FILES_DIR
from catalog import get_product

router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)


def stripe_ready() -> bool:
    return bool(os.environ.get("STRIPE_SECRET_KEY")) and bool(os.environ.get("STRIPE_WEBHOOK_SECRET"))


class OrderItem(BaseModel):
    slug: str
    name_en: str
    name_ar: str
    unit_price: float


class Order(BaseDocument):
    email: EmailStr
    items: List[OrderItem]
    total: float
    currency: str = "AED"
    status: str = "pending"
    provider: str = "stripe"
    provider_session_id: Optional[str] = None
    provider_payment_id: Optional[str] = None
    access_token: str = Field(default_factory=lambda: secrets.token_urlsafe(24))
    created_at: str = Field(default_factory=now_iso)
    paid_at: Optional[str] = None


class CheckoutIn(BaseModel):
    slugs: List[str] = Field(min_length=1, max_length=20)
    email: EmailStr
    origin_url: str


@router.get("/payments/config")
async def payments_config():
    return {"enabled": stripe_ready(), "provider": "stripe", "currency": "AED"}


@router.post("/checkout")
async def checkout(payload: CheckoutIn):
    if not stripe_ready():
        raise HTTPException(503, "payments_not_configured")
    items = []
    for slug in dict.fromkeys(payload.slugs):
        p = await get_product(slug)
        items.append(OrderItem(slug=p.slug, name_en=p.name_en, name_ar=p.name_ar, unit_price=p.effective_price))
    order = Order(email=payload.email.lower(), items=items, total=round(sum(i.unit_price for i in items), 2))
    res = await db.orders.insert_one(order.to_mongo())
    order_id = str(res.inserted_id)
    stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            customer_email=order.email,
            line_items=[{"quantity": 1, "price_data": {
                "currency": "aed", "unit_amount": int(round(i.unit_price * 100)),
                "product_data": {"name": i.name_en, "metadata": {"slug": i.slug}}}} for i in items],
            metadata={"order_id": order_id},
            success_url=f"{payload.origin_url}/order/{order_id}?token={order.access_token}",
            cancel_url=f"{payload.origin_url}/checkout?cancelled=1",
        )
    except stripe.error.StripeError as e:
        logger.error("Stripe checkout failed: %s", e)
        await db.orders.update_one({"_id": res.inserted_id}, {"$set": {"status": "failed"}})
        raise HTTPException(502, "Could not start checkout")
    await db.orders.update_one({"_id": res.inserted_id}, {"$set": {"provider_session_id": session.id}})
    return {"checkout_url": session.url, "order_id": order_id}


async def load_order(order_id: str, token: str) -> Order:
    doc = await db.orders.find_one({"_id": oid(order_id)})
    if not doc or not secrets.compare_digest(doc.get("access_token", ""), token or ""):
        raise HTTPException(404, "Order not found")
    return Order.from_mongo(doc)


async def downloadable_slugs(order: Order) -> List[str]:
    slugs = []
    for item in order.items:
        doc = await db.products.find_one({"slug": item.slug})
        slugs.extend((doc or {}).get("includes") or [item.slug])
    return list(dict.fromkeys(slugs))


@router.get("/orders/{order_id}")
async def order_status(order_id: str, token: str = ""):
    order = await load_order(order_id, token)
    downloads = []
    if order.status == "paid":
        for slug in await downloadable_slugs(order):
            doc = await db.products.find_one({"slug": slug}) or {}
            downloads.append({"slug": slug, "name_en": doc.get("name_en", slug), "name_ar": doc.get("name_ar", slug)})
    return {"id": order.id, "status": order.status, "email": order.email, "total": order.total,
            "currency": order.currency, "items": [i.model_dump() for i in order.items], "downloads": downloads}


@router.get("/orders/{order_id}/download/{slug}")
async def download(order_id: str, slug: str, token: str = ""):
    order = await load_order(order_id, token)
    if order.status != "paid":
        raise HTTPException(403, "Payment not verified")
    if slug not in await downloadable_slugs(order):
        raise HTTPException(404, "Not in this order")
    for ext, mime in (("zip", "application/zip"), ("pdf", "application/pdf")):
        path = FILES_DIR / f"{slug}.{ext}"
        if path.exists():
            return FileResponse(path, media_type=mime, filename=f"{slug.upper().replace('-', '_')}.{ext}")
    raise HTTPException(404, "File not available yet")


@router.post("/payments/webhook/stripe")
async def stripe_webhook(request: Request):
    secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
    if not secret:
        raise HTTPException(503, "Webhook not configured")
    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(payload, request.headers.get("stripe-signature", ""), secret)
    except (stripe.error.SignatureVerificationError, ValueError):
        raise HTTPException(400, "Invalid signature")
    obj, kind = event["data"]["object"], event["type"]
    order_id = (obj.get("metadata") or {}).get("order_id")
    if kind in ("checkout.session.completed", "checkout.session.async_payment_succeeded") and order_id:
        doc = await db.orders.find_one({"_id": oid(order_id)})
        expected = int(round((doc or {}).get("total", -1) * 100))
        if doc and obj.get("payment_status") == "paid" and obj.get("amount_total") == expected \
                and (obj.get("currency") or "").lower() == "aed":
            await db.orders.update_one({"_id": doc["_id"], "status": {"$ne": "paid"}},
                {"$set": {"status": "paid", "paid_at": now_iso(), "provider_payment_id": obj.get("payment_intent")}})
        elif doc:
            logger.warning("Order %s webhook mismatch: %s %s", order_id, obj.get("amount_total"), expected)
    elif kind in ("checkout.session.expired", "checkout.session.async_payment_failed") and order_id:
        status = "expired" if kind.endswith("expired") else "failed"
        await db.orders.update_one({"_id": oid(order_id), "status": "pending"}, {"$set": {"status": status}})
    elif kind == "charge.refunded":
        await db.orders.update_one({"provider_payment_id": obj.get("payment_intent")}, {"$set": {"status": "refunded"}})
    return {"received": True}
