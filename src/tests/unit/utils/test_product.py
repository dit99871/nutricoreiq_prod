import pytest
from unittest.mock import Mock
from src.app.utils.product import map_to_schema
from src.app.db.models import Product
from src.app.db.models.nutrient import NutrientCategory
from src.app.schemas.product import NutrientBase, ProductDetailResponse


# Фикстура для создания тестового продукта
@pytest.fixture
def mock_product():
    product = Mock(spec=Product)
    product.id = 1
    product.title = "Test Product"
    product.product_groups = Mock()
    product.product_groups.name = "Test Group"  # Явно задаём строку
    product.nutrient_associations = []
    return product


# Фикстура для создания тестового нутриента
def create_nutrient_association(
    name: str, category: NutrientCategory, amount: float, unit: str = "g"
):
    assoc = Mock()
    assoc.nutrients = Mock()
    assoc.nutrients.name = name
    assoc.nutrients.category = category
    assoc.nutrients.unit = unit
    assoc.amount = amount
    return assoc


# Тест на продукт без нутриентов
def test_map_to_schema_no_nutrients(mock_product):
    product = mock_product
    response = map_to_schema(product)

    assert isinstance(response, ProductDetailResponse)
    assert response.id == 1
    assert response.title == "Test Product"
    assert response.group_name == "Test Group"
    assert response.proteins.total == 0
    assert response.fats.total == 0
    assert response.carbs.total == 0
    assert response.energy_value == 0
    assert response.water == 0
    assert response.vitamins.vits == []
    assert response.minerals.macro == []


# Тест на продукт с макронутриентами
def test_map_to_schema_macros(mock_product):
    product = mock_product
    product.nutrient_associations = [
        create_nutrient_association("Белки", NutrientCategory.MACRO, 10.0),
        create_nutrient_association("Жиры", NutrientCategory.MACRO, 5.0),
        create_nutrient_association("Углеводы", NutrientCategory.MACRO, 20.0),
        create_nutrient_association("Вода", NutrientCategory.MACRO, 100.0),
        create_nutrient_association(
            "Энергетическая ценность", NutrientCategory.ENERGY_VALUE, 200.0, "kcal"
        ),
    ]
    response = map_to_schema(product)

    assert response.proteins.total == 10.0
    assert response.fats.total == 5.0
    assert response.carbs.total == 20.0
    assert response.water == 100.0
    assert response.energy_value == 200.0


# Тест на продукт с аминокислотами
def test_map_to_schema_amino_acids(mock_product):
    product = mock_product
    product.nutrient_associations = [
        create_nutrient_association("Лейцин", NutrientCategory.ESSENTIAL_AMINO, 2.0),
        create_nutrient_association(
            "Тирозин", NutrientCategory.COND_ESSENTIAL_AMINO, 1.5
        ),
        create_nutrient_association("Аланин", NutrientCategory.NONESSENTIAL_AMINO, 1.0),
    ]
    response = map_to_schema(product)

    assert response.proteins.amino_acids.essential == 2.0
    assert response.proteins.amino_acids.cond_essential == 1.5
    assert response.proteins.amino_acids.nonessential == 1.0


# Тест на продукт с жирами
def test_map_to_schema_fats(mock_product):
    product = mock_product
    product.nutrient_associations = [
        create_nutrient_association(
            "Насыщенные жиры", NutrientCategory.SATURATED_FATS, 3.0
        ),
        create_nutrient_association(
            "Холестерин", NutrientCategory.SATURATED_FATS, 0.1, "mg"
        ),
        create_nutrient_association(
            "Мононенасыщенные жиры", NutrientCategory.MONOUNSATURATED_FATS, 2.0
        ),
        create_nutrient_association(
            "Полиненасыщенные жиры", NutrientCategory.POLYUNSATURATED_FATS, 1.0
        ),
        create_nutrient_association(
            "Омега-3", NutrientCategory.POLYUNSATURATED_FATS, 0.5
        ),
        create_nutrient_association(
            "Омега-6", NutrientCategory.POLYUNSATURATED_FATS, 0.3
        ),
    ]
    response = map_to_schema(product)

    assert response.fats.breakdown.saturated == 3.0
    assert response.fats.breakdown.cholesterol == 0.1
    assert response.fats.breakdown.monounsaturated == 2.0
    assert response.fats.breakdown.polyunsaturated.total == 1.0
    assert response.fats.breakdown.polyunsaturated.omega3 == 0.5
    assert response.fats.breakdown.polyunsaturated.omega6 == 0.3


