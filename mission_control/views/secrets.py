"""Secrets views."""

from fasthtml.common import *

from ..components import link, resource_table
from ..config import DEFAULT_NAMESPACE
from ..k8s import get_secrets


def secrets_content(namespace: str = DEFAULT_NAMESPACE):
    """Render the secrets list."""
    secrets = get_secrets(namespace)

    if not secrets:
        return Div(
            H2("Secrets"),
            P(f"No secrets found in the {namespace} namespace."),
        )

    headers = ["Name", "Type", "Keys", "Namespace", "Created"]
    rows = [_secret_row(secret) for secret in secrets]

    return Div(
        H2("Secrets"),
        resource_table(headers, rows),
    )


def _secret_row(secret: dict):
    """Render a single secret row."""
    return Tr(
        Td(link(secret["name"], f"/secret/{secret['namespace']}/{secret['name']}")),
        Td(secret["type"]),
        Td(secret["keys"]),
        Td(secret["namespace"]),
        Td(secret["created"]),
    )
