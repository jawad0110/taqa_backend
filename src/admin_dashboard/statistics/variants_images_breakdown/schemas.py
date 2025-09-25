from pydantic import BaseModel, Field

class BreakdownStats(BaseModel):
    with_additional_images_pct: float = Field(..., description="Percentage of products with more than 1 image")
    with_variants_pct: float = Field(..., description="Percentage of products with at least 1 variant")
