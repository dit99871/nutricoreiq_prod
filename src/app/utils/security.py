from secrets import token_hex, token_urlsafe


def generate_csrf_token() -> str:
    return token_hex(32)


def generate_csp_nonce() -> str:
    return token_urlsafe(32)
