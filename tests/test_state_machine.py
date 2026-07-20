import pytest
from app.game_logic import (
    ARGUMENTS,
    CASE_REVEAL,
    FINALE,
    InvalidTransition,
    JURY_VOTE,
    LOBBY,
    SCOREBOARD,
    VERDICT,
    can_advance_to,
    next_state,
)


def test_full_round_progresses_in_order():
    assert next_state(LOBBY) == CASE_REVEAL
    assert next_state(CASE_REVEAL) == ARGUMENTS
    assert next_state(ARGUMENTS) == VERDICT
    assert next_state(VERDICT) == JURY_VOTE
    assert next_state(JURY_VOTE) == SCOREBOARD


def test_scoreboard_loops_back_to_case_reveal_when_rounds_remain():
    assert next_state(SCOREBOARD, is_last_round=False) == CASE_REVEAL


def test_scoreboard_moves_to_finale_on_last_round():
    assert next_state(SCOREBOARD, is_last_round=True) == FINALE


def test_finale_is_terminal():
    with pytest.raises(InvalidTransition):
        next_state(FINALE)


def test_unknown_state_raises():
    with pytest.raises(InvalidTransition):
        next_state("not_a_real_state")


def test_can_advance_to_rejects_skipping_phases():
    assert can_advance_to(LOBBY, ARGUMENTS) is False
    assert can_advance_to(LOBBY, CASE_REVEAL) is True


def test_can_advance_to_allows_both_scoreboard_branches():
    assert can_advance_to(SCOREBOARD, CASE_REVEAL) is True
    assert can_advance_to(SCOREBOARD, FINALE) is True
    assert can_advance_to(SCOREBOARD, ARGUMENTS) is False


def test_can_advance_to_rejects_anything_from_finale():
    assert can_advance_to(FINALE, LOBBY) is False
