from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class InternalRole(StrEnum):
    DIRECAO = "direcao"
    COMERCIAL = "comercial"
    PREVENCAO = "prevencao"
    ADMIN_TECNICO = "admin-tecnico"


@dataclass(frozen=True, slots=True)
class InternalUser:
    username: str
    display_name: str
    role: InternalRole
    token_env_var: str


@dataclass(frozen=True, slots=True)
class AuthenticatedPrincipal:
    user: InternalUser
