from decimal import Decimal
from pydantic import BaseModel, ConfigDict, field_validator


class ProductResponse(BaseModel):
    """保险产品响应结果"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    clause_name: str
    category: str
    insurer: str
    image_url: str | None = None
    description: str | None = None
    min_premium: Decimal | None
    max_premium: Decimal | None
    target_group: str | None
    highlights: list[str] | None = None
    status: str