# Тест на продукт с углеводами
def test_map_to_schema_carbs(mock_product):
    product = mock_product
    product.nutrient_associations = [
        create_nutrient_association("Клетчатка", NutrientCategory.CARBS, 4.0),
        create_nutrient_association("Сахар", NutrientCategory.CARBS, 10.0),
    ]
    response = map_to_schema(product)

    assert response.carbs.breakdown.fiber == 4.0
    assert response.carbs.breakdown.sugar == 10.0


# Тест на продукт с витаминами, минералами и другими нутриентами
def test_map_to_schema_vitamins_minerals_others(mock_product):
    product = mock_product
    product.nutrient_associations = [
        create_nutrient_association("Витамин С", NutrientCategory.VITAMINS, 90.0, "mg"),
        create_nutrient_association(
            "Холин", NutrientCategory.VITAMIN_LIKE, 550.0, "mg"
        ),
        create_nutrient_association(
            "Кальций", NutrientCategory.MINERALS_MACRO, 1000.0, "mg"
        ),
        create_nutrient_association(
            "Железо", NutrientCategory.MINERALS_MICRO, 18.0, "mg"
        ),
        create_nutrient_association("Кофеин", NutrientCategory.OTHER, 200.0, "mg"),
    ]
    response = map_to_schema(product)

    assert len(response.vitamins.vits) == 1
    assert response.vitamins.vits[0] == NutrientBase(
        name="Витамин С", amount=90.0, unit="mg"
    )
    assert len(response.vitamin_like.vitslk) == 1
    assert response.vitamin_like.vitslk[0] == NutrientBase(
        name="Холин", amount=550.0, unit="mg"
    )
    assert len(response.minerals.macro) == 1
    assert response.minerals.macro[0] == NutrientBase(
        name="Кальций", amount=1000.0, unit="mg"
    )
    assert len(response.minerals.micro) == 1
    assert response.minerals.micro[0] == NutrientBase(
        name="Железо", amount=18.0, unit="mg"
    )
    assert len(response.other.oths) == 1
    assert response.other.oths[0] == NutrientBase(
        name="Кофеин", amount=200.0, unit="mg"
    )


# Тест на продукт со всеми категориями
def test_map_to_schema_full(mock_product):
    product = mock_product
    product.nutrient_associations = [
        create_nutrient_association("Белки", NutrientCategory.MACRO, 10.0),
        create_nutrient_association("Жиры", NutrientCategory.MACRO, 5.0),
        create_nutrient_association("Углеводы", NutrientCategory.MACRO, 20.0),
        create_nutrient_association(
            "Энергетическая ценность", NutrientCategory.ENERGY_VALUE, 200.0, "kcal"
        ),
        create_nutrient_association("Лейцин", NutrientCategory.ESSENTIAL_AMINO, 2.0),
        create_nutrient_association(
            "Насыщенные жиры", NutrientCategory.SATURATED_FATS, 3.0
        ),
        create_nutrient_association("Клетчатка", NutrientCategory.CARBS, 4.0),
        create_nutrient_association("Витамин С", NutrientCategory.VITAMINS, 90.0, "mg"),
        create_nutrient_association(
            "Кальций", NutrientCategory.MINERALS_MACRO, 1000.0, "mg"
        ),
    ]
    response = map_to_schema(product)

    assert response.proteins.total == 10.0
    assert response.proteins.amino_acids.essential == 2.0
    assert response.fats.total == 5.0
    assert response.fats.breakdown.saturated == 3.0
    assert response.carbs.total == 20.0
    assert response.carbs.breakdown.fiber == 4.0
    assert response.energy_value == 200.0
    assert len(response.vitamins.vits) == 1
    assert len(response.minerals.macro) == 1
