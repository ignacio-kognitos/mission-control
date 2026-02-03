"""Mission Control - Kubernetes resource browser.

This module contains only route definitions. Business logic lives in:
- mission_control/k8s.py - Kubernetes operations
- mission_control/components.py - UI components
- mission_control/views/ - View functions
"""

from pathlib import Path

from fasthtml.common import *
from starlette.requests import Request
from starlette.staticfiles import StaticFiles

from mission_control.components import context_dropdown_oob, manifest_modal, page_layout
from mission_control.config import DEFAULT_NAMESPACE, ENV_CONTEXT_PATTERNS
from mission_control.k8s import (
    get_associated_pod,
    get_book_connection_manifest,
    get_book_connections,
    get_book_manifest,
    get_kube_contexts,
    get_pod_logs,
    get_pod_manifest,
    switch_kube_context,
)
from mission_control.url_parser import parse_kognitos_url
from mission_control.views.book_connections import (
    book_connection_row,
    book_connection_row_expanded,
    book_connections_content,
)
from mission_control.views.books import books_content

# -----------------------------------------------------------------------------
# App Setup
# -----------------------------------------------------------------------------

STATIC_DIR = Path(__file__).parent / "static"

app, rt = fast_app(
    hdrs=(
        Link(rel="icon", type="image/png", href="/static/favicon.png"),
        Style("""
            .htmx-indicator { display: none; }
            .htmx-request .htmx-indicator,
            .htmx-request.htmx-indicator { display: inline-block; }
            #global-loader {
                position: fixed;
                top: 0; left: 0; right: 0;
                height: 3px;
                background: var(--pico-primary);
                z-index: 9999;
                animation: loading 1s ease-in-out infinite;
            }
            @keyframes loading {
                0% { transform: translateX(-100%); }
                50% { transform: translateX(0%); }
                100% { transform: translateX(100%); }
            }
        """),
        Script("""
            document.addEventListener('htmx:beforeRequest', () =>
                document.getElementById('global-loader').style.display = 'block');
            document.addEventListener('htmx:afterRequest', () =>
                document.getElementById('global-loader').style.display = 'none');

            // Load keyboard shortcuts
            document.addEventListener('DOMContentLoaded', async () => {
                let shortcuts = { navigation: {}, actions: {} };
                try {
                    const response = await fetch('/keyboard-shortcuts.json');
                    shortcuts = await response.json();
                } catch (e) {
                    console.warn('Could not load keyboard shortcuts:', e);
                }

                document.addEventListener('keydown', (e) => {
                    // Ignore if typing in input or textarea
                    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') {
                        return;
                    }

                    // Handle navigation shortcuts
                    const nav = shortcuts.navigation && shortcuts.navigation[e.key];
                    if (nav) {
                        htmx.ajax('GET', nav, {target: '#main-content', swap: 'innerHTML'});
                        history.pushState({}, '', nav);
                        return;
                    }

                    // Handle Escape to close modal
                    if (e.key === 'Escape') {
                        const modal = document.getElementById('modal-overlay');
                        if (modal) {
                            htmx.ajax('GET', '/close-manifest', {target: '#modal-container', swap: 'innerHTML'});
                        }
                    }
                });
            });
        """),
    ),
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# -----------------------------------------------------------------------------
# Helper
# -----------------------------------------------------------------------------


def full_page_or_fragment(request: Request, content):
    """Return full page for direct requests, fragment for HTMX."""
    if request.headers.get("HX-Request"):
        return content
    return Title("Mission Control"), page_layout(content)


# -----------------------------------------------------------------------------
# Routes: General
# -----------------------------------------------------------------------------


@rt("/")
def get():
    return Title("Mission Control"), page_layout(books_content())


@rt("/switch-context")
def post(context: str):
    switch_kube_context(context)
    return ""


@rt("/close-manifest")
def get():
    return ""


@rt("/keyboard-shortcuts.json")
def get():
    from starlette.responses import Response

    shortcuts_path = Path(__file__).parent / "keyboard-shortcuts.json"
    if shortcuts_path.exists():
        return Response(shortcuts_path.read_text(), media_type="application/json")
    return Response('{"navigation": {}, "actions": {}}', media_type="application/json")


# -----------------------------------------------------------------------------
# Routes: Books
# -----------------------------------------------------------------------------


@rt("/books")
def get(request: Request, namespace: str = DEFAULT_NAMESPACE):
    return full_page_or_fragment(request, books_content(namespace))


@rt("/book/{namespace}/{name}")
def get(namespace: str, name: str):
    return manifest_modal(get_book_manifest(name, namespace), f"Book: {name}")


# -----------------------------------------------------------------------------
# Routes: Book Connections
# -----------------------------------------------------------------------------


@rt("/book-connections")
def get(request: Request, namespace: str = DEFAULT_NAMESPACE):
    return full_page_or_fragment(request, book_connections_content(namespace))


@rt("/book-connections-from-url")
def get(request: Request, url: str = ""):
    parsed = parse_kognitos_url(url)
    namespace = DEFAULT_NAMESPACE

    if parsed:
        namespace = parsed["namespace"]
        pattern = ENV_CONTEXT_PATTERNS.get(parsed["env"])
        if pattern:
            contexts, _ = get_kube_contexts()
            matching = next((ctx for ctx in contexts if pattern in ctx), None)
            if matching:
                switch_kube_context(matching)

    content = book_connections_content(namespace, url)

    if request.headers.get("HX-Request"):
        return context_dropdown_oob(), content
    return Title("Mission Control"), page_layout(content)


@rt("/book-connection/{namespace}/{name}")
def get(namespace: str, name: str):
    return manifest_modal(get_book_connection_manifest(name, namespace), f"BookConnection: {name}")


@rt("/book-connection-pod/{namespace}/{name}")
def get(namespace: str, name: str):
    conn = {"name": name, "namespace": namespace, "label_name": "", "label_version": "", "created": ""}
    pod = get_associated_pod(name, namespace)
    return book_connection_row_expanded(conn, pod)


@rt("/book-connection-row/{namespace}/{name}")
def get(namespace: str, name: str):
    connections = get_book_connections(namespace)
    conn = next((c for c in connections if c["name"] == name), None)
    return book_connection_row(conn) if conn else ""


# -----------------------------------------------------------------------------
# Routes: Pods
# -----------------------------------------------------------------------------


@rt("/pod/{namespace}/{name}")
def get(namespace: str, name: str):
    return manifest_modal(get_pod_manifest(name, namespace), f"Pod: {name}")


@rt("/pod-logs/{namespace}/{name}")
def get(namespace: str, name: str):
    return manifest_modal(get_pod_logs(name, namespace), f"Logs: {name}")


# -----------------------------------------------------------------------------
# Run
# -----------------------------------------------------------------------------

serve()
