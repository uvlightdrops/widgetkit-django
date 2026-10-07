from __future__ import annotations

from dataclasses import asdict, dataclass
from html import escape
from html.parser import HTMLParser
from typing import Any


@dataclass(frozen=True)
class PreviewResult:
    """Serializable, host-neutral data for one read-only widget preview."""

    widget_id: str
    label: str
    description: str
    area: str
    category: str
    width: int
    height: int
    active_domain: str
    preview_mode: str
    readonly: bool
    status: str
    note: str
    body_html: str
    scope_label: str = "Scope"

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


class _ReadOnlyFragment(HTMLParser):
    """Retain basic visual markup while removing executable behavior/resources."""

    allowed_tags = frozenset({
        "div", "span", "p", "strong", "em", "small", "code", "pre",
        "table", "thead", "tbody", "tr", "th", "td", "ul", "ol", "li",
        "h3", "h4", "article", "section", "a", "form", "label", "input",
        "select", "option", "textarea", "button", "details", "summary", "br",
    })
    allowed_attrs = frozenset({
        "class", "title", "colspan", "rowspan", "type", "value",
        "placeholder", "selected", "multiple", "accept", "open",
    })
    blocked_content = frozenset({"script", "style", "iframe", "object", "svg", "math", "template"})
    void_tags = frozenset({"input", "br"})

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.blocked: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self.blocked or tag in self.blocked_content:
            self.blocked.append(tag)
            return
        if tag not in self.allowed_tags:
            return
        if tag == "input" and dict(attrs).get("type") == "hidden":
            return
        output_tag = "div" if tag == "form" else tag
        safe_attrs = [(key, value) for key, value in attrs if key in self.allowed_attrs]
        if tag == "form":
            safe_attrs.append(("role", "group"))
        if tag in {"a", "button", "input", "select", "textarea"}:
            safe_attrs.extend([("aria-disabled", "true"), ("tabindex", "-1")])
        if tag in {"button", "input", "select", "textarea"}:
            safe_attrs.append(("disabled", None))
        for key, value in attrs:
            if key != "style" or not value:
                continue
            declarations = []
            for declaration in value.split(";"):
                prop, separator, setting = declaration.partition(":")
                if separator and prop.strip() in {
                    "display", "gap", "flex-wrap", "margin", "margin-top",
                    "text-align", "border-color", "color",
                } and all(token not in setting.lower() for token in ("url", "expression", "@", "\\", "<")):
                    declarations.append(declaration)
            if declarations:
                safe_attrs.append(("style", ";".join(declarations)))
        markup = "".join(
            f' {key}="{escape(value, quote=True)}"' if value is not None else f" {key}"
            for key, value in safe_attrs
        )
        self.parts.append(f"<{output_tag}{markup}>")

    def handle_endtag(self, tag: str) -> None:
        if self.blocked:
            if tag == self.blocked[-1]:
                self.blocked.pop()
            return
        if tag in self.allowed_tags and tag not in self.void_tags:
            self.parts.append(f"</{'div' if tag == 'form' else tag}>")

    def handle_data(self, data: str) -> None:
        if not self.blocked:
            self.parts.append(escape(data))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in self.void_tags:
            self.handle_endtag(tag)


def readonly_preview_html(body: str) -> str:
    parser = _ReadOnlyFragment()
    parser.feed(body)
    parser.close()
    return "".join(parser.parts)
