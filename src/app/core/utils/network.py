from ipaddress import ip_address, ip_network
from typing import List, Optional

from fastapi import Request


def _is_trusted_proxy(peer_ip: str, trusted_proxies: List[str]) -> bool:
    """
    Проверяет, является ли IP-адрес доверенным прокси.

    :param peer_ip: IP-адрес для проверки
    :param trusted_proxies: Список доверенных прокси (IP или подсети)
    :return: True если IP является доверенным прокси
    """
    try:
        peer = ip_address(peer_ip)
    except ValueError:
        return False

    for proxy in trusted_proxies:
        try:
            if "/" in proxy:
                if peer in ip_network(proxy, strict=False):
                    return True
            else:
                if peer == ip_address(proxy):
                    return True
        except ValueError:
            continue

    return False


def get_client_ip(request: Request, trusted_proxies: Optional[List[str]] = None) -> str:
    """
    Получает реальный IP-адрес клиента, учитывая заголовки прокси.

    :param request: FastAPI Request объект
    :param trusted_proxies: Список доверенных прокси
    :return: Реальный IP-адрес клиента или "unknown"
    """
    trusted_proxies = trusted_proxies or []

    peer_ip = None
    if request.client and request.client.host:
        peer_ip = request.client.host

    # без явного списка доверенных прокси не доверяем заголовкам X-Forwarded-*.
    # это защищает от подделки X-Forwarded-For при прямом доступе к приложению.
    if not trusted_proxies:
        request.state.client_ip = peer_ip or "unknown"
        return request.state.client_ip

    # если peer не является доверенным прокси, не используем X-Forwarded-*.
    if peer_ip and not _is_trusted_proxy(peer_ip, trusted_proxies):
        request.state.client_ip = peer_ip
        return peer_ip

    # список заголовков, в которых может быть реальный ip
    headers_to_check = [
        "X-Forwarded-For",
        "X-Real-IP",
        "X-Client-IP",
        "HTTP_X_FORWARDED_FOR",
        "HTTP_X_REAL_IP",
    ]

    for header in headers_to_check:
        if header in request.headers:
            # берем первый ip из списка, если их несколько
            ip = request.headers[header].split(",")[0].strip()
            try:
                # валидируем, что это корректный ip-адрес
                ip_address(ip)
                request.state.client_ip = ip
                return ip
            except ValueError:
                continue

    # eсли заголовков нет, используем стандартный способ
    if peer_ip:
        request.state.client_ip = peer_ip
        return peer_ip

    request.state.client_ip = "unknown"
    return "unknown"


def get_scheme_and_host(
    request: Request, trusted_proxies: Optional[List[str]] = None
) -> tuple[str, str]:
    trusted_proxies = trusted_proxies or []

    scheme = request.url.scheme
    host = request.headers.get("Host", "") or (request.url.hostname or "")

    peer_ip = None
    if request.client and request.client.host:
        peer_ip = request.client.host

    if trusted_proxies and peer_ip and _is_trusted_proxy(peer_ip, trusted_proxies):
        scheme = request.headers.get("X-Forwarded-Proto", scheme)
        host = request.headers.get("X-Forwarded-Host", "").split(",")[0].strip() or host

    request.state.scheme = scheme
    request.state.host = host

    return scheme, host
