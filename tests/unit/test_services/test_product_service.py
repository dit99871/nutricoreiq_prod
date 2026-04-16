"""
Тесты для ProductService.
"""

from unittest.mock import MagicMock

import pytest

from src.app.core.models import NutrientCategory
from src.app.core.schemas.product import ProductDetailResponse
from src.app.core.services.product_service import ProductService


@pytest.fixture
def mock_product_group():
    """Создает мок для ProductGroup."""
    group = MagicMock()
    group.name = "Fruits"
    return group


@pytest.fixture
def mock_product(mock_product_group):
    """Создает мок для Product."""
    product = MagicMock()
    product.id = 1
    product.title = "Apple"
    product.product_groups = mock_product_group
    product.nutrient_associations = []
    return product


def create_nutrient_assoc(name: str, category: NutrientCategory, amount: float, unit: str = "г"):
    """Создает мок для ProductNutrient association."""
    assoc = MagicMock()
    assoc.amount = amount
    
    nutrient = MagicMock()
    nutrient.name = name
    nutrient.unit = unit
    nutrient.category = category
    
    assoc.nutrients = nutrient
    return assoc


# --- map_to_schema базовые тесты ---


def test_map_to_schema_basic_fields(mock_product):
    """Тест базовых полей маппинга."""
    result = ProductService.map_to_schema(mock_product)
    
    assert isinstance(result, ProductDetailResponse)
    assert result.id == 1
    assert result.title == "Apple"
    assert result.group_name == "Fruits"


def test_map_to_schema_empty_associations(mock_product):
    """Тест с пустым списком ассоциаций."""
    result = ProductService.map_to_schema(mock_product)
    
    assert result.proteins.total == 0.0
    assert result.fats.total == 0.0
    assert result.carbs.total == 0.0
    assert result.energy_value == 0.0
    assert result.water == 0.0


# --- Макронутриенты ---


def test_map_to_schema_macronutrients_proteins(mock_product):
    """Тест маппинга белков."""
    mock_product.nutrient_associations = [
        create_nutrient_assoc("Белки", NutrientCategory.MACRO, 25.5),
    ]
    
    result = ProductService.map_to_schema(mock_product)
    
    assert result.proteins.total == 25.5


def test_map_to_schema_macronutrients_fats(mock_product):
    """Тест маппинга жиров."""
    mock_product.nutrient_associations = [
        create_nutrient_assoc("Жиры", NutrientCategory.MACRO, 10.3),
    ]
    
    result = ProductService.map_to_schema(mock_product)
    
    assert result.fats.total == 10.3


def test_map_to_schema_macronutrients_carbs(mock_product):
    """Тест маппинга углеводов."""
    mock_product.nutrient_associations = [
        create_nutrient_assoc("Углеводы", NutrientCategory.MACRO, 52.0),
    ]
    
    result = ProductService.map_to_schema(mock_product)
    
    assert result.carbs.total == 52.0


def test_map_to_schema_macronutrients_water(mock_product):
    """Тест маппинга воды."""
    mock_product.nutrient_associations = [
        create_nutrient_assoc("Вода", NutrientCategory.MACRO, 84.0),
    ]
    
    result = ProductService.map_to_schema(mock_product)
    
    assert result.water == 84.0


# --- Энергетическая ценность ---


def test_map_to_schema_energy_value(mock_product):
    """Тест маппинга энергетической ценности."""
    mock_product.nutrient_associations = [
        create_nutrient_assoc("Калорийность", NutrientCategory.ENERGY_VALUE, 52.0, "ккал"),
    ]
    
    result = ProductService.map_to_schema(mock_product)
    
    assert result.energy_value == 52.0


# --- Аминокислоты ---


def test_map_to_schema_amino_acids_essential(mock_product):
    """Тест маппинга незаменимых аминокислот."""
    mock_product.nutrient_associations = [
        create_nutrient_assoc("Лизин", NutrientCategory.ESSENTIAL_AMINO, 0.5),
        create_nutrient_assoc("Метионин", NutrientCategory.ESSENTIAL_AMINO, 0.3),
    ]
    
    result = ProductService.map_to_schema(mock_product)
    
    assert result.proteins.amino_acids.essential == 0.8


def test_map_to_schema_amino_acids_cond_essential(mock_product):
    """Тест маппинга условно незаменимых аминокислот."""
    mock_product.nutrient_associations = [
        create_nutrient_assoc("Аргинин", NutrientCategory.COND_ESSENTIAL_AMINO, 1.2),
    ]
    
    result = ProductService.map_to_schema(mock_product)
    
    assert result.proteins.amino_acids.cond_essential == 1.2


def test_map_to_schema_amino_acids_nonessential(mock_product):
    """Тест маппинга заменимых аминокислот."""
    mock_product.nutrient_associations = [
        create_nutrient_assoc("Аланин", NutrientCategory.NONESSENTIAL_AMINO, 0.8),
        create_nutrient_assoc("Глицин", NutrientCategory.NONESSENTIAL_AMINO, 0.4),
    ]
    
    result = ProductService.map_to_schema(mock_product)
    
    assert result.proteins.amino_acids.nonessential == pytest.approx(1.2)


