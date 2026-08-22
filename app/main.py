from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas
from app.database import engine, get_db
from app import models
from app.database import engine
from typing import List
app = FastAPI()

models.Base.metadata.create_all(bind=engine)

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

@app.post("/accounts/{account_id}/cost_records", response_model=schemas.CostRecordOut)
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

@app.get("/accounts/{account_id}/cost_records", response_model=List[schemas.CostRecordOut])
def list_all_cost_records(account_id: int, db: Session = Depends(get_db)):
    account = db.query(models.CloudAccount).filter(models.CloudAccount.id == account_id).first()
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    
    return db.query(models.CostRecord).filter(models.CostRecord.cloud_account_id == account_id).all()