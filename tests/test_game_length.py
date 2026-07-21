import pytest

from app.db import db
from app.game_logic.rooms import (
    MAX_TARGET_TURNS,
    MIN_TARGET_TURNS,
    RoomError,
    advance_to_jury_vote,
    advance_to_next_case,
    advance_to_scoreboard,
    create_room,
    end_game_now,
    join_room,
    set_target_turns,
    start_game,
)
from app.game_logic.state_machine import CASE_REVEAL, FINALE, VERDICT
from app.models import Case


def _complete_current_round(game, winner="plaintiff", damages=100):
    """Push the current round all the way through VERDICT -> JURY_VOTE ->
    SCOREBOARD, standing in for the judge service and jurors so tests can
    reach the round-boundary logic without needing either.
    """
    case = Case.query.filter_by(game_id=game.id, case_number=game.round_number).first()
    case.winner = winner
    case.damages = damages
    game.state = VERDICT
    db.session.commit()

    advance_to_jury_vote(game.join_code, game.host_token)
    return advance_to_scoreboard(game.join_code, game.host_token)


def test_create_room_defaults_target_turns_to_two(db):
    game = create_room()

    assert game.target_turns == 2


def test_create_room_accepts_a_custom_target_turns(db):
    game = create_room(target_turns=5)

    assert game.target_turns == 5


def test_create_room_clamps_out_of_range_target_turns(db):
    too_high = create_room(target_turns=999)
    too_low = create_room(target_turns=0)

    assert too_high.target_turns == MAX_TARGET_TURNS
    assert too_low.target_turns == MIN_TARGET_TURNS


def test_create_room_falls_back_to_default_on_garbage_input(db):
    game = create_room(target_turns="not a number")

    assert game.target_turns == 2


def test_set_target_turns_updates_the_game(db):
    game = create_room()

    updated = set_target_turns(game.join_code, game.host_token, 4)

    assert updated.target_turns == 4


def test_set_target_turns_rejects_wrong_host_token(db):
    game = create_room()

    with pytest.raises(RoomError):
        set_target_turns(game.join_code, "not-the-real-token", 4)


def test_set_target_turns_rejects_once_game_has_started(db):
    game = create_room()
    join_room(game.join_code, "Alex")
    join_room(game.join_code, "Sam")
    game = start_game(game.join_code, game.host_token)

    with pytest.raises(RoomError):
        set_target_turns(game.join_code, game.host_token, 4)


def test_next_case_starts_a_new_round_when_target_not_yet_reached(db):
    game = create_room(target_turns=2)
    join_room(game.join_code, "Alex")
    join_room(game.join_code, "Sam")
    game = start_game(game.join_code, game.host_token)  # round 1, each litigant now at 1/2
    game = _complete_current_round(game)

    updated = advance_to_next_case(game.join_code, game.host_token)

    assert updated.state == CASE_REVEAL
    assert updated.round_number == 2


def test_next_case_moves_to_finale_once_everyone_reached_target(db):
    game = create_room(target_turns=1)  # with 2 players, one round satisfies everyone
    join_room(game.join_code, "Alex")
    join_room(game.join_code, "Sam")
    game = start_game(game.join_code, game.host_token)
    game = _complete_current_round(game)

    updated = advance_to_next_case(game.join_code, game.host_token)

    assert updated.state == FINALE


def test_next_case_reaches_finale_after_enough_rounds_with_default_target(db):
    game = create_room()  # target_turns=2, 2 players -> 2 rounds needed
    join_room(game.join_code, "Alex")
    join_room(game.join_code, "Sam")
    game = start_game(game.join_code, game.host_token)
    game = _complete_current_round(game)

    game = advance_to_next_case(game.join_code, game.host_token)
    assert game.state == CASE_REVEAL  # not done after round 1

    game = _complete_current_round(game)
    game = advance_to_next_case(game.join_code, game.host_token)
    assert game.state == FINALE  # done after round 2


def test_next_case_rejects_wrong_host_token(db):
    game = create_room(target_turns=1)
    join_room(game.join_code, "Alex")
    join_room(game.join_code, "Sam")
    game = start_game(game.join_code, game.host_token)
    game = _complete_current_round(game)

    with pytest.raises(RoomError):
        advance_to_next_case(game.join_code, "not-the-real-token")


def test_next_case_rejects_outside_scoreboard(db):
    game = create_room()
    join_room(game.join_code, "Alex")
    join_room(game.join_code, "Sam")
    game = start_game(game.join_code, game.host_token)  # CASE_REVEAL, not SCOREBOARD

    with pytest.raises(RoomError):
        advance_to_next_case(game.join_code, game.host_token)


def test_end_game_now_forces_finale_from_any_active_state(db):
    game = create_room()
    join_room(game.join_code, "Alex")
    join_room(game.join_code, "Sam")
    game = start_game(game.join_code, game.host_token)  # CASE_REVEAL

    updated = end_game_now(game.join_code, game.host_token)

    assert updated.state == FINALE


def test_end_game_now_rejects_wrong_host_token(db):
    game = create_room()

    with pytest.raises(RoomError):
        end_game_now(game.join_code, "not-the-real-token")


def test_end_game_now_rejects_when_already_ended(db):
    game = create_room()
    end_game_now(game.join_code, game.host_token)

    with pytest.raises(RoomError):
        end_game_now(game.join_code, game.host_token)


def test_next_case_does_not_repeat_a_prompt_while_others_remain(db):
    game = create_room(target_turns=3)  # 2 players -> 3 rounds needed
    join_room(game.join_code, "Alex")
    join_room(game.join_code, "Sam")
    game = start_game(game.join_code, game.host_token)

    prompts_seen = set()
    for _ in range(3):
        case = Case.query.filter_by(game_id=game.id, case_number=game.round_number).first()
        prompts_seen.add(case.prompt)
        game = _complete_current_round(game)
        game = advance_to_next_case(game.join_code, game.host_token)

    assert len(prompts_seen) == 3  # 3 rounds, 3 distinct prompts, well within the 6-prompt bank


def test_settings_next_case_and_end_routes_work_end_to_end(client, db):
    create_resp = client.post("/api/rooms", json={"target_turns": 1})
    body = create_resp.get_json()
    join_code, host_token = body["join_code"], body["host_token"]
    assert body["target_turns"] == 1

    settings_resp = client.post(
        f"/api/rooms/{join_code}/settings", json={"host_token": host_token, "target_turns": 3}
    )
    assert settings_resp.get_json()["target_turns"] == 3

    client.post(f"/api/rooms/{join_code}/join", json={"name": "Alex"})
    client.post(f"/api/rooms/{join_code}/join", json={"name": "Sam"})
    client.post(f"/api/rooms/{join_code}/start", json={"host_token": host_token})

    end_resp = client.post(f"/api/rooms/{join_code}/end", json={"host_token": host_token})
    assert end_resp.get_json()["phase"] == FINALE
