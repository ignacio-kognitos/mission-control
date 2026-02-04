"""Authentication utilities for k8s contexts."""

import json
import subprocess
from pathlib import Path

from .config import ENV_CONTEXT_PATTERNS

# Shared state for tracking if we recently logged in
_login_performed = False


def reset_login_flag():
    """Reset the login performed flag."""
    global _login_performed
    _login_performed = False


def was_login_performed() -> bool:
    """Check if login was recently performed."""
    return _login_performed


def get_env_from_context(context: str) -> str | None:
    """Determine which env (dev, stg, prod) the context belongs to."""
    for env_name, pattern in ENV_CONTEXT_PATTERNS.items():
        if env_name in ("dev", "stg", "prod") and pattern in context:
            return env_name
    return None


def is_auth_error(exception: Exception) -> bool:
    """Check if the exception indicates an authentication/authorization error."""
    error_str = str(exception).lower()
    auth_indicators = [
        "unauthorized",
        "401",
        "403",
        "forbidden",
        "token has expired",
        "token is expired",
        "unable to connect to the server",
        "credentials",
        "authentication",
        "exec plugin",
        "no auth provider",
    ]
    return any(indicator in error_str for indicator in auth_indicators)


def perform_login(context: str) -> tuple[bool, str]:
    """Perform login for the given context.

    Returns:
        Tuple of (success: bool, message: str)
    """
    global _login_performed

    env = get_env_from_context(context)
    if not env:
        return False, "Login only supported for dev, stg, prod contexts"

    # Get gitops path from config
    config_path = Path(__file__).parent.parent / "config.json"
    if not config_path.exists():
        return False, "config.json not found"

    try:
        config = json.loads(config_path.read_text())
    except json.JSONDecodeError:
        return False, "Invalid config.json"

    gitops_path = config.get("gitops_path", "")
    if not gitops_path:
        return False, "gitops_path not configured in config.json"

    script_path = Path(gitops_path) / "scripts" / "setup-access.sh"
    if not script_path.exists():
        return False, f"Script not found: {script_path}"

    # Run the login script
    try:
        result = subprocess.run(
            [str(script_path), env],
            cwd=gitops_path,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            return False, f"Login failed: {result.stderr}"

        _login_performed = True
        return True, f"Successfully logged in to {env}"
    except subprocess.TimeoutExpired:
        return False, "Login timed out"
    except Exception as e:
        return False, f"Login error: {str(e)}"
