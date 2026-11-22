from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest
from navi_server.models import Chapter, GameGuide, Section


def _build_sample_guide() -> GameGuide:
    ch1 = Chapter(
        order=1,
        title="Forêt Kokiri",
        sections=(
            Section(title="Trouver l'Épée Kokiri", content="Passez dans le tunnel au sud-ouest.", order=1),
            Section(title="Acheter le Bouclier Mojo", content="Collectez 40 rubis dans le village.", order=2),
        ),
    )
    ch2 = Chapter(
        order=2,
        title="Arbre Mojo",
        sections=(
            Section(title="Boss : Gohma", content="Visez son œil avec le lance-pierre.", order=1),
        ),
    )
    ch3 = Chapter(
        order=3,
        title="Château d'Hyrule",
        sections=(
            Section(title="Infiltration", content="Évitez les gardes dans la cour.", order=1),
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
    assert all(ch.title != "Château d'Hyrule" for ch in visible)


def test_get_chapter_returns_match_or_none() -> None:
    guide = _build_sample_guide()
    ch2 = guide.get_chapter(2)

    assert ch2 is not None
    assert ch2.title == "Arbre Mojo"
    assert "Gohma" in ch2.full_text
    assert guide.get_chapter(99) is None


def test_models_are_immutable() -> None:
    section = Section(title="Test", content="Contenu", order=1)
    with pytest.raises(FrozenInstanceError):
        section.title = "Modifié"  # type: ignore[misc]