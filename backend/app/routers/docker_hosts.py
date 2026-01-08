from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.core.dependencies import get_tenant_id

router = APIRouter(
    prefix="/docker/hosts",
    tags=["docker-hosts"],
    responses={404: {"description": "Not found"}},
)


@router.get("/")
def list_docker_hosts(db: Session = Depends(get_db), tenant_id: str = Depends(get_tenant_id)):
    """Placeholder Docker hosts endpoint. Returns an empty list for now."""
    return []
