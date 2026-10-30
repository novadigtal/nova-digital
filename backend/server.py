import logging
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from core import client
import auth
import catalog
import orders
import content
import admin

logging.basicConfig(level=logging.INFO)

app = FastAPI()
for module in (auth, catalog, orders, content, admin):
    app.include_router(module.router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origin_regex=".*",
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    await auth.seed_admin()
    await catalog.seed_products()


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
