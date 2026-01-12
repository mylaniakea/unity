from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.core.dependencies import get_tenant_id
from app import models, schemas_knowledge

router = APIRouter(
    prefix="/knowledge",
    tags=["knowledge"],
    responses={404: {"description": "Not found"}},
)

@router.get("/", response_model=List[schemas_knowledge.KnowledgeItem])
def read_knowledge(skip: int = 0, limit: int = 100, db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)):
    items = db.query(models.KnowledgeItem).order_by(models.KnowledgeItem.updated_at.desc()).offset(skip).limit(limit).all()
    return items

@router.post("/", response_model=schemas_knowledge.KnowledgeItem)
def create_knowledge(item: schemas_knowledge.KnowledgeCreate, db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)):
    db_item = models.KnowledgeItem(tenant_id=tenant_id, **item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@router.delete("/{item_id}")
def delete_knowledge(item_id: int, db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)):
    item = db.query(models.KnowledgeItem).filter(models.KnowledgeItem.tenant_id == tenant_id).filter(models.KnowledgeItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(item)
    db.commit()
    return {"ok": True}
