"""Kubernetes client and resource operations."""

import yaml
from kubernetes import client
from kubernetes import config as kube_config
from kubernetes.client import api_client
from kubernetes.dynamic import DynamicClient

from .config import DEFAULT_NAMESPACE, KUBECONFIG_PATH

# -----------------------------------------------------------------------------
# Client & Context
# -----------------------------------------------------------------------------


def get_k8s_client() -> DynamicClient:
    """Get a configured dynamic kubernetes client."""
    kube_config.load_kube_config()
    return DynamicClient(api_client.ApiClient())


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


# -----------------------------------------------------------------------------
# Books
# -----------------------------------------------------------------------------


def get_books(namespace: str = DEFAULT_NAMESPACE) -> list[dict]:
    """Get list of Book resources from the specified namespace."""
    try:
        dyn_client = get_k8s_client()
        book_resource = dyn_client.resources.get(kind="Book")
        books = book_resource.get(namespace=namespace)

        return [_extract_book_info(book) for book in books.items]
    except Exception:
        return []


def _extract_book_info(book) -> dict:
    """Extract book info from a Book resource, including spec fields."""
    spec = book.spec or {}
    return {
        "name": book.metadata.name,
        "namespace": book.metadata.namespace,
        "created": book.metadata.creationTimestamp,
        "spec_name": spec.get("name", ""),
        "spec_version": spec.get("version", ""),
        "bdk_version": spec.get("bdkVersion", ""),
    }


def get_book_manifest(name: str, namespace: str = DEFAULT_NAMESPACE) -> str:
    """Get the full manifest of a Book resource."""
    try:
        dyn_client = get_k8s_client()
        book_resource = dyn_client.resources.get(kind="Book")
        book = book_resource.get(name=name, namespace=namespace)
        return yaml.safe_dump(book.to_dict(), default_flow_style=False)
    except Exception as e:
        return f"Error fetching manifest: {e}"


# -----------------------------------------------------------------------------
# Book Connections
# -----------------------------------------------------------------------------


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
                "label_name": (conn.metadata.labels or {}).get("book_name", ""),
                "label_version": (conn.metadata.labels or {}).get("book_version", ""),
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


# -----------------------------------------------------------------------------
# Pods
# -----------------------------------------------------------------------------


def get_associated_pod(bookconnection_name: str, namespace: str = DEFAULT_NAMESPACE) -> dict | None:
    """Get the pod associated with a BookConnection by label."""
    try:
        dyn_client = get_k8s_client()
        pod_resource = dyn_client.resources.get(api_version="v1", kind="Pod")
        pods = pod_resource.get(
            namespace=namespace,
            label_selector=f"bookconnection.kognitos.com/name={bookconnection_name}",
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
        logs = v1.read_namespaced_pod_log(name=name, namespace=namespace, tail_lines=tail_lines)
        return logs if logs else "No logs available"
    except Exception as e:
        return f"Error fetching logs: {e}"


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
                    "cpu": _parse_cpu(cpu_raw) if cpu_raw != "N/A" else "N/A",
                    "memory": _parse_memory(mem_raw) if mem_raw != "N/A" else "N/A",
                }
            )

        return {"containers": containers}
    except Exception:
        return None


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _extract_resource_info(resource) -> dict:
    """Extract common resource info from a k8s resource."""
    labels = resource.metadata.labels or {}
    return {
        "name": resource.metadata.name,
        "namespace": resource.metadata.namespace,
        "created": resource.metadata.creationTimestamp,
        "label_name": labels.get("name", ""),
        "label_version": labels.get("version", ""),
    }


def _parse_cpu(cpu_str: str) -> str:
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


def _parse_memory(mem_str: str) -> str:
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


# -----------------------------------------------------------------------------
# Trigger Instances
# -----------------------------------------------------------------------------


def get_trigger_instances(namespace: str = DEFAULT_NAMESPACE) -> list[dict]:
    """Get list of TriggerInstance resources from the specified namespace."""
    try:
        dyn_client = get_k8s_client()
        resource = dyn_client.resources.get(kind="TriggerInstance")
        instances = resource.get(namespace=namespace)

        return [_extract_resource_info(instance) for instance in instances.items]
    except Exception:
        return []


def get_trigger_instance_manifest(name: str, namespace: str = DEFAULT_NAMESPACE) -> str:
    """Get the full manifest of a TriggerInstance resource."""
    try:
        dyn_client = get_k8s_client()
        resource = dyn_client.resources.get(kind="TriggerInstance")
        instance = resource.get(name=name, namespace=namespace)
        return yaml.safe_dump(instance.to_dict(), default_flow_style=False)
    except Exception as e:
        return f"Error fetching manifest: {e}"


# -----------------------------------------------------------------------------
# Deployments
# -----------------------------------------------------------------------------


def get_deployments(namespace: str = DEFAULT_NAMESPACE) -> list[dict]:
    """Get list of Deployment resources from the specified namespace."""
    try:
        dyn_client = get_k8s_client()
        resource = dyn_client.resources.get(api_version="apps/v1", kind="Deployment")
        deployments = resource.get(namespace=namespace)

        return [
            {
                "name": d.metadata.name,
                "namespace": d.metadata.namespace,
                "created": d.metadata.creationTimestamp,
                "replicas": f"{d.status.readyReplicas or 0}/{d.spec.replicas or 0}",
                "image": (
                    d.spec.template.spec.containers[0].image
                    if d.spec.template.spec.containers
                    else ""
                ),
            }
            for d in deployments.items
        ]
    except Exception:
        return []


def get_deployment_manifest(name: str, namespace: str = DEFAULT_NAMESPACE) -> str:
    """Get the full manifest of a Deployment resource."""
    try:
        dyn_client = get_k8s_client()
        resource = dyn_client.resources.get(api_version="apps/v1", kind="Deployment")
        deployment = resource.get(name=name, namespace=namespace)
        return yaml.safe_dump(deployment.to_dict(), default_flow_style=False)
    except Exception as e:
        return f"Error fetching manifest: {e}"


# -----------------------------------------------------------------------------
# Secrets
# -----------------------------------------------------------------------------


def get_secrets(namespace: str = DEFAULT_NAMESPACE) -> list[dict]:
    """Get list of Secret resources from the specified namespace."""
    try:
        dyn_client = get_k8s_client()
        resource = dyn_client.resources.get(api_version="v1", kind="Secret")
        secrets = resource.get(namespace=namespace)

        return [
            {
                "name": s.metadata.name,
                "namespace": s.metadata.namespace,
                "created": s.metadata.creationTimestamp,
                "type": s.type,
                "keys": ", ".join(sorted((s.data or {}).keys())),
            }
            for s in secrets.items
        ]
    except Exception:
        return []


def get_secret_manifest(name: str, namespace: str = DEFAULT_NAMESPACE) -> str:
    """Get the full manifest of a Secret resource (keys only, no values)."""
    try:
        dyn_client = get_k8s_client()
        resource = dyn_client.resources.get(api_version="v1", kind="Secret")
        secret = resource.get(name=name, namespace=namespace)
        secret_dict = secret.to_dict()
        # Replace secret values with placeholder for security
        if "data" in secret_dict and secret_dict["data"]:
            secret_dict["data"] = {k: "<REDACTED>" for k in secret_dict["data"].keys()}
        return yaml.safe_dump(secret_dict, default_flow_style=False)
    except Exception as e:
        return f"Error fetching manifest: {e}"
