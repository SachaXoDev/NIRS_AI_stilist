from __future__ import annotations

from wardrobe_rag.constraints import assemble_outfit, validate_selection
from wardrobe_rag.schemas import Candidate, RetrievalResult


def make_result(items, **updates):
    slots = {slot: [] for slot in ("tops", "bottoms", "shoes", "outerwear", "accessories")}
    for item in items:
        slots[item.category].append(Candidate(item=item, score=1.0))
    data = {
        "user_id": "alice",
        "query": "город",
        "mode": "hybrid",
        "alpha": 0.65,
        "visual_weight": 0.35,
        "rrf_c": 60,
        "candidates_by_slot": slots,
        "wardrobe_revision": "test-revision",
        "model_fingerprint": "test-only",
    }
    data.update(updates)
    return RetrievalResult.model_validate(data)


def test_valid_selection_contains_only_canonical_items(wardrobe):
    result = make_result(wardrobe)
    validation = validate_selection(["top", "bottom", "shoe"], result)
    assert validation.valid and validation.complete
    assert {item.id for item in validation.selected_items} == {"top", "bottom", "shoe"}


def test_duplicate_and_unknown_ids_are_rejected(wardrobe):
    result = make_result(wardrobe)
    assert not validate_selection(["top", "top", "bottom", "shoe"], result).valid
    assert not validate_selection(["top", "bottom", "invented-shoe"], result).valid


def test_missing_shoes_are_reported_without_borrowing_items(wardrobe):
    result = make_result([item for item in wardrobe if item.category != "shoes"])
    validation = assemble_outfit(result)
    assert not validation.complete
    assert "shoes" in validation.missing_slots
    assert all(item.id != "shoe" for item in validation.selected_items)


def test_two_different_shoes_cannot_fill_a_single_slot(wardrobe, make_item):
    result = make_result([*wardrobe, make_item("shoe-2", "shoes", "Кеды")])
    validation = validate_selection(["top", "bottom", "shoe", "shoe-2"], result)
    assert not validation.valid


def test_assembly_respects_anchor_instead_of_the_first_top(wardrobe, make_item):
    result = make_result([*wardrobe, make_item("anchor", "tops", "Любимый джемпер")], anchor_item_id="anchor")
    validation = assemble_outfit(result)
    assert validation.complete and validation.valid
    ids = {item.id for item in validation.selected_items}
    assert "anchor" in ids
    assert "top" not in ids


def test_required_outerwear_is_checked_in_final_selection(wardrobe):
    result = make_result(wardrobe, required_slots=["tops", "bottoms", "shoes", "outerwear"])
    incomplete = validate_selection(["top", "bottom", "shoe"], result)
    assert not incomplete.complete
    assert "outerwear" in incomplete.missing_slots
    assert validate_selection(["top", "bottom", "shoe", "coat"], result).complete
