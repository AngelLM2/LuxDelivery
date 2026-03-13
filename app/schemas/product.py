from pydantic import BaseModel, ConfigDict, Field


class ProductCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    price: float = Field(gt=0)
    description: str = Field(min_length=2, max_length=1000)
    is_offer: bool = False
    category_id: int | None = None


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    price: float | None = Field(default=None, gt=0)
    description: str | None = Field(default=None, min_length=2, max_length=1000)
    is_offer: bool | None = None
    category_id: int | None = None


class ProductRead(BaseModel):
    id: int
    name: str
    price: float
    description: str
    is_offer: bool
    category_id: int | None = None

    model_config = ConfigDict(from_attributes=True)
