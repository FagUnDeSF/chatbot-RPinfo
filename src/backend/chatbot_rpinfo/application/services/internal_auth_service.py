from __future__ import annotations

from collections.abc import Mapping
from secrets import compare_digest

from chatbot_rpinfo.domain.entities import AuthenticatedPrincipal
from chatbot_rpinfo.domain.repositories import InternalUserRepository


class AuthenticationError(Exception):
    """Raised when internal credentials cannot authenticate a nominative user."""


class InternalAuthService:
    def __init__(
        self,
        user_repository: InternalUserRepository,
        token_source: Mapping[str, str],
    ) -> None:
        self._user_repository = user_repository
        self._token_source = token_source

    def authenticate(self, username: str, token: str) -> AuthenticatedPrincipal:
        user = self._user_repository.get_by_username(username)
        if user is None:
            raise AuthenticationError("invalid_internal_credentials")

        expected_token = self._token_source.get(user.token_env_var)
        if expected_token is None or not compare_digest(token, expected_token):
            raise AuthenticationError("invalid_internal_credentials")

        return AuthenticatedPrincipal(user=user)
