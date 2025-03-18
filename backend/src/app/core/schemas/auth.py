from pydantic import BaseModel, EmailStr


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class TokenPayload(BaseModel):
    sub: EmailStr
    exp: int
    role: str  # Добавляем роль пользователя


class UserLogin(BaseModel):
    email: EmailStr
    password: str
