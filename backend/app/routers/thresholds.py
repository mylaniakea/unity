from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app import models
from app.schemas.alerts import ThresholdRule, ThresholdRuleCreate, ThresholdRuleUpdate

router = APIRouter(prefix="/thresholds", tags=["thresholds"])

@router.get("/", response_model=List[ThresholdRule])
def get_threshold_rules(db: Session = Depends(get_db)):
    """Get all threshold rules"""
    rules = db.query(models.ThresholdRule).all()
    return rules

@router.get("/{rule_id}", response_model=ThresholdRule)
def get_threshold_rule(rule_id: int, db: Session = Depends(get_db)):
    """Get a specific threshold rule"""
    rule = db.query(models.ThresholdRule).filter(models.ThresholdRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Threshold rule not found")
    return rule

@router.post("/", response_model=ThresholdRule)
def create_threshold_rule(rule: ThresholdRuleCreate, db: Session = Depends(get_db)):
    """Create a new threshold rule"""
    db_rule = models.ThresholdRule(**rule.model_dump())
    db.add(db_rule)
    db.commit()
    db.refresh(db_rule)
    return db_rule

@router.put("/{rule_id}", response_model=ThresholdRule)
def update_threshold_rule(rule_id: int, rule: ThresholdRuleUpdate, db: Session = Depends(get_db)):
    """Update a threshold rule"""
    db_rule = db.query(models.ThresholdRule).filter(models.ThresholdRule.id == rule_id).first()
    if not db_rule:
        raise HTTPException(status_code=404, detail="Threshold rule not found")

    update_data = rule.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_rule, key, value)

    db.commit()
    db.refresh(db_rule)
    return db_rule

@router.post("/{rule_id}/mute", response_model=ThresholdRule)
def mute_threshold_rule(rule_id: int, mute_duration_minutes: int, db: Session = Depends(get_db)):
    """Mute a threshold rule for a specified duration in minutes"""
    db_rule = db.query(models.ThresholdRule).filter(models.ThresholdRule.id == rule_id).first()
    if not db_rule:
        raise HTTPException(status_code=404, detail="Threshold rule not found")

    db_rule.muted_until = datetime.now() + timedelta(minutes=mute_duration_minutes)
    db.commit()
    db.refresh(db_rule)
    return db_rule

@router.delete("/{rule_id}")
def delete_threshold_rule(rule_id: int, db: Session = Depends(get_db)):
    """Delete a threshold rule"""
    db_rule = db.query(models.ThresholdRule).filter(models.ThresholdRule.id == rule_id).first()
    if not db_rule:
        raise HTTPException(status_code=404, detail="Threshold rule not found")

    db.delete(db_rule)
    db.commit()
    return {"message": "Threshold rule deleted successfully"}
