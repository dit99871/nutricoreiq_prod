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


class TestNetworkEdgeCases:
    """Тесты для непокрытых веток в network.py."""

    def _make_request(self, headers=None, client_host="127.0.0.1"):
        request = MagicMock()
        request.client = MagicMock()
        request.client.host = client_host
        request.headers = headers or {}
        request.state = MagicMock()
        request.url.scheme = "http"
        request.url.hostname = "localhost"
        return request

    def test_is_trusted_proxy_cidr_match(self):
        """IP внутри CIDR подсети — доверенный прокси."""
        from src.app.core.utils.network import _is_trusted_proxy

        assert _is_trusted_proxy("192.168.1.50", ["192.168.1.0/24"]) is True

    def test_is_trusted_proxy_exact_ip_match(self):
        """Точное совпадение IP — доверенный прокси."""
        from src.app.core.utils.network import _is_trusted_proxy

        assert _is_trusted_proxy("10.0.0.1", ["10.0.0.1"]) is True

    def test_is_trusted_proxy_no_match(self):
        """IP не в списке доверенных прокси."""
        from src.app.core.utils.network import _is_trusted_proxy

        assert _is_trusted_proxy("8.8.8.8", ["10.0.0.0/8"]) is False

    def test_is_trusted_proxy_invalid_ip(self):
        """Невалидный IP — не является доверенным прокси."""
        from src.app.core.utils.network import _is_trusted_proxy

        assert _is_trusted_proxy("not-an-ip", ["10.0.0.0/8"]) is False

    def test_is_trusted_proxy_invalid_proxy_entry_skipped(self):
        """Невалидная запись в списке прокси пропускается без ошибок."""
        from src.app.core.utils.network import _is_trusted_proxy

        # Невалидный прокси-адрес просто игнорируется
        assert _is_trusted_proxy("10.0.0.1", ["invalid-entry", "10.0.0.1"]) is True

    def test_get_client_ip_no_client(self):
        """Без client.host возвращает 'unknown'."""
        from src.app.core.utils.network import get_client_ip

        request = MagicMock()
        request.client = None
        request.headers = {}
        request.state = MagicMock()

        ip = get_client_ip(request, trusted_proxies=[])
        assert ip == "unknown"

    def test_get_client_ip_x_forwarded_for_invalid_ips_skipped(self):
        """Невалидные IP в X-Forwarded-For пропускаются."""
        from src.app.core.utils.network import get_client_ip

        request = self._make_request(
            headers={"X-Forwarded-For": "invalid-ip, 1.2.3.4"},
            client_host="10.0.0.1",
        )
        ip = get_client_ip(request, trusted_proxies=["10.0.0.0/8"])
        assert ip == "1.2.3.4"

    def test_get_scheme_and_host_with_trusted_proxy(self):
        """С доверенным прокси берёт схему из X-Forwarded-Proto."""
        from src.app.core.utils.network import get_scheme_and_host

        request = self._make_request(
            headers={"X-Forwarded-Proto": "https", "Host": "example.com"},
            client_host="10.0.0.1",
        )
        scheme, host = get_scheme_and_host(request, trusted_proxies=["10.0.0.0/8"])
        assert scheme == "https"

    def test_get_scheme_and_host_with_x_forwarded_host(self):
        """С доверенным прокси берёт хост из X-Forwarded-Host."""
        from src.app.core.utils.network import get_scheme_and_host

        request = self._make_request(
            headers={
                "X-Forwarded-Proto": "https",
                "X-Forwarded-Host": "real.example.com, proxy.internal",
                "Host": "proxy.internal",
            },
            client_host="10.0.0.1",
        )
        scheme, host = get_scheme_and_host(request, trusted_proxies=["10.0.0.0/8"])
        assert host == "real.example.com"

    def test_get_scheme_and_host_without_trusted_proxy(self):
        """Без доверенного прокси берёт схему из URL."""
        from src.app.core.utils.network import get_scheme_and_host

        request = self._make_request(
            headers={"X-Forwarded-Proto": "https"},
            client_host="5.6.7.8",
        )
        # 5.6.7.8 не в списке доверенных → не доверяем заголовкам
        scheme, host = get_scheme_and_host(request, trusted_proxies=["10.0.0.0/8"])
        assert scheme == "http"  # из request.url.scheme


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
