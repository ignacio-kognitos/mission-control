"""Book Connections views."""

from fasthtml.common import *

from ..components import filterable_table, link
from ..config import DEFAULT_NAMESPACE
from ..k8s import get_book_connections, get_kube_contexts, get_pod_metrics


def book_connections_content(namespace: str = DEFAULT_NAMESPACE, url: str = ""):
    """Render the book connections list."""
    _, current_context = get_kube_contexts()
    connections = get_book_connections(namespace)

    inputs = _inputs(namespace, url, current_context)

    if not connections:
        return Div(
            H2("Book Connections"),
            *inputs,
            P(f"No book connections found in the {namespace} namespace."),
        )

    headers = ["Resource Name", "Name", "Version", "Namespace", "Created", "Actions"]
    rows = [book_connection_row(conn) for conn in connections]

    return Div(
        H2("Book Connections"),
        *inputs,
        filterable_table(headers, rows, "book-connections-table"),
    )


def _inputs(namespace: str, url: str, current_context: str | None):
    """Render URL and namespace inputs."""
    url_input = Div(
        Label("URL:", fr="url-input"),
        Input(
            type="text",
            name="url",
            value=url,
            id="url-input",
            placeholder="https://app.us-1.dev.kognitos.com/organizations/.../workspaces/.../apps",
            hx_get="/book-connections-from-url",
            hx_target="#main-content",
            hx_swap="innerHTML",
            hx_trigger="change",
            style="flex: 1; margin-left: 0.5rem; min-width: 300px;",
        ),
        style="display: flex; align-items: center; margin-bottom: 0.5rem;",
    )

    namespace_input = Div(
        Label("Namespace:", fr="namespace-input"),
        Input(
            type="text",
            name="namespace",
            value=namespace,
            id="namespace-input",
            hx_get="/book-connections",
            hx_target="#main-content",
            hx_swap="innerHTML",
            hx_trigger="change",
            style="width: 200px; margin-left: 0.5rem;",
        ),
        Span(
            f"(context: {current_context})",
            style="margin-left: 1rem; color: var(--pico-muted-color); font-size: 0.85rem;",
        ),
        style="display: flex; align-items: center; margin-bottom: 1rem;",
    )

    return [url_input, namespace_input]


def book_connection_row(conn: dict):
    """Render a single book connection row."""
    row_id = f"bc-row-{conn['namespace']}-{conn['name']}"

    return Tr(
        Td(link(conn["name"], f"/book-connection/{conn['namespace']}/{conn['name']}")),
        Td(conn["label_name"]),
        Td(conn["label_version"]),
        Td(conn["namespace"]),
        Td(conn["created"]),
        Td(
            A(
                "View Pod",
                hx_get=f"/book-connection-pod/{conn['namespace']}/{conn['name']}",
                hx_target=f"#{row_id}",
                hx_swap="outerHTML",
                style="cursor: pointer; text-decoration: underline; color: var(--pico-primary);",
            )
        ),
        id=row_id,
    )


def book_connection_row_expanded(conn: dict, pod: dict | None):
    """Render an expanded book connection row with pod info."""
    row_id = f"bc-row-{conn['namespace']}-{conn['name']}"

    if not pod:
        return _no_pod_row(row_id, conn)

    metrics = get_pod_metrics(pod["name"], pod["namespace"])
    metrics_section = _metrics_section(metrics)

    return Tr(
        Td(
            Div(
                Div(Strong("Pod: "), pod["name"], style="margin-right: 1rem;"),
                Div(Strong("Status: "), pod["phase"], style="margin-right: 1rem;"),
                *metrics_section,
                style="display: flex; flex-wrap: wrap; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;",
            ),
            Div(
                link("View Manifest", f"/pod/{pod['namespace']}/{pod['name']}"),
                link("View Logs", f"/pod-logs/{pod['namespace']}/{pod['name']}"),
                A(
                    "Collapse",
                    hx_get=f"/book-connection-row/{conn['namespace']}/{conn['name']}",
                    hx_target=f"#{row_id}",
                    hx_swap="outerHTML",
                    style="cursor: pointer; text-decoration: underline; color: var(--pico-muted-color); margin-left: 1rem;",
                ),
                style="display: flex; flex-wrap: wrap; align-items: center; gap: 1rem;",
            ),
            colspan="6",
            style="padding: 0.5rem; background: var(--pico-code-background-color);",
        ),
        id=row_id,
    )


def _no_pod_row(row_id: str, conn: dict):
    """Render a row when no pod is found."""
    return Tr(
        Td(
            Div(
                Span("No associated pod found", style="color: var(--pico-muted-color); margin-right: 1rem;"),
                A(
                    "Collapse",
                    hx_get=f"/book-connection-row/{conn['namespace']}/{conn['name']}",
                    hx_target=f"#{row_id}",
                    hx_swap="outerHTML",
                    style="cursor: pointer; text-decoration: underline; color: var(--pico-muted-color);",
                ),
                style="display: flex; align-items: center;",
            ),
            colspan="6",
            style="padding: 0.5rem; background: var(--pico-code-background-color);",
        ),
        id=row_id,
    )


def _metrics_section(metrics: dict | None) -> list:
    """Render metrics section."""
    if not metrics:
        return [Div(Span("Metrics not available", style="color: var(--pico-muted-color);"))]

    return [
        Div(
            Strong(f"{c['name']}: "),
            f"CPU: {c['cpu']}, Memory: {c['memory']}",
            style="margin-right: 1rem;",
        )
        for c in metrics["containers"]
    ]
