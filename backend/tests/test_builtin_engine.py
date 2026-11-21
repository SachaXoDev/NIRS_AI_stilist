import pytest

from app.rag.base import AnchorRejected, RetrievalQuery
from app.rag.builtin_engine import BuiltinEngine, lexical_scores
from app.services.analysis import analyze_query
from app.services.textutils import stem, tokenize
from app.storage.app_store import AppStore


@pytest.fixture
def engine(tmp_path, capsule):
    engine = BuiltinEngine(AppStore(str(tmp_path / "builtin.db")))
    engine.sync("alice", capsule)
    return engine


def _ids(outcome, slot):
    return [candidate.item.id for candidate in outcome.candidates_by_slot[slot]]


def test_stemming_merges_word_forms():
    assert stem("деловой") == stem("деловая") == stem("деловую")
    assert stem("кашемир") == stem("кашемировый")
    assert stem("шерсть") == stem("шерстяной")
    assert tokenize("Подбери образ с рубашкой") == [stem("рубашка")]


def test_lexical_scores_rank_the_obvious_item_first(capsule):
    query = "теплый свитер из кашемира"
    scores = lexical_scores(query, analyze_query(query), capsule)
    assert max(scores, key=scores.get) == "item-5"


def test_sync_reports_changes_and_is_idempotent(engine, capsule):
    again = engine.sync("alice", capsule)
    assert again["unchanged_count"] == 10 and again["added_count"] == again["deleted_count"] == 0

    edited = [item.model_copy(update={"color": "Красный"}) if item.id == "item-1" else item
              for item in capsule if item.id != "item-10"]
    report = engine.sync("alice", edited)
    assert (report["updated_count"], report["deleted_count"], report["unchanged_count"]) == (1, 1, 8)
    assert report["revision"] != again["revision"]
    assert "item-10" not in [item.id for item in engine.get_items("alice")]


def test_users_are_isolated(engine, capsule):
    engine.sync("bob", capsule[:2])
    assert len(engine.get_items("alice")) == 10 and len(engine.get_items("bob")) == 2
    engine.sync("bob", [])
    assert engine.get_items("bob") == [] and len(engine.get_items("alice")) == 10


def test_retrieve_groups_candidates_by_slot_with_budgets(engine):
    outcome = engine.retrieve(RetrievalQuery(user_id="alice", query="образ в офис на деловую встречу"))
    assert outcome.required_slots == ["tops", "bottoms", "shoes"] and not outcome.missing_slots
    assert _ids(outcome, "shoes")[0] == "item-8", "лоферы уместнее кед в офисе"
    assert all(len(group) <= 3 for group in outcome.candidates_by_slot.values())
    assert outcome.engine == outcome.diagnostics["engine"] == "builtin-bm25"
    assert any("запасной" in warning for warning in outcome.warnings)


def test_rain_or_cold_requires_outerwear_and_prefers_trench(engine):
    outcome = engine.retrieve(RetrievalQuery(user_id="alice", query="Дождь и +12°C"))
    assert "outerwear" in outcome.required_slots
    assert _ids(outcome, "outerwear")[0] == "item-6"
    assert outcome.context["temperature_c"] == 12 and outcome.context["rain"] is True


def test_missing_required_slot_is_reported(engine, capsule):
    engine.sync("carol", [item for item in capsule if item.category != "shoes"])
    outcome = engine.retrieve(RetrievalQuery(user_id="carol", query="образ на прогулку"))
    assert outcome.missing_slots == ["shoes"]


def test_anchor_is_pinned_first_and_unknown_anchor_is_rejected(engine):
    outcome = engine.retrieve(
        RetrievalQuery(user_id="alice", query="образ в офис", anchor_item_id="item-7")
    )
    first = outcome.candidates_by_slot["shoes"][0]
    assert first.item.id == "item-7" and first.anchored
    with pytest.raises(AnchorRejected):
        engine.retrieve(RetrievalQuery(user_id="alice", query="образ", anchor_item_id="ghost"))


def test_excluded_items_never_become_candidates(engine):
    outcome = engine.retrieve(
        RetrievalQuery(user_id="alice", query="образ в офис", exclude_item_ids=["item-8", "item-1"])
    )
    assert "item-8" not in _ids(outcome, "shoes") and "item-1" not in _ids(outcome, "tops")


def test_validate_selection_rules(engine):
    outcome = engine.retrieve(RetrievalQuery(user_id="alice", query="образ в офис"))
    ok = engine.validate_selection(["item-1", "item-4", "item-8", "item-2"], outcome)
    assert ok.valid and ok.complete and len(ok.items) == 4

    two_shoes = engine.validate_selection(["item-1", "item-4", "item-8", "item-7"], outcome)
    assert not two_shoes.valid and any("shoes" in v for v in two_shoes.violations)

    foreign = engine.validate_selection(["item-1", "item-4", "item-8", "gucci-bag"], outcome)
    assert not foreign.valid and any("gucci-bag" in v for v in foreign.violations)

    duplicate = engine.validate_selection(["item-1", "item-1", "item-4", "item-8"], outcome)
    assert not duplicate.valid

    no_shoes = engine.validate_selection(["item-1", "item-4"], outcome)
    assert no_shoes.valid and not no_shoes.complete and no_shoes.missing_slots == ["shoes"]


def test_validate_selection_requires_anchor(engine):
    outcome = engine.retrieve(
        RetrievalQuery(user_id="alice", query="образ в офис", anchor_item_id="item-10")
    )
    check = engine.validate_selection(["item-1", "item-4", "item-8"], outcome)
    assert not check.valid and any("anchor" in v.lower() for v in check.violations)


def test_validate_selection_detects_changed_wardrobe(engine, capsule):
    outcome = engine.retrieve(RetrievalQuery(user_id="alice", query="образ в офис"))
    engine.sync("alice", capsule[:9])
    check = engine.validate_selection(["item-1", "item-4", "item-8"], outcome)
    assert check.stale and not check.valid


def test_assemble_builds_complete_valid_outfit(engine):
    cold = engine.retrieve(RetrievalQuery(user_id="alice", query="Дождь и +12°C"))
    check = engine.assemble(cold)
    assert check.complete
    assert {"tops", "bottoms", "shoes", "outerwear"} <= {item.category for item in check.items}

    hot = engine.retrieve(RetrievalQuery(user_id="alice", query="прогулка, +28°C"))
    assert all(item.category != "outerwear" for item in engine.assemble(hot).items)
