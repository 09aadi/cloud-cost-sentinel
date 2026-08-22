
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class CloudAccount(Base):
    __tablename__ = "cloud_accounts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    provider = Column(String, nullable=False)  # "aws", "gcp", or "azure"
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    cost_record = relationship("CostRecord", back_populates="cloud_account")

class CostRecord(Base):
    __tablename__ = "cost_record"

    id = Column(Integer, primary_key=True, index=True)
    cloud_account_id = Column(Integer, ForeignKey("cloud_accounts.id"), nullable=False)
    date = Column(Date, nullable=False)
    service_name = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    cloud_account = relationship("CloudAccount", back_populates="cost_record")