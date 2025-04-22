from .base import BaseSchema


# Базовые схемы
class NutrientBase(BaseSchema):
    amount: float
    name: str
    unit: str


class AminoAcids(BaseSchema):
    essential: float = 0.0
    cond_essential: float = 0.0
    nonessential: float = 0.0


class PolyunsaturatedFats(BaseSchema):
    total: float = 0.0
    omega3: float = 0.0
    omega6: float = 0.0


class FatsDetail(BaseSchema):
    saturated: float = 0.0
    monounsaturated: float = 0.0
    polyunsaturated: PolyunsaturatedFats = PolyunsaturatedFats()
    cholesterol: float = 0.0  # Особый случай, можно искать по названию


class CarbsDetail(BaseSchema):
    fiber: float = 0.0
    sugar: float = 0.0


# Основные схемы группировки
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


# Главная схема продукта
class ProductDetailResponse(BaseSchema):
    id: int
    title: str
    group_name: str

    proteins: ProteinsSchema = ProteinsSchema()
    fats: FatsSchema = FatsSchema()
    carbs: CarbsSchema = CarbsSchema()

    vitamins: VitaminsSchema = VitaminsSchema()
    vitamin_like: VitaminLikeSchema = VitaminLikeSchema()
    minerals: MineralsSchema = MineralsSchema()
    other: OtherSchema = OtherSchema()
