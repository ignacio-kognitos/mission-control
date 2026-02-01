# Mission Control

A Kubernetes resource browser UI for Kognitos BDK resources.

## Tech Stack

- **FastHTML** - Python web framework with HTMX integration (docs: `.claude/docs/fasthtml.txt`)
- **Kubernetes Python client** - For interacting with k8s clusters
- **HTMX** - For dynamic UI updates without full page reloads
- **Pico CSS** - Default styling from FastHTML

## Project Structure

```
main.py          - Main application (FastHTML app, routes, UI components)
static/          - Static assets (logo, favicon)
.claude/docs/    - Reference documentation
```

## Key Concepts

### FastHTML Patterns
- Use `fast_app()` to create the app
- Routes use `@rt("/path")` decorator
- HTML elements are Python functions: `Div()`, `Table()`, `A()`, etc.
- HTMX attributes use underscores: `hx_get`, `hx_target`, `hx_swap`
- Return tuples for multiple elements: `return Title("..."), Div(...)`

### Kubernetes Resources
- **Books** - Custom resource in `bdk` namespace
- **BookConnections** - Custom resource with associated pods
- Pods are found via label: `bookconnection.kognitos.com/name=<name>`

### URL Parsing
The app can parse Kognitos URLs to auto-switch context and namespace:
- Dev: `app.us-1.dev.kognitos.com/organizations/<org>/workspaces/<ws>/...`
- Stg: `app.us-1.stg.kognitos.com/...`
- Prod: `app.us-1.kognitos.com/...`

Namespace format: `org-<org-id>-ws-<ws-id>` (lowercase, sanitized)

## Running

```bash
uv run python main.py
```

Server runs on http://localhost:5001

## References

When working with FastHTML, read `.claude/docs/fasthtml.txt` for API reference.
