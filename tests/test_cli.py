from __future__ import annotations

from pathlib import Path

import pytest
from navi_server.cli import ManualSession, SpoilerBlockedError, run_interactive_loop
from navi_server.parser import parse_walkthrough_file

SAMPLE_GUIDE = (
    Path(__file__).resolve().parent.parent / "data" / "sample_guides" / "zelda_oot_sample.txt"
)


def _create_session(progress: int = 1) -> ManualSession:
    guide = parse_walkthrough_file(
        path=SAMPLE_GUIDE,
        game_id="zelda_oot",
        title="The Legend of Zelda: Ocarina of Time",
    )
    return ManualSession(guide=guide, current_chapter=progress)


def test_toc_masks_future_chapter_titles_when_shield_is_on() -> None:
    session = _create_session(progress=1)

    toc = session.format_toc()

    assert "[1] Kokiri Forest" in toc
    assert "[2] [LOCKED - Spoiler Shield]" in toc
    assert "Deku Tree" not in toc
    assert "Hyrule Castle" not in toc


def test_read_chapter_enforces_spoiler_shield_and_unlocks_on_progress() -> None:
    session = _create_session(progress=1)

    ch1 = session.read_chapter(1)
    assert "Kokiri Sword" in ch1.full_text

    with pytest.raises(SpoilerBlockedError):
        session.read_chapter(2)

    session.set_progress(2)
    ch2 = session.read_chapter(2)
    assert "Queen Gohma" in ch2.full_text


def test_interactive_loop_handles_commands_end_to_end() -> None:
    session = _create_session(progress=1)
    commands = iter(["read 2", "shield off", "read 2", "progress 3", "toc", "quit"])
    outputs: list[str] = []

    run_interactive_loop(
        session=session,
        input_fn=lambda _prompt: next(commands),
        output_fn=outputs.append,
    )

    transcript = "\n".join(outputs)
    assert "hidden by Spoiler Shield" in transcript
    assert "Spoiler Shield is now OFF." in transcript
    assert "Queen Gohma" in transcript
    assert "Progress updated to Chapter 3." in transcript
    assert "[3] Hyrule Castle" in transcript
    assert "Closing Navi manual." in transcript