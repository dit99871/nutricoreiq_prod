from typing import Annotated

from pydantic import Field

from .base import BaseSchema


# базовые схемы
class NutrientBase(BaseSchema):
    amount: Annotated[float, Field(ge=0)] = 0.0
    name: Annotated[str, Field(min_length=3, max_length=40)]
    unit: str


class AminoAcids(BaseSchema):
    essential: Annotated[float, Field(ge=0)] = 0.0
    cond_essential: Annotated[float, Field(ge=0)] = 0.0
    nonessential: Annotated[float, Field(ge=0)] = 0.0


class PolyunsaturatedFats(BaseSchema):
    total: float = 0.0
    omega3: float = 0.0
    omega6: float = 0.0


class FatsDetail(BaseSchema):
    saturated: float = 0.0
    monounsaturated: float = 0.0
    polyunsaturated: PolyunsaturatedFats = PolyunsaturatedFats()
    cholesterol: float = 0.0


class CarbsDetail(BaseSchema):
    fiber: float = 0.0
    sugar: float = 0.0


# основные схемы группировки
class ProteinsSchema(BaseSchema):
    total: float = 0.0
    amino_acids: AminoAcids = AminoAcids()


class FatsSchema(BaseSchema):
    total: float = 0.0
    breakdown: FatsDetail = FatsDetail()


class CarbsSchema(BaseSchema):
    total: float = 0.0
    breakdown: CarbsDetail = CarbsDetail()


class VitaminsSchema(BaseSchema):
    vits: list[NutrientBase] = []


class VitaminLikeSchema(BaseSchema):
    vitslk: list[NutrientBase] = []


class MineralsSchema(BaseSchema):
    macro: list[NutrientBase] = []
    micro: list[NutrientBase] = []


class OtherSchema(BaseSchema):
    oths: list[NutrientBase] = []


# главная схема продукта
class ProductDetailResponse(BaseSchema):
    id: int
    title: Annotated[str, Field(min_length=3, max_length=40)]
    group_name: Annotated[str, Field(min_length=3, max_length=40)]

    proteins: ProteinsSchema = ProteinsSchema()
    fats: FatsSchema = FatsSchema()
    carbs: CarbsSchema = CarbsSchema()
    energy_value: float = 0.0
    water: float = 0.0

    vitamins: VitaminsSchema = VitaminsSchema()
    vitamin_like: VitaminLikeSchema = VitaminLikeSchema()
    minerals: MineralsSchema = MineralsSchema()
    other: OtherSchema = OtherSchema()


class ProductSuggestion(BaseSchema):
    id: int
    title: Annotated[str, Field(min_length=3, max_length=40)]
    group_name: str


class PendingProductCreate(BaseSchema):
    name: Annotated[str, Field(min_length=3, max_length=40)]


# схема ответа
class UnifiedProductResponse(BaseSchema):
    exact_match: ProductDetailResponse | None = None
    suggestions: list[ProductSuggestion] = []
    needs_confirmation: bool = False
    pending_added: bool = False
