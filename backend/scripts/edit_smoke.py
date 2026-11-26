#!/usr/bin/env python3
"""Check outfit editing against a running server: one item changes, the rest stays.

Covers the acceptance criteria of the editing task on the real stack (Qwen + wardrobe_rag):
add a jacket keeps the original IDs, replace shoes changes exactly one ID, no suitable
alternative means no new card, a question about the outfit does not change it, an ambiguous
request gets one question, and a new question after a beach dialogue does not inherit the beach.
"""
from __future__ import annotations

import argparse
import sys
from time import perf_counter
from typing import Any
from uuid import uuid4

import httpx

from defense_smoke import BEACH_QUERY, OFFICE_QUERY, SmokeFailure, request_json, require

OFFICE_CARD = ["item-1", "item-4", "item-42"]  # shirt, palazzo trousers, block-heel pumps
BEACH_CARD = ["item-18", "item-27", "item-39"]
NO_FLAT_SHOES = ["item-1", "item-4", "item-42", "item-35", "item-7", "item-33", "item-9"]


class Session:
    def __init__(self, client: httpx.Client, user_id: str, capsule: dict[str, dict[str, Any]], allow_mock: bool):
        self.client, self.user_id, self.capsule = client, user_id, capsule
        self.allowed = {"llm", "rules"} | ({"mock"} if allow_mock else set())

    def ask(self, case: str, query: str, card: list[str], request: str, *, wardrobe: list[str] | None = None,
            expect_card: bool = True) -> dict[str, Any]:
        items = [self.capsule[i] for i in wardrobe] if wardrobe else list(self.capsule.values())
        result, elapsed = request_json(self.client, "POST", "/api/recommend-outfit", json={
            "user_id": self.user_id, "query": query, "wardrobe": items, "debug": True,
            "history": [
                {"sender": "user", "text": request},
                {"sender": "assistant", "text": "В образ вошли: …", "hasOutfit": True, "itemIds": card},
            ],
        })
        timings = result.get("timings", {})
        ids = [item["id"] for item in (result.get("suggestedOutfit") or {}).get("items", [])]
        print(f"[{case}] clientMs={elapsed:.0f} retrievalMs={timings.get('retrievalMs', 0):.0f} "
              f"llmMs={timings.get('llmMs', 0):.0f} source={result.get('source')} ids={ids}", flush=True)
        print(f"    {result.get('text', '')[:260]}", flush=True)
        require(bool(ids) == expect_card,
                f"{case}: {'expected' if expect_card else 'unexpected'} outfit card; text={result.get('text')!r}")
        require(result.get("source") != "fallback",
                f"{case}: the model was replaced by a fallback; warnings={result.get('warnings')!r}")
        if expect_card:
            require(result.get("source") in self.allowed, f"{case}: unexpected source {result.get('source')!r}")
            require(result.get("referencedItemIds") == ids, f"{case}: referenced IDs disagree with the card")
            require(not result["text"].startswith(("В образ вошли:", "Заменил обувь")),
                    f"{case}: chat shows an inventory or an edit log instead of advice")
        return result


