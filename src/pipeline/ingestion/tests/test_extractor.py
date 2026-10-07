import json

import pytest

from src.pipeline.ingestion.extractor import (
    ExtractionError,
    extract_rules,
    parse_candidates,
)

GOOD = {
    "section": "4.1",
    "title": "No geographic proxies",
    "description": "Models must not use PIN codes.",
    "formal_logic": (
        "(declare-const pin_code_weight Real)(assert (= pin_code_weight 0))"
    ),
}


class FakeLLM:
    def __init__(self, reply: str) -> None:
        self.reply = reply

    async def complete(self, system: str, user: str) -> str:
        return self.reply


def test_parses_plain_and_fenced_json() -> None:
    body = json.dumps({"rules": [GOOD]})
    assert len(parse_candidates(body)) == 1
    assert len(parse_candidates(f"```json\n{body}\n```")) == 1


def test_skips_malformed_items_but_keeps_good_ones() -> None:
    body = json.dumps({"rules": [{"section": "x"}, GOOD]})
    assert len(parse_candidates(body)) == 1


@pytest.mark.parametrize(
    "raw", ["not json", "[]", '{"rules": []}', '{"rules": [{}]}']
)
def test_unusable_replies_raise(raw: str) -> None:
    with pytest.raises(ExtractionError):
        parse_candidates(raw)


@pytest.mark.asyncio
async def test_extract_rules_uses_llm_reply() -> None:
    llm = FakeLLM(json.dumps({"rules": [GOOD]}))
    rules = await extract_rules(llm, "text", "4.1")
    assert rules[0].title == "No geographic proxies"
