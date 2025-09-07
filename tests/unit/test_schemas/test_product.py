import pytest
from datetime import datetime
from pydantic import ValidationError
from src.app.schemas.product import (
    NutrientBase,
    AminoAcids,
    PolyunsaturatedFats,
    FatsDetail,
    CarbsDetail,
    ProteinsSchema,
    FatsSchema,
    CarbsSchema,
    VitaminsSchema,
    VitaminLikeSchema,
    MineralsSchema,
    OtherSchema,
    ProductDetailResponse,
    ProductSuggestion,
    PendingProductCreate,
    UnifiedProductResponse,
)


# Тесты для базовых схем
def test_nutrient_base_validation():
    # Проверка корректного создания
    nutrient = NutrientBase(amount=10.5, name="Protein", unit="g")
    assert nutrient.amount == 10.5
    assert nutrient.name == "Protein"
    assert nutrient.unit == "g"

    # Проверка валидации типов
    with pytest.raises(ValidationError):
        NutrientBase(amount="not a number", name=123, unit=[])


def test_amino_acids_validation():
    # Проверка значений по умолчанию
    aa = AminoAcids()
    assert aa.essential == 0.0
    assert aa.cond_essential == 0.0
    assert aa.nonessential == 0.0

    # Проверка кастомных значений
    aa = AminoAcids(essential=5.0, cond_essential=3.0, nonessential=2.0)
    assert aa.essential == 5.0


# Тесты для схем макронутриентов
def test_fats_schema_validation():
    fats = FatsSchema(
        total=10.0,
        breakdown=FatsDetail(
            saturated=3.0,
            monounsaturated=4.0,
            polyunsaturated=PolyunsaturatedFats(total=3.0, omega3=1.0, omega6=2.0),
            cholesterol=0.1,
        ),
    )
    assert fats.total == 10.0
    assert fats.breakdown.saturated == 3.0
    assert fats.breakdown.polyunsaturated.omega3 == 1.0


# Тесты для основной схемы продукта
def test_product_detail_response_validation():
    product = ProductDetailResponse(
        id=1,
        title="Test Product",
        group_name="Test Group",
        proteins=ProteinsSchema(total=10.0),
        fats=FatsSchema(total=5.0),
        carbs=CarbsSchema(total=20.0),
        energy_value=150.0,
        water=70.0,
    )

    assert product.id == 1
    assert product.title == "Test Product"
    assert product.group_name == "Test Group"
    assert product.proteins.total == 10.0
    assert product.energy_value == 150.0
    assert product.water == 70.0


def test_product_suggestion_validation():
    suggestion = ProductSuggestion(
        id=1, title="Test Suggestion", group_name="Test Group"
    )
    assert suggestion.id == 1
    assert suggestion.title == "Test Suggestion"
    assert suggestion.group_name == "Test Group"


def test_pending_product_create_validation():
    # Проверка корректного создания
    pending = PendingProductCreate(name="New Product")
    assert pending.name == "New Product"

    # Проверка на пустую строку
    with pytest.raises(ValidationError) as exc_info:
        PendingProductCreate(name="")
    assert "String should have at least 3 characters" in str(exc_info.value)


def test_unified_product_response_validation():
    response = UnifiedProductResponse(
        exact_match=ProductDetailResponse(
            id=1,
            title="Test Product",
            group_name="Test Group",
            proteins=ProteinsSchema(total=10.0),
            fats=FatsSchema(total=5.0),
            carbs=CarbsSchema(total=20.0),
        ),
        suggestions=[
            ProductSuggestion(id=2, title="Similar Product", group_name="Test Group")
        ],
        needs_confirmation=True,
        pending_added=False,
    )

    assert response.exact_match.id == 1
    assert len(response.suggestions) == 1
    assert response.suggestions[0].title == "Similar Product"
    assert response.needs_confirmation is True
    assert response.pending_added is False


# Тесты на граничные случаи
def test_negative_values_validation():
    # Проверка отрицательного значения amount
    with pytest.raises(ValidationError) as exc_info:
        NutrientBase(amount=-1, name="Invalid", unit="g")
    assert "Input should be greater than 0" in str(exc_info.value)

    # Проверка отрицательного значения аминокислот
    with pytest.raises(ValidationError) as exc_info:
        AminoAcids(essential=-1.0, cond_essential=0.0, nonessential=0.0)
    assert "Input should be greater than 0" in str(exc_info.value)


# Тесты на валидацию вложенных объектов
def test_nested_validation():
    with pytest.raises(ValidationError):
        FatsSchema(total=10.0, breakdown="not a FatsDetail object")


# Тесты на значения по умолчанию
def test_default_values():
    product = ProductDetailResponse(
        id=1,
        title="Test",
        group_name="Test",
        proteins=ProteinsSchema(total=0),
        fats=FatsSchema(total=0),
        carbs=CarbsSchema(total=0),
    )

    assert product.vitamins.vits == []
    assert product.minerals.macro == []
    assert product.minerals.micro == []
    assert product.other.oths == []
    assert product.water == 0.0
    assert product.energy_value == 0.0
