"""
Knowledge base schema definitions.

Documentation and knowledge management.
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# Knowledge
class KnowledgeBase(BaseModel):
    title: str
    content: str
    category: str
    tags: List[str] = []

class KnowledgeCreate(KnowledgeBase):
    pass

class KnowledgeUpdate(KnowledgeBase):
    pass

class KnowledgeItem(KnowledgeBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