# --- Жиры ---


def test_map_to_schema_fats_saturated(mock_product):
    """Тест маппинга насыщенных жиров."""
    mock_product.nutrient_associations = [
        create_nutrient_assoc("Насыщенные жирные кислоты", NutrientCategory.SATURATED_FATS, 5.0),
    ]
    
    result = ProductService.map_to_schema(mock_product)
    
    assert result.fats.breakdown.saturated == 5.0


def test_map_to_schema_fats_cholesterol(mock_product):
    """Тест маппинга холестерина."""
    mock_product.nutrient_associations = [
        create_nutrient_assoc("Холестерин", NutrientCategory.SATURATED_FATS, 0.01, "мг"),
    ]
    
    result = ProductService.map_to_schema(mock_product)
    
    assert result.fats.breakdown.cholesterol == 0.01


def test_map_to_schema_fats_monounsaturated(mock_product):
    """Тест маппинга мононенасыщенных жиров."""
    mock_product.nutrient_associations = [
        create_nutrient_assoc("Мононенасыщенные жирные кислоты", NutrientCategory.MONOUNSATURATED_FATS, 3.5),
    ]
    
    result = ProductService.map_to_schema(mock_product)
    
    assert result.fats.breakdown.monounsaturated == 3.5


def test_map_to_schema_fats_polyunsaturated_total(mock_product):
    """Тест маппинга полиненасыщенных жиров (общее)."""
    mock_product.nutrient_associations = [
        create_nutrient_assoc("Полиненасыщенные жирные кислоты", NutrientCategory.POLYUNSATURATED_FATS, 2.0),
    ]
    
    result = ProductService.map_to_schema(mock_product)
    
    assert result.fats.breakdown.polyunsaturated.total == 2.0


def test_map_to_schema_fats_polyunsaturated_omega3(mock_product):
    """Тест маппинга омега-3."""
    mock_product.nutrient_associations = [
        create_nutrient_assoc("Омега-3", NutrientCategory.POLYUNSATURATED_FATS, 0.5),
    ]
    
    result = ProductService.map_to_schema(mock_product)
    
    assert result.fats.breakdown.polyunsaturated.omega3 == 0.5


def test_map_to_schema_fats_polyunsaturated_omega6(mock_product):
    """Тест маппинга омега-6."""
    mock_product.nutrient_associations = [
        create_nutrient_assoc("Омега-6", NutrientCategory.POLYUNSATURATED_FATS, 1.5),
    ]
    
    result = ProductService.map_to_schema(mock_product)
    
    assert result.fats.breakdown.polyunsaturated.omega6 == 1.5


# --- Углеводы ---


def test_map_to_schema_carbs_fiber(mock_product):
    """Тест маппинга клетчатки."""
    mock_product.nutrient_associations = [
        create_nutrient_assoc("Клетчатка", NutrientCategory.CARBS, 2.4),
    ]
    
    result = ProductService.map_to_schema(mock_product)
    
    assert result.carbs.breakdown.fiber == 2.4


def test_map_to_schema_carbs_sugar(mock_product):
    """Тест маппинга сахаров."""
    mock_product.nutrient_associations = [
        create_nutrient_assoc("Сахар", NutrientCategory.CARBS, 10.5),
    ]
    
    result = ProductService.map_to_schema(mock_product)
    
    assert result.carbs.breakdown.sugar == 10.5


# --- Витамины ---


def test_map_to_schema_vitamins(mock_product):
    """Тест маппинга витаминов."""
    mock_product.nutrient_associations = [
        create_nutrient_assoc("Витамин C", NutrientCategory.VITAMINS, 10.0, "мг"),
        create_nutrient_assoc("Витамин A", NutrientCategory.VITAMINS, 0.05, "мг"),
    ]
    
    result = ProductService.map_to_schema(mock_product)
    
    assert len(result.vitamins.vits) == 2
    assert result.vitamins.vits[0].name == "Витамин C"
    assert result.vitamins.vits[0].amount == 10.0
    assert result.vitamins.vits[0].unit == "мг"


# --- Витаминоподобные вещества ---


def test_map_to_schema_vitamin_like(mock_product):
    """Тест маппинга витаминоподобных веществ."""
    mock_product.nutrient_associations = [
        create_nutrient_assoc("Карнитин", NutrientCategory.VITAMIN_LIKE, 5.0, "мг"),
    ]
    
    result = ProductService.map_to_schema(mock_product)
    
    assert len(result.vitamin_like.vitslk) == 1
    assert result.vitamin_like.vitslk[0].name == "Карнитин"
    assert result.vitamin_like.vitslk[0].amount == 5.0


# --- Минералы ---


def test_map_to_schema_minerals_macro(mock_product):
    """Тест маппинга макроминералов."""
    mock_product.nutrient_associations = [
        create_nutrient_assoc("Кальций", NutrientCategory.MINERALS_MACRO, 10.0, "мг"),
        create_nutrient_assoc("Магний", NutrientCategory.MINERALS_MACRO, 5.0, "мг"),
    ]
    
    result = ProductService.map_to_schema(mock_product)
    
    assert len(result.minerals.macro) == 2
    assert result.minerals.macro[0].name == "Кальций"
    assert result.minerals.macro[0].amount == 10.0


