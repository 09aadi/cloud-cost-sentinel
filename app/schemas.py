from pydantic import BaseModel
from datetime import datetime


class CloudAccountCreate(BaseModel):
    name: str
    provider: str


class CloudAccountOut(BaseModel):
    id: int
    name: str
    provider: str
    created_at: datetime

    class Config:
        from_attributes = True