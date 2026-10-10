from html.parser import HTMLParser
from typing import Any


class _DirectoryParser(HTMLParser):
    """Parse SEBI directory HTML while preserving record boundaries."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)

        self.depth = 0
        self.has_table_wrapper = False
        self.has_record_containers = False

        self.cards: list[dict[str, str]] = []
        self.records: list[dict[str, str]] = []

        self.card_depth: int | None = None
        self.card_fields: dict[str, str] = {}

        self.field_depth: int | None = None
        self.field_name: str | None = None
        self.field_parts: list[str] = []

        self.record_depth: int | None = None
        self.record_fields: dict[str, str] = {}

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        if tag.lower() != "div":
            return

        self.depth += 1

        attributes = dict(attrs)
        classes = set((attributes.get("class") or "").split())

        if {"fixed-table-body", "card-table"} & classes:
            self.has_table_wrapper = True

        if "card-table-left" in classes:
            self.has_record_containers = True
            self.record_depth = self.depth
            self.record_fields = {}

        if "card-view" in classes:
            self.card_depth = self.depth
            self.card_fields = {}

        if self.card_depth is not None and self.field_depth is None:
            if "title" in classes:
                self.field_name = "title"
                self.field_depth = self.depth
                self.field_parts = []
            elif "value" in classes:
                self.field_name = "value"
                self.field_depth = self.depth
                self.field_parts = []

    def handle_data(self, data: str) -> None:
        if self.field_depth is not None:
            self.field_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "div":
            return

        # Finish a title/value field only when its own div closes.
        if self.field_depth == self.depth:
            value = " ".join("".join(self.field_parts).split())

            if self.field_name is not None:
                self.card_fields[self.field_name] = value

            self.field_depth = None
            self.field_name = None
            self.field_parts = []

        # Finish a card and associate it with the appropriate record.
        if self.card_depth == self.depth:
            title = self.card_fields.get("title", "")
            value = self.card_fields.get("value", "")

            if title and value:
                if self.record_depth is not None:
                    self.record_fields[title] = value
                else:
                    self.cards.append({"title": title, "value": value})

            self.card_depth = None
            self.card_fields = {}

        # Finish a record container.
        if self.record_depth == self.depth:
            if self.record_fields.get("Registration No.", "").strip():
                self.records.append(self.record_fields.copy())

            self.record_depth = None
            self.record_fields = {}

        self.depth = max(0, self.depth - 1)


def parse_sebi_directory_html(html: str) -> list[dict[str, Any]]:
    """Parse SEBI directory HTML into records with registration numbers."""
    if not html or not html.strip():
        return []

    parser = _DirectoryParser()
    parser.feed(html)
    parser.close()

    # Layout 1: Each card-table-left container represents one record.
    if parser.has_record_containers:
        return parser.records

    # Layout 2: Multiple card-view elements describe one table record.
    if parser.has_table_wrapper:
        fields = {
            card["title"]: card["value"]
            for card in parser.cards
        }

        if fields.get("Registration No.", "").strip():
            return [fields]

        return []

    # Layout 3: Wrapperless fragments; retain the existing fallback.
    return [
        {card["title"]: card["value"]}
        for card in parser.cards
        if card["title"] == "Registration No."
        and card["value"].strip()
    ]