from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, SecretStr

from chatbot_rpinfo.domain.entities import AuthenticatedPrincipal, InternalRole


class InternalLoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    username: str = Field(min_length=3, max_length=64, pattern=r"^[a-z0-9_.-]+$")
    access_token: SecretStr = Field(min_length=1, max_length=256)


class InternalUserResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    username: str
    display_name: str
    role: InternalRole

    @classmethod
    def from_principal(cls, principal: AuthenticatedPrincipal) -> InternalUserResponse:
        return cls(
            username=principal.user.username,
            display_name=principal.user.display_name,
            role=principal.user.role,
        )
