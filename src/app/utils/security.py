from secrets import token_hex


def generate_csrf_token() -> str:
    return token_hex(32)
