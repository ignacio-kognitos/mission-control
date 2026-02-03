"""Trigger Instances views."""

from fasthtml.common import *

from ..components import link, resource_table
from ..config import DEFAULT_NAMESPACE
from ..k8s import get_trigger_instances


def trigger_instances_content(namespace: str = DEFAULT_NAMESPACE):
    """Render the trigger instances list."""
    instances = get_trigger_instances(namespace)

    if not instances:
        return Div(
            H2("Trigger Instances"),
            P(f"No trigger instances found in the {namespace} namespace."),
        )

    headers = ["Resource Name", "Name", "Version", "Namespace", "Created"]
    rows = [_trigger_instance_row(instance) for instance in instances]

    return Div(
        H2("Trigger Instances"),
        resource_table(headers, rows),
    )


def _trigger_instance_row(instance: dict):
    """Render a single trigger instance row."""
    return Tr(
        Td(link(instance["name"], f"/trigger-instance/{instance['namespace']}/{instance['name']}")),
        Td(instance["label_name"]),
        Td(instance["label_version"]),
        Td(instance["namespace"]),
        Td(instance["created"]),
    )
