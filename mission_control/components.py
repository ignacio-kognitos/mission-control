"""Reusable UI components."""

from fasthtml.common import *

from .k8s import get_kube_contexts

# -----------------------------------------------------------------------------
# Layout
# -----------------------------------------------------------------------------


def page_layout(*content):
    """Render the full page layout with sidebar."""
    return Div(
        Div(id="global-loader", style="display: none;"),
        _header(),
        Div(
            sidebar(),
            Main(
                *content,
                id="main-content",
                style="flex: 1; padding: 0.5rem; overflow: hidden; min-width: 0;",
            ),
            style="display: flex; flex: 1;",
        ),
        Div(id="modal-container"),
        style="display: flex; flex-direction: column; min-height: 100vh;",
    )


def _header():
    """Render the header bar."""
    return Div(
        Div(
            Img(
                src="/static/logo.jpg",
                alt="Mission Control",
                style="height: 32px; width: 32px; border-radius: 4px;",
            ),
            Span("Mission Control", style="font-weight: bold; font-size: 1.1rem; margin-left: 0.5rem;"),
            style="display: flex; align-items: center;",
        ),
        context_dropdown(),
        style="display: flex; justify-content: space-between; align-items: center; padding: 0.5rem; border-bottom: 1px solid var(--pico-muted-border-color);",
    )


def sidebar():
    """Render the left sidebar with resource navigation."""
    return Nav(
        Ul(
            Li(A("Books", hx_get="/books", hx_target="#main-content", hx_swap="innerHTML", hx_push_url="true")),
            Li(
                A(
                    "Book Connections",
                    hx_get="/book-connections",
                    hx_target="#main-content",
                    hx_swap="innerHTML",
                    hx_push_url="true",
                )
            ),
            style="list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 0.5rem;",
        ),
        style="min-width: 180px; padding: 0.5rem; border-right: 1px solid var(--pico-muted-border-color);",
    )


# -----------------------------------------------------------------------------
# Context Dropdown
# -----------------------------------------------------------------------------


def context_dropdown():
    """Render the kube context dropdown."""
    contexts, current = get_kube_contexts()
    return Select(
        *[Option(ctx, value=ctx, selected=(ctx == current)) for ctx in contexts],
        name="context",
        hx_post="/switch-context",
        hx_on__after_request="window.location.reload()",
        id="context-dropdown",
        style="min-width: 200px;",
    )


def context_dropdown_oob():
    """Render the kube context dropdown with out-of-band swap."""
    contexts, current = get_kube_contexts()
    return Select(
        *[Option(ctx, value=ctx, selected=(ctx == current)) for ctx in contexts],
        name="context",
        hx_post="/switch-context",
        hx_on__after_request="window.location.reload()",
        id="context-dropdown",
        hx_swap_oob="true",
        style="min-width: 200px;",
    )


# -----------------------------------------------------------------------------
# Modal
# -----------------------------------------------------------------------------


def manifest_modal(content: str, title: str):
    """Render content in a modal dialog."""
    return Div(
        Div(
            Div(
                H3(f"{title}", style="margin: 0;"),
                Button(
                    "✕",
                    hx_get="/close-manifest",
                    hx_target="#modal-container",
                    hx_swap="innerHTML",
                    style="background: none; border: none; font-size: 1.5rem; cursor: pointer; padding: 0; line-height: 1;",
                ),
                style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;",
            ),
            Pre(
                Code(content),
                style="background: var(--pico-code-background-color); padding: 0.5rem; overflow: auto; max-height: 70vh; margin: 0; white-space: pre; font-size: 0.85rem;",
            ),
            style="background: var(--pico-background-color); padding: 1rem; border-radius: 8px; max-width: 800px; width: 90%; max-height: 85vh; overflow: hidden; display: flex; flex-direction: column;",
        ),
        hx_get="/close-manifest",
        hx_target="#modal-container",
        hx_swap="innerHTML",
        hx_trigger="click[target.id=='modal-overlay']",
        id="modal-overlay",
        style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); display: flex; justify-content: center; align-items: center; z-index: 1000;",
    )


# -----------------------------------------------------------------------------
# Tables
# -----------------------------------------------------------------------------


def resource_table(headers: list[str], rows: list):
    """Render a table with headers and rows."""
    return Table(
        Thead(Tr(*[Th(h) for h in headers])),
        Tbody(*rows),
    )


def link(text: str, hx_get: str, hx_target: str = "#modal-container", hx_swap: str = "innerHTML"):
    """Render a clickable link."""
    return A(
        text,
        hx_get=hx_get,
        hx_target=hx_target,
        hx_swap=hx_swap,
        style="cursor: pointer; text-decoration: underline; color: var(--pico-primary);",
    )
