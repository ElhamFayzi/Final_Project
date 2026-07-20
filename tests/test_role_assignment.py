import random

import pytest

from app.game_logic import NotEnoughPlayers, select_litigants


def test_raises_with_fewer_than_two_players():
    with pytest.raises(NotEnoughPlayers):
        select_litigants(["a"], {})


def test_returns_two_distinct_players_from_the_pool():
    players = ["a", "b", "c", "d"]
    plaintiff, defendant = select_litigants(players, {}, random_number_gen=random.Random(0))

    assert plaintiff != defendant
    assert plaintiff in players
    assert defendant in players


def test_prefers_players_who_have_litigated_the_least():
    players = ["a", "b", "c", "d"]
    # a and b have already litigated twice each; c and d have never gone.
    counts = {"a": 2, "b": 2, "c": 0, "d": 0}

    plaintiff, defendant = select_litigants(players, counts, random_number_gen=random.Random(0))

    assert {plaintiff, defendant} == {"c", "d"}


def test_fills_remaining_slot_from_next_lowest_tier_when_tied_group_is_too_small():
    players = ["a", "b", "c", "d"]
    # only "d" is at the minimum; the second slot must come from the next tier (a/b at 1).
    counts = {"a": 1, "b": 1, "c": 2, "d": 0}

    plaintiff, defendant = select_litigants(players, counts, random_number_gen=random.Random(0))

    assert "d" in {plaintiff, defendant}
    other = (plaintiff if defendant == "d" else defendant)
    assert other in {"a", "b"}


def test_exactly_two_players_always_selected_regardless_of_counts():
    players = ["a", "b"]
    counts = {"a": 5, "b": 0}

    plaintiff, defendant = select_litigants(players, counts, random_number_gen=random.Random(0))

    assert {plaintiff, defendant} == {"a", "b"}


def test_is_deterministic_given_the_same_seeded_rng():
    players = ["a", "b", "c", "d"]
    result_1 = select_litigants(players, {}, random_number_gen=random.Random(42))
    result_2 = select_litigants(players, {}, random_number_gen=random.Random(42))

    assert result_1 == result_2
