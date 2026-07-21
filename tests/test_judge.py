"""Unit tests for the Petty Court judge logic."""

import json
import random

import pytest

from app.game_logic import (
    DEFENDANT,
    JudgeClientError,
    PLAINTIFF,
    Verdict,
    VerdictParseError,
    build_user_prompt,
    fallback_verdict,
    judge_case,
    parse_verdict,
)

SAMPLE_PROMPT = "Whether cereal is a soup"

GOOD_VERDICT = {
    "ruling": "Cereal is a cold soup and I will hear no objections.",
    "reasoning": "Liquid base, solid bits, eaten with a spoon. Soup.",
    "winner": "plaintiff",
    "damages": 250,
}

def _client_returning(text):
    """A fake client that records its inputs and returns given text."""
    def _call(system_text, user_text):
        _call.system = system_text
        _call.user = user_text
        return text
    return _call

def _judge_args(client, random_number_gen=None):
    return dict(
        prompt=SAMPLE_PROMPT,
        plaintiff_name="Alex",
        plaintiff_argument="It has broth-like milk. Soup.",
        defendant_name="Sam",
        defendant_argument="Soup is hot. Cereal is not.",
        client=client,
        random_number_gen=random_number_gen,
    )

# --- build_user_prompt ----------------------------------------------
def test_user_prompt_includes_case_and_both_sides():
    text = build_user_prompt(
        SAMPLE_PROMPT, "Alex", "milk is broth", "Sam", "soup is hot"
    )
    assert SAMPLE_PROMPT in text
    assert "Alex" in text and "Sam" in text
    assert "milk is broth" in text and "soup is hot" in text


def test_user_prompt_handles_missing_arguments():
    text = build_user_prompt(SAMPLE_PROMPT, "Alex", "", "Sam", None)
    assert text.count("(no argument submitted)") == 2

# --- parse_verdict --------------------------------------------------
def test_parse_clean_json():
    verdict = parse_verdict(json.dumps(GOOD_VERDICT))
    assert isinstance(verdict, Verdict)
    assert verdict.winner == PLAINTIFF
    assert verdict.damages == 250


def test_parse_strips_markdown_fences():
    fenced = "```json\n" + json.dumps(GOOD_VERDICT) + "\n```"
    assert parse_verdict(fenced).winner == PLAINTIFF


def test_parse_ignores_surrounding_prose():
    noisy = "Here it is!\n" + json.dumps(GOOD_VERDICT) + "\nCheers."
    assert parse_verdict(noisy).damages == 250


def test_parse_normalizes_winner_casing():
    payload = dict(GOOD_VERDICT, winner="Defendant")
    assert parse_verdict(json.dumps(payload)).winner == DEFENDANT


def test_parse_coerces_string_damages():
    payload = dict(GOOD_VERDICT, damages="300")
    assert parse_verdict(json.dumps(payload)).damages == 300


def test_parse_clamps_negative_damages_to_zero():
    payload = dict(GOOD_VERDICT, damages=-50)
    assert parse_verdict(json.dumps(payload)).damages == 0


def test_parse_rejects_missing_field():
    payload = {k: v for k, v in GOOD_VERDICT.items() if k != "ruling"}
    with pytest.raises(VerdictParseError):
        parse_verdict(json.dumps(payload))


def test_parse_rejects_invalid_winner():
    payload = dict(GOOD_VERDICT, winner="the judge")
    with pytest.raises(VerdictParseError):
        parse_verdict(json.dumps(payload))


def test_parse_rejects_non_numeric_damages():
    payload = dict(GOOD_VERDICT, damages="a lot")
    with pytest.raises(VerdictParseError):
        parse_verdict(json.dumps(payload))


def test_parse_rejects_empty_response():
    with pytest.raises(VerdictParseError):
        parse_verdict("   ")


def test_parse_rejects_non_json_text():
    with pytest.raises(VerdictParseError):
        parse_verdict("the defendant is guilty, no notes")


# --- fallback_verdict -----------------------------------------------

def test_fallback_is_a_valid_verdict():
    verdict = fallback_verdict(random_number_gen=random.Random(0))
    assert isinstance(verdict, Verdict)
    assert verdict.winner in (PLAINTIFF, DEFENDANT)
    assert verdict.ruling and verdict.reasoning
    assert verdict.damages == 0


def test_fallback_is_deterministic_with_seed():
    a = fallback_verdict(random_number_gen=random.Random(7)).winner
    b = fallback_verdict(random_number_gen=random.Random(7)).winner
    assert a == b


# --- judge_case -----------------------------------------------------
def test_judge_case_returns_parsed_verdict():
    client = _client_returning(json.dumps(GOOD_VERDICT))
    verdict = judge_case(**_judge_args(client))
    assert verdict.winner == PLAINTIFF
    assert verdict.damages == 250


def test_judge_case_passes_system_and_case_to_client():
    client = _client_returning(json.dumps(GOOD_VERDICT))
    judge_case(**_judge_args(client))
    assert "Judge Hootsworth" in client.system
    assert SAMPLE_PROMPT in client.user
    assert "Alex" in client.user and "Sam" in client.user


def test_judge_case_falls_back_on_garbage_response():
    client = _client_returning("lol I dunno")
    verdict = judge_case(**_judge_args(client, random.Random(1)))
    assert verdict.winner in (PLAINTIFF, DEFENDANT)
    assert "Mistrial" in verdict.ruling


def test_judge_case_falls_back_on_client_error():
    def _boom(system_text, user_text):
        raise JudgeClientError("network down")

    verdict = judge_case(**_judge_args(_boom, random.Random(1)))
    assert verdict.winner in (PLAINTIFF, DEFENDANT)
    assert verdict.damages == 0


# --- Verdict.to_dict ------------------------------------------------
def test_verdict_to_dict_matches_case_columns():
    verdict = parse_verdict(json.dumps(GOOD_VERDICT))
    assert verdict.to_dict() == {
        "ruling": GOOD_VERDICT["ruling"],
        "reasoning": GOOD_VERDICT["reasoning"],
        "winner": "plaintiff",
        "damages": 250,
    }