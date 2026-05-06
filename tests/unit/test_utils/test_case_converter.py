class TestCaseConverter:
    """Тесты для case_converter."""

    def test_camel_to_snake_basic(self):
        """CamelCase → snake_case."""
        from src.app.core.utils.case_converter import camel_case_to_snake_case

        assert camel_case_to_snake_case("HelloWorld") == "hello_world"

    def test_camel_to_snake_single_word(self):
        """Одно слово остаётся без изменений (в нижнем регистре)."""
        from src.app.core.utils.case_converter import camel_case_to_snake_case

        assert camel_case_to_snake_case("Hello") == "hello"

    def test_camel_to_snake_abbreviation(self):
        """Аббревиатуры обрабатываются корректно."""
        from src.app.core.utils.case_converter import camel_case_to_snake_case

        assert camel_case_to_snake_case("SomeSDK") == "some_sdk"

    def test_camel_to_snake_sdk_demo(self):
        """SDKDemo → sdk_demo."""
        from src.app.core.utils.case_converter import camel_case_to_snake_case

        assert camel_case_to_snake_case("SDKDemo") == "sdk_demo"
