from pydantic import BaseModel, Field
class RevokeInput(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)