def test_map_to_schema_minerals_micro(mock_product):
    """Тест маппинга микроминералов."""
    mock_product.nutrient_associations = [
        create_nutrient_assoc("Железо", NutrientCategory.MINERALS_MICRO, 0.5, "мг"),
        create_nutrient_assoc("Цинк", NutrientCategory.MINERALS_MICRO, 0.2, "мг"),
    ]
    
    result = ProductService.map_to_schema(mock_product)
    
    assert len(result.minerals.micro) == 2
    assert result.minerals.micro[0].name == "Железо"
    assert result.minerals.micro[0].amount == 0.5


# --- Прочие нутриенты ---


def test_map_to_schema_other_nutrients(mock_product):
    """Тест маппинга прочих нутриентов."""
    mock_product.nutrient_associations = [
        create_nutrient_assoc("Кофеин", NutrientCategory.OTHER, 0.01, "г"),
    ]
    
    result = ProductService.map_to_schema(mock_product)
    
    assert len(result.other.oths) == 1
    assert result.other.oths[0].name == "Кофеин"
    assert result.other.oths[0].amount == 0.01


# --- Комплексный тест ---


def test_map_to_schema_comprehensive(mock_product):
    """Тест комплексного маппинга со всеми категориями."""
    mock_product.nutrient_associations = [
        # Макронутриенты
        create_nutrient_assoc("Белки", NutrientCategory.MACRO, 25.5),
        create_nutrient_assoc("Жиры", NutrientCategory.MACRO, 10.3),
        create_nutrient_assoc("Углеводы", NutrientCategory.MACRO, 52.0),
        create_nutrient_assoc("Вода", NutrientCategory.MACRO, 84.0),
        # Энергия
        create_nutrient_assoc("Калорийность", NutrientCategory.ENERGY_VALUE, 52.0, "ккал"),
        # Аминокислоты
        create_nutrient_assoc("Лизин", NutrientCategory.ESSENTIAL_AMINO, 0.5),
        create_nutrient_assoc("Аргинин", NutrientCategory.COND_ESSENTIAL_AMINO, 1.2),
        create_nutrient_assoc("Аланин", NutrientCategory.NONESSENTIAL_AMINO, 0.8),
        # Жиры
        create_nutrient_assoc("Насыщенные жирные кислоты", NutrientCategory.SATURATED_FATS, 5.0),
        create_nutrient_assoc("Холестерин", NutrientCategory.SATURATED_FATS, 0.01, "мг"),
        create_nutrient_assoc("Мононенасыщенные жирные кислоты", NutrientCategory.MONOUNSATURATED_FATS, 3.5),
        create_nutrient_assoc("Омега-3", NutrientCategory.POLYUNSATURATED_FATS, 0.5),
        # Углеводы
        create_nutrient_assoc("Клетчатка", NutrientCategory.CARBS, 2.4),
        create_nutrient_assoc("Сахар", NutrientCategory.CARBS, 10.5),
        # Витамины
        create_nutrient_assoc("Витамин C", NutrientCategory.VITAMINS, 10.0, "мг"),
        # Витаминоподобные
        create_nutrient_assoc("Карнитин", NutrientCategory.VITAMIN_LIKE, 5.0, "мг"),
        # Минералы
        create_nutrient_assoc("Кальций", NutrientCategory.MINERALS_MACRO, 10.0, "мг"),
        create_nutrient_assoc("Железо", NutrientCategory.MINERALS_MICRO, 0.5, "мг"),
        # Прочие
        create_nutrient_assoc("Кофеин", NutrientCategory.OTHER, 0.01, "г"),
    ]
    
    result = ProductService.map_to_schema(mock_product)
    
    # Проверка макронутриентов
    assert result.proteins.total == 25.5
    assert result.fats.total == 10.3
    assert result.carbs.total == 52.0
    assert result.water == 84.0
    
    # Проверка энергии
    assert result.energy_value == 52.0
    
    # Проверка аминокислот
    assert result.proteins.amino_acids.essential == 0.5
    assert result.proteins.amino_acids.cond_essential == 1.2
    assert result.proteins.amino_acids.nonessential == 0.8
    
    # Проверка жиров
    assert result.fats.breakdown.saturated == 5.0
    assert result.fats.breakdown.cholesterol == 0.01
    assert result.fats.breakdown.monounsaturated == 3.5
    assert result.fats.breakdown.polyunsaturated.omega3 == 0.5
    
    # Проверка углеводов
    assert result.carbs.breakdown.fiber == 2.4
    assert result.carbs.breakdown.sugar == 10.5
    
    # Проверка витаминов
    assert len(result.vitamins.vits) == 1
    assert result.vitamins.vits[0].name == "Витамин C"
    
    # Проверка витаминоподобных
    assert len(result.vitamin_like.vitslk) == 1
    
    # Проверка минералов
    assert len(result.minerals.macro) == 1
    assert len(result.minerals.micro) == 1
    
    # Проверка прочих
    assert len(result.other.oths) == 1
