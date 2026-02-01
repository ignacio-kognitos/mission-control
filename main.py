from pathlib import Path
import re
from urllib.parse import urlparse

import yaml
from kubernetes import client, config as kube_config
from kubernetes.dynamic import DynamicClient
from kubernetes.client import api_client
from fasthtml.common import *
from starlette.requests import Request
from starlette.responses import FileResponse
from starlette.staticfiles import StaticFiles

STATIC_DIR = Path(__file__).parent / "static"

app, rt = fast_app(
    hdrs=(
        Link(rel="icon", type="image/png", href="/static/favicon.png"),
        Style("""
            .htmx-indicator {
                display: none;
            }
            .htmx-request .htmx-indicator,
            .htmx-request.htmx-indicator {
                display: inline-block;
            }
            #global-loader {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
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
            document.addEventListener('htmx:beforeRequest', function() {
                document.getElementById('global-loader').style.display = 'block';
            });
            document.addEventListener('htmx:afterRequest', function() {
                document.getElementById('global-loader').style.display = 'none';
            });
        """),
    ),
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

KUBECONFIG_PATH = Path.home() / ".kube" / "config"
DEFAULT_NAMESPACE = "bdk"

# Map environment to kube context search patterns
ENV_CONTEXT_PATTERNS = {
    "dev": "kognitos-dev",
    "stg": "kognitos-stg",
    "prod": "kognitos-prod",
    "local": "kind-",
}


def sanitize_k8s_name(name: str) -> str:
    """Sanitize a string to be kubernetes compliant (lowercase, alphanumeric and hyphens)."""
    name = name.lower()
    name = re.sub(r"[^a-z0-9-]", "-", name)
    name = re.sub(r"-+", "-", name)
    name = name.strip("-")
    return name


def parse_kognitos_url(url: str) -> dict | None:
    """Parse a Kognitos URL and extract environment, org-id, ws-id, and namespace."""
    if not url:
        return None

    try:
        # Add protocol if missing
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url

        parsed = urlparse(url)
        host = parsed.netloc

        # Determine environment from host
        if "localhost" in host or "127.0.0.1" in host:
            env = "local"
        elif ".dev." in host:
            env = "dev"
        elif ".stg." in host:
            env = "stg"
        elif "kognitos.com" in host:
            env = "prod"
        else:
            return None

        # Parse org-id and ws-id from path: /organizations/<org-id>/workspaces/<ws-id>...
        path_match = re.search(r"/organizations/([^/]+)/workspaces/([^/]+)", parsed.path)
        if not path_match:
            return None

        org_id = sanitize_k8s_name(path_match.group(1))
        ws_id = sanitize_k8s_name(path_match.group(2))
        namespace = f"org-{org_id}-ws-{ws_id}"

        return {
            "env": env,
            "org_id": org_id,
            "ws_id": ws_id,
            "namespace": namespace,
        }
    except Exception:
        return None


def get_kube_contexts() -> tuple[list[str], str | None]:
    """Get list of kube contexts and the current context."""
    try:
        contexts, current_context = kube_config.list_kube_config_contexts()
        context_names = [ctx["name"] for ctx in contexts]
        current_name = current_context["name"] if current_context else None
        return context_names, current_name
    except kube_config.ConfigException:
        return [], None


def switch_kube_context(context: str) -> bool:
    """Switch to the specified kube context by updating kubeconfig."""
    try:
        with open(KUBECONFIG_PATH) as f:
            config = yaml.safe_load(f)

        config["current-context"] = context

        with open(KUBECONFIG_PATH, "w") as f:
            yaml.safe_dump(config, f, default_flow_style=False)

        return True
    except Exception:
        return False


def get_k8s_client():
    """Get a configured dynamic kubernetes client."""
    kube_config.load_kube_config()
    return DynamicClient(api_client.ApiClient())


def get_books(namespace: str = DEFAULT_NAMESPACE) -> list[dict]:
    """Get list of Book resources from the specified namespace."""
    try:
        dyn_client = get_k8s_client()
        book_resource = dyn_client.resources.get(kind="Book")
        books = book_resource.get(namespace=namespace)

        return [
            {
                "name": book.metadata.name,
                "namespace": book.metadata.namespace,
                "created": book.metadata.creationTimestamp,
                "label_name": book.metadata.labels.get("name", "") if book.metadata.labels else "",
                "label_version": book.metadata.labels.get("version", "") if book.metadata.labels else "",
            }
            for book in books.items
        ]
    except Exception:
        return []


def get_book_manifest(name: str, namespace: str = DEFAULT_NAMESPACE) -> str:
    """Get the full manifest of a Book resource."""
    try:
        dyn_client = get_k8s_client()
        book_resource = dyn_client.resources.get(kind="Book")
        book = book_resource.get(name=name, namespace=namespace)
        return yaml.safe_dump(book.to_dict(), default_flow_style=False)
    except Exception as e:
        return f"Error fetching manifest: {e}"


def get_book_connections(namespace: str = DEFAULT_NAMESPACE) -> list[dict]:
    """Get list of BookConnection resources from the specified namespace."""
    try:
        dyn_client = get_k8s_client()
        bc_resource = dyn_client.resources.get(kind="BookConnection")
        connections = bc_resource.get(namespace=namespace)

        return [
            {
                "name": conn.metadata.name,
                "namespace": conn.metadata.namespace,
                "created": conn.metadata.creationTimestamp,
                "label_name": conn.metadata.labels.get("name", "") if conn.metadata.labels else "",
                "label_version": conn.metadata.labels.get("version", "") if conn.metadata.labels else "",
            }
            for conn in connections.items
        ]
    except Exception:
        return []


def get_book_connection_manifest(name: str, namespace: str = DEFAULT_NAMESPACE) -> str:
    """Get the full manifest of a BookConnection resource."""
    try:
        dyn_client = get_k8s_client()
        bc_resource = dyn_client.resources.get(kind="BookConnection")
        conn = bc_resource.get(name=name, namespace=namespace)
        return yaml.safe_dump(conn.to_dict(), default_flow_style=False)
    except Exception as e:
        return f"Error fetching manifest: {e}"


def get_associated_pod(bookconnection_name: str, namespace: str = DEFAULT_NAMESPACE) -> dict | None:
    """Get the pod associated with a BookConnection by label."""
    try:
        dyn_client = get_k8s_client()
        pod_resource = dyn_client.resources.get(api_version="v1", kind="Pod")
        pods = pod_resource.get(
            namespace=namespace, label_selector=f"bookconnection.kognitos.com/name={bookconnection_name}"
        )
        if pods.items:
            pod = pods.items[0]
            return {
                "name": pod.metadata.name,
                "namespace": pod.metadata.namespace,
                "phase": pod.status.phase if pod.status else "Unknown",
            }
        return None
    except Exception:
        return None


def get_pod_manifest(name: str, namespace: str = DEFAULT_NAMESPACE) -> str:
    """Get the full manifest of a Pod."""
    try:
        dyn_client = get_k8s_client()
        pod_resource = dyn_client.resources.get(api_version="v1", kind="Pod")
        pod = pod_resource.get(name=name, namespace=namespace)
        return yaml.safe_dump(pod.to_dict(), default_flow_style=False)
    except Exception as e:
        return f"Error fetching manifest: {e}"


def get_pod_logs(name: str, namespace: str = DEFAULT_NAMESPACE, tail_lines: int = 500) -> str:
    """Get the logs of a Pod."""
    try:
        kube_config.load_kube_config()
        v1 = client.CoreV1Api()
        logs = v1.read_namespaced_pod_log(
            name=name,
            namespace=namespace,
            tail_lines=tail_lines,
        )
        return logs if logs else "No logs available"
    except Exception as e:
        return f"Error fetching logs: {e}"


def parse_cpu(cpu_str: str) -> str:
    """Convert CPU string to millicores."""
    if cpu_str.endswith("n"):
        nanocores = int(cpu_str[:-1])
        millicores = nanocores / 1_000_000
        return f"{millicores:.1f}m"
    elif cpu_str.endswith("u"):
        microcores = int(cpu_str[:-1])
        millicores = microcores / 1_000
        return f"{millicores:.1f}m"
    elif cpu_str.endswith("m"):
        return cpu_str
    return cpu_str


def parse_memory(mem_str: str) -> str:
    """Convert memory string to MB."""
    if mem_str.endswith("Ki"):
        kibibytes = int(mem_str[:-2])
        mb = kibibytes / 1024
        return f"{mb:.1f} MB"
    elif mem_str.endswith("Mi"):
        return f"{mem_str[:-2]} MB"
    elif mem_str.endswith("Gi"):
        gb = float(mem_str[:-2])
        mb = gb * 1024
        return f"{mb:.0f} MB"
    elif mem_str.endswith("K"):
        kb = int(mem_str[:-1])
        mb = kb / 1000
        return f"{mb:.1f} MB"
    elif mem_str.endswith("M"):
        return f"{mem_str[:-1]} MB"
    return mem_str


def get_pod_metrics(name: str, namespace: str = DEFAULT_NAMESPACE) -> dict | None:
    """Get pod metrics from the metrics API if available."""
    try:
        dyn_client = get_k8s_client()
        metrics_resource = dyn_client.resources.get(api_version="metrics.k8s.io/v1beta1", kind="PodMetrics")
        metrics = metrics_resource.get(name=name, namespace=namespace)

        containers = []
        for container in metrics.containers:
            cpu_raw = container.usage.get("cpu", "N/A")
            mem_raw = container.usage.get("memory", "N/A")
            containers.append(
                {
                    "name": container.name,
                    "cpu": parse_cpu(cpu_raw) if cpu_raw != "N/A" else "N/A",
                    "memory": parse_memory(mem_raw) if mem_raw != "N/A" else "N/A",
                }
            )

        return {"containers": containers}
    except Exception:
        return None


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


def sidebar():
    """Render the left sidebar with resource navigation."""
    return Nav(
        Ul(
            Li(
                A(
                    "Books",
                    hx_get="/books",
                    hx_target="#main-content",
                    hx_swap="innerHTML",
                    hx_push_url="true",
                )
            ),
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


def books_content(namespace: str = DEFAULT_NAMESPACE):
    """Render the books content."""
    books = get_books(namespace)

    if not books:
        return Div(
            H2("Books"),
            P(f"No books found in the {namespace} namespace."),
        )

    return Div(
        H2("Books"),
        Table(
            Thead(
                Tr(
                    Th("Resource Name"),
                    Th("Name"),
                    Th("Version"),
                    Th("Namespace"),
                    Th("Created"),
                )
            ),
            Tbody(
                *[
                    Tr(
                        Td(
                            A(
                                book["name"],
                                hx_get=f"/book/{book['namespace']}/{book['name']}",
                                hx_target="#modal-container",
                                hx_swap="innerHTML",
                                style="cursor: pointer; text-decoration: underline; color: var(--pico-primary);",
                            )
                        ),
                        Td(book["label_name"]),
                        Td(book["label_version"]),
                        Td(book["namespace"]),
                        Td(book["created"]),
                    )
                    for book in books
                ]
            ),
        ),
    )


def book_connection_row(conn: dict, expanded: bool = False):
    """Render a single book connection row."""
    row_id = f"bc-row-{conn['namespace']}-{conn['name']}"

    main_row = Tr(
        Td(
            A(
                conn["name"],
                hx_get=f"/book-connection/{conn['namespace']}/{conn['name']}",
                hx_target="#modal-container",
                hx_swap="innerHTML",
                style="cursor: pointer; text-decoration: underline; color: var(--pico-primary);",
            )
        ),
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

    return main_row


def book_connection_row_expanded(conn: dict, pod: dict | None):
    """Render an expanded book connection row with pod info."""
    row_id = f"bc-row-{conn['namespace']}-{conn['name']}"

    if pod:
        metrics = get_pod_metrics(pod["name"], pod["namespace"])

        metrics_section = []
        if metrics:
            for container in metrics["containers"]:
                metrics_section.append(
                    Div(
                        Strong(f"{container['name']}: "),
                        f"CPU: {container['cpu']}, Memory: {container['memory']}",
                        style="margin-right: 1rem;",
                    )
                )
        else:
            metrics_section.append(
                Div(
                    Span("Metrics not available", style="color: var(--pico-muted-color);"),
                    style="margin-right: 1rem;",
                )
            )

        pod_info = Tr(
            Td(
                Div(
                    Div(
                        Strong("Pod: "),
                        pod["name"],
                        style="margin-right: 1rem;",
                    ),
                    Div(
                        Strong("Status: "),
                        pod["phase"],
                        style="margin-right: 1rem;",
                    ),
                    *metrics_section,
                    style="display: flex; flex-wrap: wrap; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;",
                ),
                Div(
                    A(
                        "View Manifest",
                        hx_get=f"/pod/{pod['namespace']}/{pod['name']}",
                        hx_target="#modal-container",
                        hx_swap="innerHTML",
                        style="cursor: pointer; text-decoration: underline; color: var(--pico-primary); margin-right: 1rem;",
                    ),
                    A(
                        "View Logs",
                        hx_get=f"/pod-logs/{pod['namespace']}/{pod['name']}",
                        hx_target="#modal-container",
                        hx_swap="innerHTML",
                        style="cursor: pointer; text-decoration: underline; color: var(--pico-primary); margin-right: 1rem;",
                    ),
                    A(
                        "Collapse",
                        hx_get=f"/book-connection-row/{conn['namespace']}/{conn['name']}",
                        hx_target=f"#{row_id}",
                        hx_swap="outerHTML",
                        style="cursor: pointer; text-decoration: underline; color: var(--pico-muted-color);",
                    ),
                    style="display: flex; flex-wrap: wrap; align-items: center;",
                ),
                colspan="6",
                style="padding: 0.5rem; background: var(--pico-code-background-color);",
            ),
            id=row_id,
        )
    else:
        pod_info = Tr(
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

    return pod_info


def book_connections_content(namespace: str = DEFAULT_NAMESPACE, url: str = ""):
    """Render the book connections content."""
    _, current_context = get_kube_contexts()
    connections = get_book_connections(namespace)

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

    if not connections:
        return Div(
            H2("Book Connections"),
            url_input,
            namespace_input,
            P(f"No book connections found in the {namespace} namespace."),
        )

    return Div(
        H2("Book Connections"),
        url_input,
        namespace_input,
        Table(
            Thead(
                Tr(
                    Th("Resource Name"),
                    Th("Name"),
                    Th("Version"),
                    Th("Namespace"),
                    Th("Created"),
                    Th("Actions"),
                )
            ),
            Tbody(*[book_connection_row(conn) for conn in connections]),
        ),
    )


def manifest_view(manifest: str, name: str):
    """Render the manifest view as a modal dialog."""
    return Div(
        Div(
            Div(
                H3(f"Manifest: {name}", style="margin: 0;"),
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
                Code(manifest),
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


def page_layout(*content):
    """Render the full page layout with sidebar."""
    return Div(
        Div(id="global-loader", style="display: none;"),
        Div(
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
        ),
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


@rt("/")
def get():
    return Title("Mission Control"), page_layout(books_content())


@rt("/switch-context")
def post(context: str):
    switch_kube_context(context)
    return ""


@rt("/books")
def get(request: Request, namespace: str = DEFAULT_NAMESPACE):
    content = books_content(namespace)
    if request.headers.get("HX-Request"):
        return content
    return Title("Mission Control"), page_layout(content)


@rt("/book/{namespace}/{name}")
def get(namespace: str, name: str):
    manifest = get_book_manifest(name, namespace)
    return manifest_view(manifest, name)


@rt("/book-connections")
def get(request: Request, namespace: str = DEFAULT_NAMESPACE):
    content = book_connections_content(namespace)
    if request.headers.get("HX-Request"):
        return content
    return Title("Mission Control"), page_layout(content)


@rt("/book-connections-from-url")
def get(request: Request, url: str = ""):
    parsed = parse_kognitos_url(url)
    namespace = DEFAULT_NAMESPACE

    if parsed:
        namespace = parsed["namespace"]
        # Switch to the appropriate context
        pattern = ENV_CONTEXT_PATTERNS.get(parsed["env"])
        if pattern:
            contexts, _ = get_kube_contexts()
            matching_context = next((ctx for ctx in contexts if pattern in ctx), None)
            if matching_context:
                switch_kube_context(matching_context)

    content = book_connections_content(namespace, url)

    if request.headers.get("HX-Request"):
        return (
            context_dropdown_oob(),
            content,
        )
    return Title("Mission Control"), page_layout(content)


@rt("/book-connection/{namespace}/{name}")
def get(namespace: str, name: str):
    manifest = get_book_connection_manifest(name, namespace)
    return manifest_view(manifest, name)


@rt("/pod/{namespace}/{name}")
def get(namespace: str, name: str):
    manifest = get_pod_manifest(name, namespace)
    return manifest_view(manifest, name)


@rt("/pod-logs/{namespace}/{name}")
def get(namespace: str, name: str):
    logs = get_pod_logs(name, namespace)
    return manifest_view(logs, f"{name} logs")


@rt("/book-connection-pod/{namespace}/{name}")
def get(namespace: str, name: str):
    conn = {
        "name": name,
        "namespace": namespace,
        "label_name": "",
        "label_version": "",
        "created": "",
    }
    pod = get_associated_pod(name, namespace)
    return book_connection_row_expanded(conn, pod)


@rt("/book-connection-row/{namespace}/{name}")
def get(namespace: str, name: str):
    connections = get_book_connections(namespace)
    conn = next((c for c in connections if c["name"] == name), None)
    if conn:
        return book_connection_row(conn)
    return ""


@rt("/close-manifest")
def get():
    return ""


serve()