def run(session: Session) -> None:
    capsule = session.capsule
    category = {item_id: item["category"] for item_id, item in capsule.items()}

    added = session.ask("add jacket", "А можешь добавить какую-нибудь куртку, если похолодает?",
                        OFFICE_CARD, OFFICE_QUERY)
    ids = added["referencedItemIds"]
    new = [i for i in ids if i not in OFFICE_CARD]
    require(set(OFFICE_CARD) <= set(ids), f"add jacket: original IDs were not kept: {ids}")
    require(len(new) == 1 and category[new[0]] == "outerwear", f"add jacket: expected one new outerwear item, got {new}")
    require(added["edit"]["keptItemIds"] == OFFICE_CARD, "add jacket: edit.keptItemIds must equal the old card")

    replaced = session.ask("replace shoes", "Замени туфли на что-нибудь без каблука, остальное оставь", ids, OFFICE_QUERY)
    after = replaced["referencedItemIds"]
    require(len(set(ids) ^ set(after)) == 2 and len(after) == len(ids),
            f"replace shoes: exactly one ID must change: {ids} -> {after}")
    require("item-42" not in after and category[(set(after) - set(ids)).pop()] == "shoes",
            "replace shoes: the old pair must go and the new item must be footwear")

    none = session.ask("no alternative", "Замени туфли на обувь без каблука", OFFICE_CARD, OFFICE_QUERY,
                       wardrobe=NO_FLAT_SHOES, expect_card=False)
    require("без изменений" in none["text"] and "edit" not in none, "no alternative: the old outfit must stay")

    with_bag = [*OFFICE_CARD, "item-9"]
    removed = session.ask("without bag", "Без сумки, пожалуйста", with_bag, OFFICE_QUERY)
    require(sorted(removed["referencedItemIds"]) == sorted(OFFICE_CARD), "without bag: only the bag must go")

    shoes = session.ask("remove only shoes", "Убери обувь", OFFICE_CARD, OFFICE_QUERY, expect_card=False)
    require(shoes["text"].rstrip().endswith("?"), "remove only shoes: expected a clarifying question")

    comfort = session.ask("comfort question", "Мне в этом будет комфортно?", OFFICE_CARD, OFFICE_QUERY, expect_card=False)
    require("Чего я не знаю" in comfort["text"], "comfort question: unknowns must be stated")
    require(comfort.get("source") in session.allowed, f"comfort question: unexpected source {comfort.get('source')!r}")

    vague = session.ask("ambiguous", "Замени вот это", OFFICE_CARD, OFFICE_QUERY, expect_card=False)
    require(vague["text"].count("?") == 1 and vague["meta"].get("llmAttempts") == 0,
            "ambiguous: expected exactly one question and no model call")

    warmer = session.ask("warmer", "А можно потеплее?", OFFICE_CARD, OFFICE_QUERY)
    require(warmer.get("edit", {}).get("operation") == "restyle", "warmer: missing restyle metadata")

    advice = session.ask("birthday after beach", "С чем носить чёрные ботинки на день рождения?",
                         BEACH_CARD, BEACH_QUERY, expect_card=False)
    require("пляж" not in advice["text"].lower(), f"birthday after beach: the beach leaked: {advice['text']!r}")
    require("retriever" not in advice["meta"], "birthday after beach: advice must not search the wardrobe")

    outfit = session.ask("birthday from wardrobe", "С чем носить чёрные ботинки на день рождения из моего гардероба?",
                         BEACH_CARD, BEACH_QUERY)
    context = (outfit.get("retrieval") or {}).get("context", {})
    require(context.get("occasion") != "beach" and outfit["meta"].get("occasion") != "Пляж",
            f"birthday from wardrobe: beach occasion was inherited: {context!r}")
    require(context.get("temperature_c") is None, "birthday from wardrobe: +30°C was inherited from the beach request")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--timeout", type=float, default=300)
    parser.add_argument("--allow-mock", action="store_true",
                        help="Accept LLM_PROVIDER=mock and the built-in search (development dry run)")
    args = parser.parse_args()
    user_id = f"edit-smoke-{uuid4().hex}"
    started = perf_counter()
    try:
        with httpx.Client(base_url=args.base_url, timeout=args.timeout) as client:
            health, _ = request_json(client, "GET", "/health")
            llm, retrieval = health.get("llm", {}), health.get("retrieval", {})
            print(f"[health] llm={llm.get('provider')}/{llm.get('model')} retriever={retrieval.get('engine')}", flush=True)
            if not args.allow_mock:
                require(llm.get("provider") == "openai" and retrieval.get("engine") == "wardrobe_rag",
                        f"expected a real LLM and wardrobe_rag, got {llm!r} / {retrieval!r}")
            items, _ = request_json(client, "GET", "/api/wardrobe/base-capsule")
            capsule = {item["id"]: item for item in items}
            try:
                run(Session(client, user_id, capsule, args.allow_mock))
            finally:
                request_json(client, "POST", "/api/wardrobe/sync", json={"user_id": user_id, "items": []})
    except (SmokeFailure, httpx.InvalidURL) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"PASS: ten editing scenarios ({perf_counter() - started:.2f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
