from .schemas import NoteItem, NoteList

INDENT = "    "


def _clean(text: str) -> str:
    text = " ".join(text.split())
    return text.removeprefix("- ").strip()


def _render_items(items: list[NoteItem], depth: int) -> list[str]:
    lines: list[str] = []
    for item in items:
        lines.append(f"{INDENT * depth}- {_clean(item.text)}")
        lines.extend(_render_items(item.children, depth + 1))
    return lines


def render_markdown_list(note: NoteList) -> str:
    return "\n".join(_render_items(note.items, 0))
