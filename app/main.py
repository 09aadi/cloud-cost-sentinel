from fastapi import FastAPI, Depends
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