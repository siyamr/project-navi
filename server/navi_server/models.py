from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Section:
    """
    Section of a chapter. May represent a room, a boss, an optional quest.
    """
    title: str
    content: str
    order: int

@dataclass(frozen=True, slots=True)
class Chapter:
    """
    Chapter from the game guide.
    """
    order: int
    title: str
    sections: tuple[Section, ...] = ()

    @property
    def full_text(self) -> str:
        """
        Returns the consolidated text of the chapter for indexation or display.
        """
        parts = [f"## {self.title}"]
        for section in self.sections:
            parts.append(f"### {section.title}\n{section.content}")
        return "\n\n".join(parts)

@dataclass(frozen=True, slots=True)
class GameGuide:
    """
    Complete tree of the game guide. May integrate an antispoiler filter.
    """
    game_id: str
    title: str
    executable: str | None = None
    chapters: tuple[Chapter, ...] = ()

    def chapters_up_to(self, max_chapter_order: int) -> tuple[Chapter, ...]:
        """
        Spoiler shield. Must show the current progress from the current chapter.
        """
        return tuple(ch for ch in self.chapters if ch.order <= max_chapter_order)

    def get_chapter(self, order: int) -> Chapter | None:
        """
        Get chapter using its order id.
        """
        for chapter in self.chapters:
            if chapter.order == order:
                return chapter
        return None