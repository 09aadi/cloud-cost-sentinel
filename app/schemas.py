from pydantic import BaseModel
from datetime import datetime
from datetime import date


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

class CostRecordCreate(BaseModel):
    service_name: str
    amount: float
    date: date


class CostRecordOut(BaseModel):
    id: int
    cloud_account_id: int
    service_name: str
    amount: float
    date: date
    created_at: datetime