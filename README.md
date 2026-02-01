# Mission Control

A web-based UI for browsing and managing Kognitos BDK Kubernetes resources.

## Features

- **Context Switching** - Switch between Kubernetes contexts (dev, stg, prod, local) from the UI
- **Books Browser** - View and inspect Book custom resources
- **Book Connections Browser** - View BookConnection resources with associated pod information
- **URL Parsing** - Paste a Kognitos app URL to automatically switch context and namespace
- **Pod Inspection** - View pod manifests, logs, and metrics (when available)

## Prerequisites

- Python 3.11+
- `kubectl` configured with access to your Kubernetes clusters
- [uv](https://docs.astral.sh/uv/) - Fast Python package manager

## Installation

### 1. Install uv

macOS/Linux:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Windows:
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Or via Homebrew:
```bash
brew install uv
```

### 2. Install dependencies

```bash
uv sync
```

This will create a virtual environment and install all required packages.

## Usage

### Start the server

```bash
uv run python main.py
```

The server runs at http://localhost:5001

### Navigating the UI

1. **Context Dropdown** (top-right) - Select your Kubernetes context
2. **Sidebar** - Navigate between Books and Book Connections
3. **URL Input** (Book Connections page) - Paste a Kognitos URL to auto-switch context and namespace

### URL Format

The app can parse Kognitos URLs to automatically configure context and namespace:

| Environment | URL Pattern |
|-------------|-------------|
| Dev | `app.us-1.dev.kognitos.com/organizations/<org>/workspaces/<ws>/...` |
| Staging | `app.us-1.stg.kognitos.com/organizations/<org>/workspaces/<ws>/...` |
| Production | `app.us-1.kognitos.com/organizations/<org>/workspaces/<ws>/...` |
| Local | `localhost.../organizations/<org>/workspaces/<ws>/...` |

The namespace is derived as: `org-<org-id>-ws-<ws-id>` (lowercase, sanitized)

## Development

### Project Structure

```
mission-control/
├── main.py           # Main application
├── static/           # Static assets (logo, favicon)
├── pyproject.toml    # Project dependencies
├── CLAUDE.md         # AI assistant context
└── .claude/
    └── docs/         # Reference documentation
```

### Tech Stack

- [FastHTML](https://fastht.ml/) - Python web framework with HTMX
- [Kubernetes Python Client](https://github.com/kubernetes-client/python) - K8s API interaction
- [HTMX](https://htmx.org/) - Dynamic UI without JavaScript

### Adding new resources

To add a new Kubernetes resource type:

1. Add a `get_<resource>()` function to fetch resources
2. Add a `<resource>_content()` function to render the UI
3. Add routes for listing and viewing manifests
4. Add navigation link in `sidebar()`
