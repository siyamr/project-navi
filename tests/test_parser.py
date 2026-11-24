from __future__ import annotations

from pathlib import Path

from navi_server.parser import parse_walkthrough, parse_walkthrough_file

SAMPLE_GUIDE = (
    Path(__file__).resolve().parent.parent / "data" / "sample_guides" / "zelda_oot_sample.txt"
)


def test_parse_sample_file_ignores_toc_and_builds_tree() -> None:
    guide = parse_walkthrough_file(
        path=SAMPLE_GUIDE,
        game_id="zelda_oot",
        title="The Legend of Zelda: Ocarina of Time",
        executable="soh.exe",
    )

    assert guide.game_id == "zelda_oot"
    assert [ch.order for ch in guide.chapters] == [1, 2, 3]
    assert [ch.title for ch in guide.chapters] == [
        "Kokiri Forest",
        "Inside the Deku Tree",
        "Hyrule Castle",
    ]

    ch1 = guide.get_chapter(1)
    assert ch1 is not None
    assert [sec.title for sec in ch1.sections] == [
        "Overview",
        "Finding the Kokiri Sword",
        "Buying the Deku Shield",
    ]

    # Verify that the Spoiler Shield blocks future chapters after parsing
    visible = guide.chapters_up_to(1)
    assert len(visible) == 1
    assert "Gohma" not in visible[0].full_text


def test_parse_markdown_and_numbered_sections() -> None:
    raw = """
## Chapter 1: Limgrave
Explore the starting area before rushing toward the castle.

### Site of Grace: Church of Elleh
Talk to Merchant Kalé to buy the Crafting Kit.

[1.2] Boss: Tree Sentinel
You can bypass this boss and come back later.

## Chapter 2: Stormveil Castle
1.1 - Main Gate
Take the side path recommended by Gostoc.
"""
    guide = parse_walkthrough(raw, game_id="elden_ring", title="Elden Ring")

    assert len(guide.chapters) == 2
    assert guide.chapters[0].title == "Limgrave"
    assert [s.title for s in guide.chapters[0].sections] == [
        "Overview",
        "Site of Grace: Church of Elleh",
        "Boss: Tree Sentinel",
    ]
    assert guide.chapters[1].sections[0].title == "Main Gate"


def test_parse_crlf_and_cp1252_legacy_encoding(tmp_path: Path) -> None:
    legacy_text = (
        "Chapter 1: Kokiri Forest\r\n"
        "--- Link’s Hidden Sword ---\r\n"
        "Open the chest near the boulder — watch out!\r\n"
    )
    guide_file = tmp_path / "legacy_guide.txt"
    guide_file.write_bytes(legacy_text.encode("cp1252"))

    guide = parse_walkthrough_file(guide_file, game_id="legacy", title="Legacy Game")

    assert len(guide.chapters) == 1
    assert guide.chapters[0].title == "Kokiri Forest"
    assert guide.chapters[0].sections[0].title == "Link’s Hidden Sword"


def test_empty_walkthrough_returns_empty_chapters() -> None:
    guide = parse_walkthrough("   \n\n  ", game_id="empty", title="Empty")

    assert guide.chapters == ()
