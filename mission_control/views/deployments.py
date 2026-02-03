"""Deployments views."""

from fasthtml.common import *

from ..components import link, resource_table
from ..config import DEFAULT_NAMESPACE
from ..k8s import get_deployments


def deployments_content(namespace: str = DEFAULT_NAMESPACE):
    """Render the deployments list."""
    deployments = get_deployments(namespace)

    if not deployments:
        return Div(
            H2("Deployments"),
            P(f"No deployments found in the {namespace} namespace."),
        )

    headers = ["Name", "Replicas", "Image", "Namespace", "Created"]
    rows = [_deployment_row(deployment) for deployment in deployments]

    return Div(
        H2("Deployments"),
        resource_table(headers, rows),
    )


def _deployment_row(deployment: dict):
    """Render a single deployment row."""
    return Tr(
        Td(link(deployment["name"], f"/deployment/{deployment['namespace']}/{deployment['name']}")),
        Td(deployment["replicas"]),
        Td(deployment["image"]),
        Td(deployment["namespace"]),
        Td(deployment["created"]),
    )
