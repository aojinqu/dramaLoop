from pydantic import BaseModel, Field


class ProceduralSkill(BaseModel):
    id: str = Field(min_length=1)
    stage: str = Field(min_length=1)
    trigger: str = Field(min_length=1)
    guidance: str = Field(min_length=1)
    source: str = Field(min_length=1)
    priority: int = 0
