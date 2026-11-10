from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from app import models, schemas
from app.database import engine, get_db
from typing import List
from app.anomaly import compute_anomalies
from app.cache import get_cached_summary, set_cached_summary
app = FastAPI()

models.Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    # Liveness: the process is up and serving. Deliberately does NOT touch the
    # database or Redis -- if liveness depended on them, a database outage would
    # make Kubernetes restart healthy API pods and make the outage worse.
    return {"status": "ok"}


@app.get("/ready")
def ready(db: Session = Depends(get_db)):
    # Readiness: can this pod serve real traffic? Checks the database only.
    # Redis is an optimisation (cached summaries), not a hard dependency.
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(status_code=503, detail="database unavailable")
    return {"status": "ready"}

@app.post("/accounts", response_model=schemas.CloudAccountOut)
def create_account(account: schemas.CloudAccountCreate, db: Session = Depends(get_db)):
    new_account = models.CloudAccount(name=account.name, provider=account.provider)
    db.add(new_account)
    db.commit()
    db.refresh(new_account)
    return new_account

@app.get("/accounts", response_model=List[schemas.CloudAccountOut])
def list_accounts(db: Session = Depends(get_db)):
    return db.query(models.CloudAccount).all()

@app.post("/accounts/{account_id}/cost-records", response_model=schemas.CostRecordOut)
def create_cost_record(account_id: int, record: schemas.CostRecordCreate, db: Session = Depends(get_db)):
    account = db.query(models.CloudAccount).filter(models.CloudAccount.id == account_id).first()

    if account is None:
        raise HTTPException(status_code=404, detail= "Account not found")

    new_cost_record = models.CostRecord(
        cloud_account_id=account_id,
        service_name= record.service_name, 
        amount= record.amount, 
        date=record.date)
    db.add(new_cost_record)
    db.commit()
    db.refresh(new_cost_record)
    return new_cost_record

@app.get("/accounts/{account_id}/cost-records", response_model=List[schemas.CostRecordOut])
def list_all_cost_records(account_id: int, db: Session = Depends(get_db)):
    account = db.query(models.CloudAccount).filter(models.CloudAccount.id == account_id).first()
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    
    return db.query(models.CostRecord).filter(models.CostRecord.cloud_account_id == account_id).all()

@app.get("/accounts/{account_id}/anomalies", response_model=List[schemas.AnomalyOut])
def get_anomalies(account_id: int, db: Session = Depends(get_db)):
    account = db.query(models.CloudAccount).filter(models.CloudAccount.id == account_id).first()
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    records = db.query(models.CostRecord).filter(models.CostRecord.cloud_account_id == account_id).all()
    return compute_anomalies(records)


@app.get("/accounts/{account_id}/summary")
def get_summary(account_id: int, db: Session = Depends(get_db)):
    account = db.query(models.CloudAccount).filter(models.CloudAccount.id == account_id).first()
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")

    cached = get_cached_summary(account_id)
    if cached is not None:
        return {**cached, "source": "cache"}

    records = db.query(models.CostRecord).filter(models.CostRecord.cloud_account_id == account_id).all()
    total = sum(r.amount for r in records)
    summary = {"account_id": account_id, "total_spend": total, "record_count": len(records)}
    set_cached_summary(account_id, summary)
    return {**summary, "source": "db"}