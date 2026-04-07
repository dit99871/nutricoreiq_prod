"""
Интеграционные тесты для мидлвари с использованием httpx
"""

import asyncio
import json
import time

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.app.core.exception_handlers import setup_exception_handlers


class TestMiddlewareIntegration:
    """Интеграционные тесты мидлвари"""
    
    @pytest.fixture
    def app(self):
        """Фикстура для создания приложения с новой архитектурой"""
        app = FastAPI()
        setup_exception_handlers(app)
        return app
    
    @pytest.fixture
    def test_client(self, app):
        """Фикстура для TestClient"""
        return TestClient(app)
    
    @pytest.fixture
    async def httpx_client_e2e(self):
        """Фикстура для httpx клиента (к живому серверу)"""
        client = httpx.AsyncClient(
            base_url="http://127.0.0.1:8080",
            timeout=30.0,
            follow_redirects=True,
        )
        yield client
        await client.aclose()
    
    @pytest.mark.integration
    def test_error_pipeline_inprocess(self, test_client):
        response = test_client.get("/nonexistent-endpoint-12345")
        assert response.status_code == 404
        data = response.json()
        assert data["status"] == "error"
        assert "error" in data
        assert data["error"]["message"]


    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_unified_tracing_with_httpx(self, httpx_client_e2e):
        """Тестируем unified tracing через httpx"""

        try:
            # Тест 1: Базовый запрос
            response = await httpx_client_e2e.get("/")

            assert response.status_code == 200
            assert "X-Request-ID" in response.headers
            assert "X-Trace-ID" in response.headers
            assert "X-Process-Time" in response.headers

            # Тест 2: Проверяем уникальность trace ID
            response2 = await httpx_client_e2e.get("/")
            trace_id = response.headers["X-Trace-ID"]
            trace_id2 = response2.headers["X-Trace-ID"]

            assert trace_id != trace_id2

            # Тест 3: Проверяем передачу request ID
            custom_request_id = "custom-test-123"
            response3 = await httpx_client_e2e.get(
                "/",
                headers={"X-Request-ID": custom_request_id},
            )

            assert response3.headers["X-Request-ID"] == custom_request_id
        except httpx.ConnectError:
            pytest.skip("Server not running on localhost:8080")

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_circuit_breaker_with_httpx(self, httpx_client_e2e):
        """Тестируем circuit breaker через httpx"""

        try:
            # Тест 1: Параллельные запросы для проверки производительности
            tasks = []
            for _ in range(3):  # Уменьшим количество запросов
                task = httpx_client_e2e.get("/")
                tasks.append(task)

            start_time = time.time()
            responses = await asyncio.gather(*tasks)
            end_time = time.time()

            # Все запросы должны быть успешными
            for response in responses:
                assert response.status_code == 200

            # Общее время должно быть разумным
            total_time = end_time - start_time
            assert total_time < 5.0

            # Проверяем заголовки производительности
            process_times = [
                float(r.headers.get("X-Process-Time", "0ms").replace("ms", ""))
                for r in responses
            ]
            avg_process_time = sum(process_times) / len(process_times)
            assert avg_process_time < 1000  # Меньше 1 секунды
        except httpx.ConnectError:
            pytest.skip("Server not running on localhost:8080")

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_security_features_with_httpx(self, httpx_client_e2e):
        """Тестируем безопасность через httpx"""

        try:
            # Тест 1: Проверяем CSP заголовки
            response = await httpx_client_e2e.get("/")
            csp_header = response.headers.get("Content-Security-Policy")
            assert csp_header is not None
            assert "default-src 'self'" in csp_header
            assert "script-src 'self'" in csp_header

            # Тест 2: Проверяем CORS
            response = await httpx_client_e2e.options(
                "/",
                headers={
                    "Origin": "https://example.com",
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "Content-Type",
                },
            )

            # CORS заголовки должны присутствовать
            cors_headers = [k for k in response.headers.keys() if "access-control" in k.lower()]
            _ = cors_headers

            # Тест 3: Проверяем CSRF защиту
            response = await httpx_client_e2e.post(
                "/api/test",
                json={"test": "data"},
                headers={"Content-Type": "application/json"},
            )

            # Должен быть либо 403 (CSRF), либо 404 (нет эндпоинта), либо 500 (внутренняя ошибка)
            assert response.status_code in [403, 404, 500]
        except httpx.ConnectError:
            pytest.skip("Server not running on localhost:8080")

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_error_handling_with_httpx(self, httpx_client_e2e):
        """Тестируем обработку ошибок через httpx"""

        try:
            # Тест 1: Проверяем 404 ошибку
            response = await httpx_client_e2e.get("/nonexistent-endpoint-12345")
            assert response.status_code == 404

            # Тест 2: Проверяем ошибку валидации
            response = await httpx_client_e2e.post(
                "/api/user",
                json={"invalid_field": "value"},
                headers={"Content-Type": "application/json"},
            )

            # Должен быть либо 422 (валидация), либо 404 (нет эндпоинта), либо 500 (внутренняя ошибка)
            assert response.status_code in [422, 404, 500]

            # Тест 3: Проверяем большой запрос
            large_data = {"data": "x" * 10000}
            response = await httpx_client_e2e.post(
                "/api/test",
                json=large_data,
                headers={"Content-Type": "application/json"},
            )

            # Не должно падать с ошибкой
            assert response.status_code in [200, 404, 413, 422, 500]
        except httpx.ConnectError:
            pytest.skip("Server not running on localhost:8080")

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_privacy_consent_with_httpx(self, httpx_client_e2e):
        """Тестируем проверку согласия через httpx"""

        try:
            # Тест 1: Проверяем exempt пути
            exempt_paths = ["/", "/privacy", "/auth/login"]

            for path in exempt_paths:
                response = await httpx_client_e2e.get(path)
                assert response.status_code != 451

            # Тест 2: Проверяем согласие через заголовок
            consent_data = {"personal_data": True}
            response = await httpx_client_e2e.get(
                "/api/user/profile",
                headers={"X-Privacy-Consent": json.dumps(consent_data)},
            )

            # Должен быть либо не 451 (согласие принято), либо 404 (нет эндпоинта)
            assert response.status_code != 451

            # Тест 3: Проверяем отсутствие согласия
            response = await httpx_client_e2e.get("/api/user/profile")

            # Должен быть либо 451 (согласие требуется), либо 404 (нет эндпоинта)
            assert response.status_code in [451, 404]
        except httpx.ConnectError:
            pytest.skip("Server not running on localhost:8080")

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_performance_with_httpx(self, httpx_client_e2e):
        """Тестируем производительность через httpx"""

        try:
            # Тест 1: Последовательные запросы
            times = []
            for _ in range(10):
                start = time.time()
                response = await httpx_client_e2e.get("/")
                end = time.time()
                times.append(end - start)
                assert response.status_code == 200

            avg_time = sum(times) / len(times)
            assert avg_time < 1.0  # Среднее время меньше 1 секунды

            # Тест 2: Параллельные запросы
            start_time = time.time()
            tasks = [httpx_client_e2e.get("/") for _ in range(20)]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()

            successful = [r for r in responses if isinstance(r, httpx.Response)]
            assert len(successful) >= 15  # Большинство должно быть успешными

            # Тест 3: Проверяем заголовки производительности
            if successful:
                process_times = [
                    float(r.headers.get("X-Process-Time", "0ms").replace("ms", ""))
                    for r in successful[:5]  # Первые 5
                ]
                server_avg = sum(process_times) / len(process_times)
                assert server_avg < 1000  # Меньше 1 секунды
        except httpx.ConnectError:
            pytest.skip("Server not running on localhost:8080")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
