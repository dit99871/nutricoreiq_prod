from ipaddress import ip_address, ip_network

from fastapi import Request


def _is_trusted_proxy(peer_ip: str, trusted_proxies: list[str]) -> bool:
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


def get_client_ip(request: Request, trusted_proxies: list[str] | None = None) -> str:
    """
    Получает реальный IP-адрес клиента, учитывая заголовки прокси.

    Защита от X-Forwarded-For injection:
    если сканер передаёт "X-Forwarded-For: 127.0.0.1", nginx добавляет реальный IP
    следом ("127.0.0.1, 185.177.72.29"). Берём последний не-доверенный IP из списка,
    а не первый — это исключает подделку.

    :param request: FastAPI Request объект
    :param trusted_proxies: Список доверенных прокси (IP или CIDR-подсети)
    :return: Реальный IP-адрес клиента или "unknown"
    """
    trusted_proxies = trusted_proxies or []

    peer_ip = None
    if request.client and request.client.host:
        peer_ip = request.client.host

    # без явного списка доверенных прокси не доверяем заголовкам X-Forwarded-*.
    # это защищает от подделки при прямом доступе к приложению.
    if not trusted_proxies:
        request.state.client_ip = peer_ip or "unknown"
        return request.state.client_ip

    # если tcp-peer не является доверенным прокси — не доверяем заголовкам.
    if peer_ip and not _is_trusted_proxy(peer_ip, trusted_proxies):
        request.state.client_ip = peer_ip
        return peer_ip

    # X-Forwarded-For: идём с конца списка, пропуская trusted ip.
    # первый недоверенный ip справа — реальный клиент.
    # защита от injection: "X-Forwarded-For: 127.0.0.1, <real_ip>"
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        ips = [ip.strip() for ip in x_forwarded_for.split(",")]
        for ip in reversed(ips):
            try:
                ip_address(ip)  # валидируем формат
                if not _is_trusted_proxy(ip, trusted_proxies):
                    request.state.client_ip = ip
                    return ip
            except ValueError:
                continue

    # X-Real-IP — nginx ставит $remote_addr (не append-ит),
    # поэтому не подвержен injection как X-Forwarded-For.
    # возвращаем только если это не trusted proxy (не docker ip nginx).
    x_real_ip = request.headers.get("X-Real-IP")
    if x_real_ip:
        try:
            ip_address(x_real_ip)
            if not _is_trusted_proxy(x_real_ip, trusted_proxies):
                request.state.client_ip = x_real_ip
                return x_real_ip
        except ValueError:
            pass

    # fallback на tcp peer (ip самого прокси, если всё остальное не дало результата)
    if peer_ip:
        request.state.client_ip = peer_ip
        return peer_ip

    request.state.client_ip = "unknown"
    return "unknown"


def get_scheme_and_host(
    request: Request, trusted_proxies: list[str] | None = None
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
