from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Section:
    """A section within a chapter, such as a room, boss encounter, or optional quest."""

    title: str
    content: str
    order: int


@dataclass(frozen=True, slots=True)
class Chapter:
    """A chapter in a game guide."""

    order: int
    title: str
    sections: tuple[Section, ...] = ()

    @property
    def full_text(self) -> str:
        """Return the consolidated text of the chapter for indexing or display."""
        parts = [f"## {self.title}"]
        for section in self.sections:
            parts.append(f"### {section.title}\n{section.content}")
        return "\n\n".join(parts)


@dataclass(frozen=True, slots=True)
class GameGuide:
    """Complete hierarchical tree of a game guide with built-in spoiler filtering."""

    game_id: str
    title: str
    executable: str | None = None
    chapters: tuple[Chapter, ...] = ()

    def chapters_up_to(self, max_chapter_order: int) -> tuple[Chapter, ...]:
        """Return chapters up to and including ``max_chapter_order`` (spoiler shield)."""
        return tuple(ch for ch in self.chapters if ch.order <= max_chapter_order)

    def get_chapter(self, order: int) -> Chapter | None:
        """Return the chapter matching the given order number, or ``None`` if not found."""
        for chapter in self.chapters:
            if chapter.order == order:
                return chapter
        return None
