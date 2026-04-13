"""Схемы для работы с продуктами."""

from typing import Annotated

from pydantic import Field

from .base import BaseSchema


class NutrientBase(BaseSchema):
    """Базовая схема"""

    amount: Annotated[float, Field(ge=0)] = 0.0
    name: Annotated[str, Field(min_length=3, max_length=40)]
    unit: str


class AminoAcids(BaseSchema):
    """Схема аминокислот"""

    essential: Annotated[float, Field(ge=0)] = 0.0
    cond_essential: Annotated[float, Field(ge=0)] = 0.0
    nonessential: Annotated[float, Field(ge=0)] = 0.0


class PolyunsaturatedFats(BaseSchema):
    """Схема полиненасыщенных жирных кислот"""

    total: float = 0.0
    omega3: float = 0.0
    omega6: float = 0.0


class FatsDetail(BaseSchema):
    """Схема типов жирных кислот"""

    saturated: float = 0.0
    monounsaturated: float = 0.0
    polyunsaturated: PolyunsaturatedFats = PolyunsaturatedFats()
    cholesterol: float = 0.0


class CarbsDetail(BaseSchema):
    """Схема типов углеводов"""

    fiber: float = 0.0
    sugar: float = 0.0


class ProteinsSchema(BaseSchema):
    """Схема белков"""

    total: float = 0.0
    amino_acids: AminoAcids = AminoAcids()


class FatsSchema(BaseSchema):
    """Схема жиров"""

    total: float = 0.0
    breakdown: FatsDetail = FatsDetail()


class CarbsSchema(BaseSchema):
    """Схема углеводов"""

    total: float = 0.0
    breakdown: CarbsDetail = CarbsDetail()


class VitaminsSchema(BaseSchema):
    """Схема витаминов"""

    vits: list[NutrientBase] = []


class VitaminLikeSchema(BaseSchema):
    """Схема витаминоподобных веществ"""

    vitslk: list[NutrientBase] = []


class MineralsSchema(BaseSchema):
    """Схема минералов"""

    macro: list[NutrientBase] = []
    micro: list[NutrientBase] = []


class OtherSchema(BaseSchema):
    """Схема для остальных нутриентов"""

    oths: list[NutrientBase] = []


class ProductDetailResponse(BaseSchema):
    """Главная схема продуктов для ответа"""

    id: int
    title: Annotated[str, Field(min_length=3, max_length=150)]
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
    """Схема для вывода подсказок для названий продуктов"""

    id: int
    title: Annotated[str, Field(min_length=3, max_length=150)]
    group_name: str


class PendingProductCreate(BaseSchema):
    """
    Схема создания продукта, который ожидает очереди
    на добавление в БД
    """

    name: Annotated[str, Field(min_length=3, max_length=40)]


class UnifiedProductResponse(BaseSchema):
    """Универсальная схема ответа"""

    exact_match: ProductDetailResponse | None = None
    suggestions: list[ProductSuggestion] = []
    needs_confirmation: bool = False
    pending_added: bool = False
