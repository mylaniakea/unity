from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app import models
from app.schemas.knowledge import *

router = APIRouter(
    prefix="/knowledge",
    tags=["knowledge"],
    responses={404: {"description": "Not found"}},
)

@router.get("/", response_model=List[KnowledgeItem])
def read_knowledge(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    items = db.query(models.KnowledgeItem).order_by(models.KnowledgeItem.updated_at.desc()).offset(skip).limit(limit).all()
    return items

@router.post("/", response_model=KnowledgeItem)
def create_knowledge(item: KnowledgeCreate, db: Session = Depends(get_db)):
    db_item = models.KnowledgeItem(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@router.delete("/{item_id}")
def delete_knowledge(item_id: int, db: Session = Depends(get_db)):
    item = db.query(models.KnowledgeItem).filter(models.KnowledgeItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(item)
    db.commit()
    return {"ok": True}
