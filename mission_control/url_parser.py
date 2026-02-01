"""URL parsing utilities for Kognitos URLs."""

import re
from urllib.parse import urlparse


def sanitize_k8s_name(name: str) -> str:
    """Sanitize a string to be kubernetes compliant (lowercase, alphanumeric and hyphens)."""
    name = name.lower()
    name = re.sub(r"[^a-z0-9-]", "-", name)
    name = re.sub(r"-+", "-", name)
    name = name.strip("-")
    return name


def parse_kognitos_url(url: str) -> dict | None:
    """
    Parse a Kognitos URL and extract environment, org-id, ws-id, and namespace.

    Supported URL formats:
    - Dev: app.us-1.dev.kognitos.com/organizations/<org>/workspaces/<ws>/...
    - Stg: app.us-1.stg.kognitos.com/organizations/<org>/workspaces/<ws>/...
    - Prod: app.us-1.kognitos.com/organizations/<org>/workspaces/<ws>/...
    - Local: localhost.../organizations/<org>/workspaces/<ws>/...

    Returns dict with: env, org_id, ws_id, namespace
    """
    if not url:
        return None

    try:
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url

        parsed = urlparse(url)
        host = parsed.netloc

        env = _detect_environment(host)
        if not env:
            return None

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


def _detect_environment(host: str) -> str | None:
    """Detect environment from hostname."""
    if "localhost" in host or "127.0.0.1" in host:
        return "local"
    elif ".dev." in host:
        return "dev"
    elif ".stg." in host:
        return "stg"
    elif "kognitos.com" in host:
        return "prod"
    return None
