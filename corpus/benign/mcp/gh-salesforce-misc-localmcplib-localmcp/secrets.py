"""Logical secret references resolved from environment variables and keyring."""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol

from localmcp.config import validate_identifier

_SECRET_DECLARATION_FIELDS = frozenset({"disabled", "env_vars", "name"})


class SecretError(RuntimeError):
    """Base error for secret declarations and resolution."""


class SecretNotFoundError(SecretError):
    """Raised when a required logical secret is unavailable."""


class SecretBackendError(SecretError):
    """Raised when a configured secret backend fails."""


class SecretSource(StrEnum):
    ENV = "env"
    KEYRING = "keyring"


@dataclass(frozen=True)
class SecretRef:
    """A non-secret, portable description of one logical secret.

    A missing server selects the globally shared ``localmcp`` keyring service;
    a server name selects ``localmcp:<server>``. Environment aliases remain an
    application/deployment concern and are checked in their declared order
    before keyring.
    """

    name: str
    server: str | None = None
    env_vars: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.server is not None:
            validate_identifier(self.server, field="server")
        validate_identifier(self.name, field="secret name")
        if any(not value or not value.strip() for value in self.env_vars):
            raise SecretError("secret environment variable names must not be blank")


@dataclass(frozen=True)
class ResolvedSecret:
    """A secret value whose representation never reveals its contents."""

    _value: str
    source: SecretSource
    reference: SecretRef

    def reveal(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return f"ResolvedSecret(source={self.source.value!r}, reference={self.reference!r}, value=<redacted>)"

    def __str__(self) -> str:
        return "<redacted>"


KeyringGetter = Callable[[str, str], str | None]


class SecretConfigDocument(Protocol):
    def secret_mappings(self, server: str | None = None) -> dict[str, dict[str, Any]]: ...


class SecretCatalog:
    """Logical secret declarations composed from one localmcp document."""

    def __init__(self, references: Mapping[str, SecretRef]):
        self._references = dict(references)

    @classmethod
    def from_config(cls, config: SecretConfigDocument, *, server: str | None = None) -> SecretCatalog:
        if server is not None:
            validate_identifier(server, field="server")
        global_mappings = config.secret_mappings()
        mappings = global_mappings if server is None else config.secret_mappings(server)
        references: dict[str, SecretRef] = {}
        for logical_name, values in mappings.items():
            unsupported = set(values) - _SECRET_DECLARATION_FIELDS
            if unsupported:
                raise SecretError(f"secret {logical_name} has unsupported fields: {', '.join(sorted(unsupported))}")
            if values.get("disabled") is True:
                continue
            secret_name = values.get("name", logical_name)
            env_vars = values.get("env_vars", ())
            if not isinstance(secret_name, str):
                raise SecretError(f"secret {logical_name} name must be a string")
            if not isinstance(env_vars, list | tuple) or not all(isinstance(item, str) for item in env_vars):
                raise SecretError(f"secret {logical_name} env_vars must be an array of strings")
            references[logical_name] = SecretRef(
                name=secret_name,
                server=None if logical_name in global_mappings else server,
                env_vars=tuple(env_vars),
            )
        return cls(references)

    def get(self, logical_name: str) -> SecretRef | None:
        return self._references.get(logical_name)

    def require(self, logical_name: str) -> SecretRef:
        try:
            return self._references[logical_name]
        except KeyError as exc:
            raise SecretError(f"secret declaration not found: {logical_name}") from exc

    def as_mapping(self) -> Mapping[str, SecretRef]:
        return dict(self._references)


class SecretResolver:
    """Resolve caller-declared secrets without owning an application catalog."""

    def __init__(
        self,
        env: Mapping[str, str] | None = None,
        *,
        keyring_getter: KeyringGetter | None = None,
        tolerate_keyring_errors: bool = False,
    ) -> None:
        self._env = os.environ if env is None else env
        self._keyring_getter = keyring_getter
        self._tolerate_keyring_errors = tolerate_keyring_errors

    def get(self, reference: SecretRef) -> ResolvedSecret | None:
        value = self._from_env(reference)
        if value is not None:
            return ResolvedSecret(value, SecretSource.ENV, reference)
        value = self._from_keyring(reference)
        return None if value is None else ResolvedSecret(value, SecretSource.KEYRING, reference)

    def require(self, reference: SecretRef) -> ResolvedSecret:
        value = self.get(reference)
        if value is not None:
            return value
        aliases = ", ".join(reference.env_vars) or "none"
        service, account = _keyring_location(reference)
        scope = reference.server or "global"
        raise SecretNotFoundError(
            f"secret {scope}/{reference.name} was not found; "
            f"environment aliases: {aliases}; keyring service/account: "
            f"{service}/{account}"
        )

    def _from_env(self, reference: SecretRef) -> str | None:
        for name in reference.env_vars:
            value = self._env.get(name)
            if value and value.strip():
                return value
        return None

    def _from_keyring(self, reference: SecretRef) -> str | None:
        getter = self._keyring_getter
        keyring_error: type[BaseException]
        if getter is None:
            import keyring
            import keyring.errors

            getter = keyring.get_password
            keyring_error = keyring.errors.KeyringError
        else:
            keyring_error = Exception
        service, account = _keyring_location(reference)
        try:
            value = getter(service, account)
        except keyring_error as exc:
            if self._tolerate_keyring_errors:
                return None
            scope = reference.server or "global"
            raise SecretBackendError(
                f"keyring lookup failed for {scope}/{reference.name}: {type(exc).__name__}"
            ) from exc
        return value if value and value.strip() else None


def _keyring_location(reference: SecretRef) -> tuple[str, str]:
    service = "localmcp" if reference.server is None else f"localmcp:{reference.server}"
    return service, reference.name
