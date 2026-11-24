from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from navi_server.models import Chapter, GameGuide
from navi_server.parser import parse_walkthrough_file


class SpoilerBlockedError(Exception):
    """Raised when a user tries to read a chapter locked by the Spoiler Shield."""


@dataclass
class ManualSession:
    """Stateful reading session for a single GameGuide with Spoiler Shield enforcement."""

    guide: GameGuide
    current_chapter: int = 1
    spoiler_shield: bool = True

    def __post_init__(self) -> None:
        if self.guide.chapters:
            self.current_chapter = max(1, min(self.current_chapter, len(self.guide.chapters)))
        else:
            self.current_chapter = 0

    @property
    def total_chapters(self) -> int:
        return len(self.guide.chapters)

    def visible_chapters(self) -> tuple[Chapter, ...]:
        """Return chapters allowed under the current Spoiler Shield setting."""
        if self.spoiler_shield:
            return self.guide.chapters_up_to(self.current_chapter)
        return self.guide.chapters

    def set_progress(self, chapter_order: int) -> int:
        """Update the player's current chapter progress."""
        if self.total_chapters == 0:
            raise ValueError("This guide has no chapters.")
        if chapter_order < 1 or chapter_order > self.total_chapters:
            raise ValueError(f"Chapter must be between 1 and {self.total_chapters}.")
        self.current_chapter = chapter_order
        return self.current_chapter

    def read_chapter(self, chapter_order: int) -> Chapter:
        """Fetch a chapter by number, blocking future chapters when Spoiler Shield is on."""
        chapter = self.guide.get_chapter(chapter_order)
        if chapter is None:
            raise KeyError(f"Chapter {chapter_order} does not exist.")
        if self.spoiler_shield and chapter.order > self.current_chapter:
            raise SpoilerBlockedError(
                f"Chapter {chapter_order} is hidden by Spoiler Shield "
                f"(current progress: Chapter {self.current_chapter})."
            )
        return chapter

    def format_toc(self) -> str:
        """Render the manual Table of Contents, masking locked chapter titles."""
        shield_label = "ON" if self.spoiler_shield else "OFF"
        lines = [
            f"=== {self.guide.title} ===",
            (f"Progress: Chapter {self.current_chapter}/{self.total_chapters} "
            f"| Spoiler Shield: {shield_label}"),
            "",
        ]
        if not self.guide.chapters:
            lines.append("(No chapters found in this guide.)")
            return "\n".join(lines)

        for chapter in self.guide.chapters:
            is_locked = self.spoiler_shield and chapter.order > self.current_chapter
            marker = ">" if chapter.order == self.current_chapter else " "
            if is_locked:
                lines.append(f"{marker} [{chapter.order}] [LOCKED - Spoiler Shield]")
            else:
                section_count = len(chapter.sections)
                lines.append(
                    f"{marker} [{chapter.order}] {chapter.title} ({section_count} sections)"
                )
        return "\n".join(lines)


HELP_TEXT = """Available commands:
  toc               Show the Table of Contents
  read N            Read Chapter N (subject to Spoiler Shield)
  progress N        Set your current progress to Chapter N
  shield on|off     Enable or disable the Spoiler Shield
  help              Show this help message
  quit              Exit Navi CLI"""


def _handle_command(session: ManualSession, raw_command: str) -> tuple[str, bool]:
    """Execute one user command and return (response_text, should_continue)."""
    parts = raw_command.strip().split()
    if not parts:
        return "", True

    cmd = parts[0].lower()

    if cmd in {"quit", "exit", "q"}:
        return "Closing Navi manual. Good luck out there!", False

    if cmd == "help":
        return HELP_TEXT, True

    if cmd == "toc":
        return session.format_toc(), True

    if cmd == "read":
        if len(parts) != 2 or not parts[1].isdigit():
            return "Usage: read N (example: read 1)", True
        try:
            chapter = session.read_chapter(int(parts[1]))
            return chapter.full_text, True
        except (KeyError, SpoilerBlockedError) as exc:
            return str(exc), True

    if cmd == "progress":
        if len(parts) != 2 or not parts[1].isdigit():
            return "Usage: progress N (example: progress 2)", True
        try:
            updated = session.set_progress(int(parts[1]))
            return f"Progress updated to Chapter {updated}.", True
        except ValueError as exc:
            return str(exc), True

    if cmd == "shield":
        if len(parts) != 2 or parts[1].lower() not in {"on", "off"}:
            return "Usage: shield on|off", True
        session.spoiler_shield = parts[1].lower() == "on"
        state = "ON" if session.spoiler_shield else "OFF"
        return f"Spoiler Shield is now {state}.", True

    return f"Unknown command: '{cmd}'. Type 'help' to see available commands.", True


def run_interactive_loop(
    session: ManualSession,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> None:
    """Run the interactive terminal loop with injectable I/O for clean testing."""
    output_fn(session.format_toc())
    output_fn("\nType 'help' for commands, or 'read 1' to start reading.")

    while True:
        try:
            raw_command = input_fn("\nnavi> ")
        except (EOFError, KeyboardInterrupt):
            output_fn("\nClosing Navi manual.")
            break

        response, should_continue = _handle_command(session, raw_command)
        if response:
            output_fn(response)
        if not should_continue:
            break


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="navi-cli",
        description="Navi v0.1 - Classic offline game manual browser with Spoiler Shield.",
    )
    parser.add_argument("guide_path", type=Path, help="Path to a plain-text walkthrough file.")
    parser.add_argument("--game-id", default=None, help="Unique game identifier (defaults to stem).")
    parser.add_argument("--title", default=None, help="Display title of the game.")
    parser.add_argument(
        "--progress",
        type=int,
        default=1,
        help="Starting chapter number for the Spoiler Shield (default: 1).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    guide_path: Path = args.guide_path

    if not guide_path.is_file():
        print(f"Error: guide file not found: {guide_path}")
        return 1

    game_id = args.game_id or guide_path.stem
    title = args.title or guide_path.stem.replace("_", " ").title()
    guide = parse_walkthrough_file(path=guide_path, game_id=game_id, title=title)
    session = ManualSession(guide=guide, current_chapter=args.progress)
    run_interactive_loop(session)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())