from db.models import Product
from db.models.nutrient import NutrientCategory
from schemas.product import NutrientBase, ProductDetailResponse


def map_to_schema(product: Product) -> ProductDetailResponse:
    """
    Maps a `Product` object to a `ProductDetailResponse` object.

    Iterates over the product's nutrient associations and maps the nutrient
    amounts to the corresponding fields in the response object.

    :param product: The product to map.
    :return: The mapped response object.
    """
    response = ProductDetailResponse(
        id=product.id,
        title=product.title,
        group_name=product.product_groups.name,
    )

    for assoc in product.nutrient_associations:
        nutrient = assoc.nutrients
        amount = assoc.amount
        unit = nutrient.unit

        # Обработка макронутриентов
        if nutrient.category == NutrientCategory.MACRO:
            if "белки" in nutrient.name.lower():
                response.proteins.total = amount
            elif "жиры" in nutrient.name.lower():
                response.fats.total = amount
            elif "углеводы" in nutrient.name.lower():
                response.carbs.total = amount
            elif "вода" in nutrient.name.lower():
                response.water.total = amount

        # Обработка аминокислот
        elif nutrient.category == NutrientCategory.ESSENTIAL_AMINO:
            response.proteins.amino_acids.essential += amount

        elif nutrient.category == NutrientCategory.COND_ESSENTIAL_AMINO:
            response.proteins.amino_acids.cond_essential += amount

        elif nutrient.category == NutrientCategory.NONESSENTIAL_AMINO:
            response.proteins.amino_acids.nonessential += amount

        # Обработка жиров
        elif nutrient.category == NutrientCategory.SATURATED_FATS:
            if "холестерин" in nutrient.name.lower():
                response.fats.breakdown.cholesterol = amount
            else:
                response.fats.breakdown.saturated += amount

        elif nutrient.category == NutrientCategory.MONOUNSATURATED_FATS:
            response.fats.breakdown.monounsaturated += amount

        elif nutrient.category == NutrientCategory.POLYUNSATURATED_FATS:
            if "полиненасыщенные" in nutrient.name.lower():
                response.fats.breakdown.polyunsaturated.total = amount
            elif "омега-3" in nutrient.name.lower():
                response.fats.breakdown.polyunsaturated.omega3 = amount
            elif "омега-6" in nutrient.name.lower():
                response.fats.breakdown.polyunsaturated.omega6 = amount

        # Обработка углеводов
        elif nutrient.category == NutrientCategory.CARBS:
            if "клетчатка" in nutrient.name.lower():
                response.carbs.breakdown.fiber = amount
            elif "сахар" in nutrient.name.lower():
                response.carbs.breakdown.sugar = amount

        # Витамины
        elif nutrient.category == NutrientCategory.VITAMINS:
            response.vitamins.vits.append(
                NutrientBase(name=nutrient.name, amount=amount, unit=unit)
            )

        # Витаминоподобные
        elif nutrient.category == NutrientCategory.VITAMIN_LIKE:
            response.vitamin_like.vitslk.append(
                NutrientBase(name=nutrient.name, amount=amount, unit=unit)
            )

        # Минералы
        elif nutrient.category == NutrientCategory.MINERALS_MACRO:
            response.minerals.macro.append(
                NutrientBase(name=nutrient.name, amount=amount, unit=unit)
            )

        elif nutrient.category == NutrientCategory.MINERALS_MICRO:
            response.minerals.micro.append(
                NutrientBase(name=nutrient.name, amount=amount, unit=unit)
            )

        # Прочие нутриенты
        elif nutrient.category == NutrientCategory.OTHER:
            response.other.oths.append(
                NutrientBase(name=nutrient.name, amount=amount, unit=unit)
            )

    return response
