"""Books views."""

from fasthtml.common import *

from ..components import filterable_table, link
from ..config import DEFAULT_NAMESPACE
from ..k8s import get_books


def books_content(namespace: str = DEFAULT_NAMESPACE):
    """Render the books list."""
    books = get_books(namespace)

    if not books:
        return Div(
            H2("Books"),
            P(f"No books found in the {namespace} namespace."),
        )

    headers = ["Resource Name", "Name", "Version", "Namespace", "Created"]
    rows = [_book_row(book) for book in books]

    return Div(
        H2("Books"),
        filterable_table(headers, rows, "books-table"),
    )


def _book_row(book: dict):
    """Render a single book row."""
    return Tr(
        Td(link(book["name"], f"/book/{book['namespace']}/{book['name']}")),
        Td(book["label_name"]),
        Td(book["label_version"]),
        Td(book["namespace"]),
        Td(book["created"]),
    )
