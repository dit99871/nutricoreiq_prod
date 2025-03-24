from .base import Base
from .mixins import IntIdPkMixin


class JWTBlacklist(IntIdPkMixin, Base):
    jti: str
