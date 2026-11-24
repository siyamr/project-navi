from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from navi_server.models import Chapter, GameGuide, Section

CHAPTER_PREFIX_RE = re.compile(
    r"^(?:chapter|chapitre|act|acte|part|partie|stage|episode|épisode)"
    r"\s+(?:\d+|[IVXLCDM]+)(?:\s*[:.\-–—]\s*(.+))?$",
    re.IGNORECASE,
)
MARKDOWN_H2_RE = re.compile(r"^##\s+(.+)$")
MARKDOWN_H3_RE = re.compile(r"^###\s+(.+)$")
DASH_SECTION_RE = re.compile(r"^-{2,}\s+(.+?)\s+-{2,}$")
NUMBERED_SECTION_RE = re.compile(r"^(?:\[\d+\.\d+\]|\d+\.\d+)\s*(?:[:.\-–—]\s*)?(.+)$")

IGNORED_BANNERS = frozenset(
    {
        "table of contents",
        "sommaire",
        "contents",
        "credits",
        "crédits",
        "disclaimer",
        "legal",
    }
)
MAX_HEADING_LENGTH = 100


@dataclass
class _DraftSection:
    title: str
    lines: list[str] = field(default_factory=list)


@dataclass
class _DraftChapter:
    title: str
    sections: list[_DraftSection] = field(default_factory=list)


def _is_rule(line: str, char: str) -> bool:
    """
    Checks if line is separation
    """
    stripped = line.strip()
    return len(stripped) >= 4 and set(stripped) == {char}


def _clean_chapter_title(raw: str) -> str:
    """
    Clean the chapter title prefix
    """
    cleaned = raw.strip()
    match = CHAPTER_PREFIX_RE.match(cleaned)
    if match and match.group(1):
        return match.group(1).strip()
    return cleaned


def _is_ignored_banner(text: str, game_title: str) -> bool:
    normalized = text.strip().lower()
    return normalized in IGNORED_BANNERS or normalized == game_title.strip().lower()


def _normalize_body(lines: list[str]) -> str:
    """
    Clean up the text from excessive lines and spaces.
    """
    cleaned: list[str] = []
    blank_streak = 0

    for line in lines:
        trimmed = line.rstrip()
        if not trimmed:
            if cleaned and blank_streak == 0:
                cleaned.append("")
            blank_streak += 1
        else:
            cleaned.append(trimmed)
            blank_streak = 0

    while cleaned and cleaned[-1] == "":
        cleaned.pop()

    return "\n".join(cleaned)


def _match_decorated_heading(
    lines: list[str], index: int, rule_char: str
) -> tuple[str, int] | None:
    """
    Decorated headline detections
    """
    total = len(lines)

    # Case 1
    if _is_rule(lines[index], rule_char) and index + 2 < total:
        candidate = lines[index + 1].strip()
        if (
            candidate
            and len(candidate) <= MAX_HEADING_LENGTH
            and not _is_rule(candidate, rule_char)
            and _is_rule(lines[index + 2], rule_char)
        ):
            return candidate, 3

    # Case 2
    if index + 1 < total:
        candidate = lines[index].strip()
        if (
            candidate
            and len(candidate) <= MAX_HEADING_LENGTH
            and not _is_rule(candidate, "=")
            and not _is_rule(candidate, "-")
            and _is_rule(lines[index + 1], rule_char)
        ):
            return candidate, 2

    return None


def _match_inline_chapter(stripped: str) -> str | None:
    md_match = MARKDOWN_H2_RE.match(stripped)
    if md_match:
        return _clean_chapter_title(md_match.group(1))
    if CHAPTER_PREFIX_RE.match(stripped):
        return _clean_chapter_title(stripped)
    return None


def _match_inline_section(stripped: str) -> str | None:
    for pattern in (MARKDOWN_H3_RE, DASH_SECTION_RE, NUMBERED_SECTION_RE):
        match = pattern.match(stripped)
        if match:
            return match.group(1).strip()
    return None


def _freeze_chapters(drafts: list[_DraftChapter]) -> tuple[Chapter, ...]:
    """
    Filter empty chapters and fix tree for dataclasses
    """
    frozen_chapters: list[Chapter] = []

    for draft in drafts:
        frozen_sections: list[Section] = []
        for sec in draft.sections:
            body = _normalize_body(sec.lines)
            if body:
                frozen_sections.append(
                    Section(
                        title=sec.title,
                        content=body,
                        order=len(frozen_sections) + 1,
                    )
                )

        if frozen_sections:
            frozen_chapters.append(
                Chapter(
                    order=len(frozen_chapters) + 1,
                    title=draft.title,
                    sections=tuple(frozen_sections),
                )
            )

    return tuple(frozen_chapters)


def parse_walkthrough(
    text: str,
    game_id: str,
    title: str,
    executable: str | None = None,
) -> GameGuide:
    """
    Parse the walkthrough from text to Game Guide hierarchized tree
    """
    lines = text.splitlines()
    drafts: list[_DraftChapter] = []
    current_chapter: _DraftChapter | None = None
    current_section: _DraftSection | None = None

    index = 0
    total = len(lines)

    while index < total:
        # Chapter banner
        chapter_banner = _match_decorated_heading(lines, index, "=")
        if chapter_banner is not None:
            raw_title, consumed = chapter_banner
            index += consumed
            if _is_ignored_banner(raw_title, title):
                continue
            current_chapter = _DraftChapter(title=_clean_chapter_title(raw_title))
            drafts.append(current_chapter)
            current_section = None
            continue

        # Section banner
        section_banner = _match_decorated_heading(lines, index, "-")
        if section_banner is not None:
            raw_title, consumed = section_banner
            index += consumed
            if current_chapter is None or _is_ignored_banner(raw_title, title):
                continue
            current_section = _DraftSection(title=raw_title)
            current_chapter.sections.append(current_section)
            continue

        line = lines[index]
        stripped = line.strip()
        index += 1

        # Inline chapter
        inline_chapter = _match_inline_chapter(stripped)
        if inline_chapter is not None:
            current_chapter = _DraftChapter(title=inline_chapter)
            drafts.append(current_chapter)
            current_section = None
            continue

        # Ignore inline text before chapter
        if current_chapter is None:
            continue

        # Inline section
        inline_section = _match_inline_section(stripped)
        if inline_section is not None:
            current_section = _DraftSection(title=inline_section)
            current_chapter.sections.append(current_section)
            continue

        # Create Overwiew section if no inline section text
        if current_section is None:
            if not stripped:
                continue
            current_section = _DraftSection(title="Overview")
            current_chapter.sections.append(current_section)

        current_section.lines.append(line)

    return GameGuide(
        game_id=game_id,
        title=title,
        executable=executable,
        chapters=_freeze_chapters(drafts),
    )


def parse_walkthrough_file(
    path: Path | str,
    game_id: str,
    title: str,
    executable: str | None = None,
) -> GameGuide:
    """
    Read .txt file, returns the game Guide.
    """
    raw_bytes = Path(path).read_bytes()
    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        text = raw_bytes.decode("cp1252")

    return parse_walkthrough(text=text, game_id=game_id, title=title, executable=executable)