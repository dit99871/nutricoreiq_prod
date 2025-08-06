from fastapi import HTTPException, status


class ExpiredTokenException(HTTPException):
    """
    Исключение для случаев, когда токен истек
    """

    def __init__(
        self,
        detail: str = "Срок действия токена истек. Пожалуйста, войдите заново.",
    ):

        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
        )
