from pathlib import Path

from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class AuthConfig(BaseModel):
    secret_key: str
    algorithm: str
    access_token_expires: int
    refresh_token_expires: int
    private_key_path: Path = BASE_DIR / "core" / "certs" / "jwt-private.pem"
    public_key_path: Path = BASE_DIR / "core" / "certs" / "jwt-public.pem"
