"""Configuration constants."""

from pathlib import Path

KUBECONFIG_PATH = Path.home() / ".kube" / "config"
DEFAULT_NAMESPACE = "bdk"

# Map environment to kube context search patterns
ENV_CONTEXT_PATTERNS = {
    "dev": "kognitos-dev",
    "stg": "kognitos-stg",
    "prod": "kognitos-prod",
    "local": "kind-",
}
