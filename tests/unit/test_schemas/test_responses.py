import pytest
from pydantic import ValidationError

from src.app.core.schemas.responses import SuccessResponse, ErrorDetail, ErrorResponse


def test_success_response_validation():
    # Проверка успешного создания ответа
    response = SuccessResponse(data={"message": "Success"}, meta={"count": 1})

    assert response.status == "success"
    assert response.data == {"message": "Success"}
    assert response.meta == {"count": 1}

    # Проверка с опциональным полем meta = None
    response = SuccessResponse(data={"message": "Success"})
    assert response.meta is None


def test_success_response_serialization():
    # Проверка сериализации в словарь
    response = SuccessResponse(data={"id": 1, "name": "Test"}, meta={"count": 1})

    result = response.model_dump()
    assert result == {
        "status": "success",
        "data": {"id": 1, "name": "Test"},
        "meta": {"count": 1},
    }


def test_error_detail_validation():
    # Проверка успешного создания деталей ошибки
    error = ErrorDetail(
        message="Validation error",
        details={"field": "email", "message": "Invalid format"},
    )

    assert error.message == "VALIDATION ERROR"
    assert error.details == {"field": "email", "message": "Invalid format"}

    # Проверка с опциональным полем details = None
    error = ErrorDetail(message="Not found")
    assert error.details is None


def test_error_detail_message_length_validation():
    # Проверка валидации длины сообщения (максимум 255 символов)
    with pytest.raises(ValidationError) as exc_info:
        ErrorDetail(message="x" * 256)

    assert "String should have at most 255 characters" in str(exc_info.value)


def test_error_response_validation():
    # Проверка успешного создания ответа с ошибкой
    response = ErrorResponse(
        error={"message": "Not found", "details": {"resource": "user", "id": 123}}
    )

    assert response.status == "error"
    assert response.error.message == "NOT FOUND"
    assert response.error.details == {"resource": "user", "id": 123}


def test_error_response_serialization():
    # Проверка сериализации в словарь
    response = ErrorResponse(
        error={"message": "Permission denied", "details": {"required": "admin"}}
    )

    result = response.model_dump()
    assert result == {
        "status": "error",
        "error": {
            "message": "PERMISSION DENIED",
            "details": {"required": "admin"}
        },
    }
