from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest
from navi_server.models import Chapter, GameGuide, Section


def _build_sample_guide() -> GameGuide:
    ch1 = Chapter(
        order=1,
        title="Kokiri Forest",
        sections=(
            Section(
                title="Finding the Kokiri Sword",
                content="Crawl through the tunnel to the southwest.",
                order=1,
            ),
            Section(
                title="Buying the Deku Shield",
                content="Collect 40 rupees around the village.",
                order=2,
            ),
        ),
    )
    ch2 = Chapter(
        order=2,
        title="Deku Tree",
        sections=(
            Section(title="Boss: Gohma", content="Aim at her eye with the slingshot.", order=1),
        ),
    )
    ch3 = Chapter(
        order=3,
        title="Hyrule Castle",
        sections=(
            Section(title="Infiltration", content="Avoid the guards in the courtyard.", order=1),
        ),
    )
    return GameGuide(
        game_id="zelda_oot",
        title="The Legend of Zelda: Ocarina of Time",
        executable="soh.exe",
        chapters=(ch1, ch2, ch3),
    )


def test_spoiler_shield_filters_future_chapters() -> None:
    guide = _build_sample_guide()
    visible = guide.chapters_up_to(2)

    assert [ch.order for ch in visible] == [1, 2]
    assert all(ch.title != "Hyrule Castle" for ch in visible)


def test_get_chapter_returns_match_or_none() -> None:
    guide = _build_sample_guide()
    ch2 = guide.get_chapter(2)

    assert ch2 is not None
    assert ch2.title == "Deku Tree"
    assert "Gohma" in ch2.full_text
    assert guide.get_chapter(99) is None


def test_models_are_immutable() -> None:
    section = Section(title="Test", content="Content", order=1)
    with pytest.raises(FrozenInstanceError):
        section.title = "Modified"  # type: ignore[misc]
