import pytest

from src.app.utils.case_converter import camel_case_to_snake_case


# Тесты для camel_case_to_snake_case
def test_camel_case_to_snake_case_some_sdk():
    """Тест из докстринга: SomeSDK -> some_sdk."""
    assert camel_case_to_snake_case("SomeSDK") == "some_sdk"


def test_camel_case_to_snake_case_r_servo_drive():
    """Тест из докстринга: RServoDrive -> r_servo_drive."""
    assert camel_case_to_snake_case("RServoDrive") == "r_servo_drive"


def test_camel_case_to_snake_case_sdk_demo():
    """Тест из докстринга: SDKDemo -> sdk_demo."""
    assert camel_case_to_snake_case("SDKDemo") == "sdk_demo"


def test_camel_case_to_snake_case_empty_string():
    """Тест на пустую строку."""
    assert camel_case_to_snake_case("") == ""


def test_camel_case_to_snake_case_no_uppercase():
    """Тест на строку без заглавных букв."""
    assert camel_case_to_snake_case("alreadylowercase") == "alreadylowercase"


def test_camel_case_to_snake_case_all_uppercase():
    """Тест на строку из заглавных букв."""
    assert camel_case_to_snake_case("ABC") == "abc"


def test_camel_case_to_snake_case_multiple_uppercase():
    """Тест на строку с несколькими последовательными заглавными буквами."""
    assert camel_case_to_snake_case("HTTPResponse") == "http_response"


def test_camel_case_to_snake_case_single_char():
    """Тест на строку из одного символа."""
    assert camel_case_to_snake_case("A") == "a"


def test_camel_case_to_snake_case_with_underscore():
    """Тест на строку, уже содержащую подчёркивание."""
    assert camel_case_to_snake_case("_someValue") == "_some_value"


def test_camel_case_to_snake_case_mixed_case():
    """Тест на строку с перемешанными регистрами и словами."""
    assert camel_case_to_snake_case("getUserIDByName") == "get_user_id_by_name"
