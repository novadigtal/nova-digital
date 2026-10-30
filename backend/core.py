import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Annotated
from bson import ObjectId
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, BeforeValidator, ConfigDict

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]
FILES_DIR = ROOT_DIR / "files"

PyObjectId = Annotated[str, BeforeValidator(lambda v: str(v) if isinstance(v, ObjectId) else v)]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class BaseDocument(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: Optional[PyObjectId] = Field(default=None, alias="_id")

    def to_mongo(self) -> dict:
        data = self.model_dump(by_alias=True, exclude_none=True)
        data.pop("_id", None)
        return data

    @classmethod
    def from_mongo(cls, doc: dict):
        return cls(**doc)

    def out(self) -> dict:
        return self.model_dump(exclude={"id"}) | {"id": self.id}


def oid(value: str) -> ObjectId:
    from fastapi import HTTPException
    if not ObjectId.is_valid(value):
        raise HTTPException(404, "Not found")
    return ObjectId(value)
