from typing import Literal
from pydantic import BaseModel, Field, field_validator
TOPICS = ["البنية التحتية", "جودة الحياة", "التكريم والجوائز", "الزيارات والفعاليات", "رؤية 2030", "البيئة والاستدامة", "التقنية والابتكار", "الإدارة البلدية", "المجتمع والثقافة", "الإنجازات والأرقام"]
class Metadata(BaseModel):
    topic: str | None = None
    has_stats: bool = False
    has_religious: bool = False
    desired_opening: int = Field(default=0, ge=0, le=7)
    @field_validator("topic")
    @classmethod
    def valid_topic(cls, value):
        if value is not None and value not in TOPICS: raise ValueError("Unknown topic")
        return value
class TransformRequest(BaseModel):
    text: str = Field(min_length=1, max_length=12000)
    text_type: Literal["مقال", "كلمة رسمية", "تغريدة", "فقرة قصيرة", "تقرير"] = "مقال"
    @field_validator("text")
    @classmethod
    def not_blank(cls,value):
        if not value.strip(): raise ValueError("Text is blank")
        return value.strip()
