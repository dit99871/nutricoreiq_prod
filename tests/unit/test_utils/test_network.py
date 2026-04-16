"""
Тесты для утилит работы с сетью (get_client_ip, get_scheme_and_host).
"""

from unittest.mock import MagicMock

from src.app.core.utils.network import get_client_ip, get_scheme_and_host


def make_request(
    headers: dict | None = None,
    client_host: str = "172.20.0.2",
) -> MagicMock:
    """Создаёт мок FastAPI Request."""
    request = MagicMock()
    request.client.host = client_host
    request.headers = headers or {}
    request.state = MagicMock()
    request.url.scheme = "http"
    request.url.hostname = "localhost"
    return request


DOCKER_SUBNET = ["172.20.0.0/16"]


# ─── no trusted proxies ───────────────────────────────────────────────────────


def test_no_trusted_proxies_returns_peer_ip():
    """Без trusted_proxies возвращает прямой IP."""
    request = make_request(
        headers={"X-Forwarded-For": "1.2.3.4"},
        client_host="5.6.7.8",
    )
    ip = get_client_ip(request, trusted_proxies=[])
    assert ip == "5.6.7.8"


def test_no_trusted_proxies_ignores_xff():
    """Без trusted_proxies X-Forwarded-For игнорируется."""
    request = make_request(
        headers={"X-Forwarded-For": "1.1.1.1"},
        client_host="5.6.7.8",
    )
    ip = get_client_ip(request)
    assert ip == "5.6.7.8"


# ─── peer not trusted ─────────────────────────────────────────────────────────


def test_peer_not_trusted_returns_peer_ip():
    """Если peer не в trusted_proxies — игнорируем заголовки."""
    request = make_request(
        headers={"X-Forwarded-For": "1.2.3.4"},
        client_host="10.0.0.5",  # не в Docker-подсети
    )
    ip = get_client_ip(request, trusted_proxies=DOCKER_SUBNET)
    assert ip == "10.0.0.5"


# ─── X-Forwarded-For injection protection ────────────────────────────────────


def test_xff_injection_takes_last_non_trusted():
    """Сканер подделывает первый IP — берём последний не-trusted."""
    request = make_request(
        headers={"X-Forwarded-For": "127.0.0.1, 185.177.72.29"},
        client_host="172.20.0.2",  # nginx в Docker
    )
    ip = get_client_ip(request, trusted_proxies=DOCKER_SUBNET)
    assert ip == "185.177.72.29"


def test_xff_single_ip():
    """Один IP в XFF — возвращаем его."""
    request = make_request(
        headers={"X-Forwarded-For": "5.6.7.8"},
        client_host="172.20.0.2",
    )
    ip = get_client_ip(request, trusted_proxies=DOCKER_SUBNET)
    assert ip == "5.6.7.8"


def test_xff_all_trusted_fallback_to_peer():
    """Если все IP в XFF — trusted, fallback на peer."""
    request = make_request(
        headers={"X-Forwarded-For": "172.20.0.3, 172.20.0.2"},
        client_host="172.20.0.2",
    )
    ip = get_client_ip(request, trusted_proxies=DOCKER_SUBNET)
    assert ip == "172.20.0.2"


def test_xff_multiple_real_ips_takes_rightmost():
    """Несколько реальных IP — берём крайний правый (ближайший к серверу)."""
    request = make_request(
        headers={"X-Forwarded-For": "1.1.1.1, 2.2.2.2, 172.20.0.3"},
        client_host="172.20.0.2",
    )
    ip = get_client_ip(request, trusted_proxies=DOCKER_SUBNET)
    assert ip == "2.2.2.2"


def test_xff_invalid_ip_skipped():
    """Невалидные IP в XFF пропускаются."""
    request = make_request(
        headers={"X-Forwarded-For": "not-an-ip, 5.6.7.8"},
        client_host="172.20.0.2",
    )
    ip = get_client_ip(request, trusted_proxies=DOCKER_SUBNET)
    assert ip == "5.6.7.8"


# ─── X-Real-IP ────────────────────────────────────────────────────────────────


def test_x_real_ip_used_when_no_xff():
    """X-Real-IP используется если нет XFF."""
    request = make_request(
        headers={"X-Real-IP": "5.6.7.8"},
        client_host="172.20.0.2",
    )
    ip = get_client_ip(request, trusted_proxies=DOCKER_SUBNET)
    assert ip == "5.6.7.8"


def test_x_real_ip_trusted_skipped():
    """X-Real-IP совпадает с trusted proxy — не возвращаем его."""
    request = make_request(
        headers={"X-Real-IP": "172.20.0.3"},  # Docker IP nginx
        client_host="172.20.0.2",
    )
    # нет XFF и X-Real-IP тоже trusted → fallback на peer
    ip = get_client_ip(request, trusted_proxies=DOCKER_SUBNET)
    assert ip == "172.20.0.2"


def test_x_real_ip_invalid_skipped():
    """Невалидный X-Real-IP пропускается."""
    request = make_request(
        headers={"X-Real-IP": "not-an-ip"},
        client_host="172.20.0.2",
    )
    ip = get_client_ip(request, trusted_proxies=DOCKER_SUBNET)
    assert ip == "172.20.0.2"


# ─── fallback ─────────────────────────────────────────────────────────────────


def test_no_client_returns_unknown():
    """Нет client — возвращает 'unknown'."""
    request = MagicMock()
    request.client = None
    request.headers = {}
    request.state = MagicMock()
    ip = get_client_ip(request, trusted_proxies=[])
    assert ip == "unknown"


# ─── get_scheme_and_host ──────────────────────────────────────────────────────


def test_scheme_from_x_forwarded_proto_when_trusted():
    """X-Forwarded-Proto учитывается если peer trusted."""
    request = make_request(
        headers={"X-Forwarded-Proto": "https", "Host": "nutricoreiq.ru"},
        client_host="172.20.0.2",
    )
    scheme, host = get_scheme_and_host(request, trusted_proxies=DOCKER_SUBNET)
    assert scheme == "https"


def test_scheme_ignored_when_peer_not_trusted():
    """X-Forwarded-Proto игнорируется если peer не trusted."""
    request = make_request(
        headers={"X-Forwarded-Proto": "https"},
        client_host="5.6.7.8",
    )
    scheme, host = get_scheme_and_host(request, trusted_proxies=DOCKER_SUBNET)
    assert scheme == "http"  # из request.url.scheme
