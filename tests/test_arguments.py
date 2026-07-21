import pytest

from app.db import db
from app.game_logic.rooms import (
    RoomError,
    advance_to_arguments,
    create_room,
    join_room,
    start_game,
    submit_argument,
)
from app.game_logic.state_machine import ARGUMENTS, CASE_REVEAL
from app.models import Case


def _room_ready_for_arguments(db):
    game = create_room()
    join_room(game.join_code, "Alex")
    join_room(game.join_code, "Sam")
    game = start_game(game.join_code, game.host_token)
    return game


def test_advance_to_arguments_moves_phase_forward(db):
    game = _room_ready_for_arguments(db)

    updated = advance_to_arguments(game.join_code, game.host_token)

    assert updated.state == ARGUMENTS


def test_advance_to_arguments_stamps_the_case_start_time(db):
    game = _room_ready_for_arguments(db)

    advance_to_arguments(game.join_code, game.host_token)

    case = Case.query.filter_by(game_id=game.id, case_number=game.round_number).first()
    assert case.arguments_opened_at is not None


def test_advance_to_arguments_rejects_wrong_host_token(db):
    game = _room_ready_for_arguments(db)

    with pytest.raises(RoomError):
        advance_to_arguments(game.join_code, "not-the-real-token")


def test_advance_to_arguments_rejects_from_lobby(db):
    game = create_room()
    join_room(game.join_code, "Alex")
    join_room(game.join_code, "Sam")

    with pytest.raises(RoomError):
        advance_to_arguments(game.join_code, game.host_token)


def test_submit_argument_saves_text_for_plaintiff_and_defendant(db):
    game = _room_ready_for_arguments(db)
    advance_to_arguments(game.join_code, game.host_token)
    case = Case.query.filter_by(game_id=game.id, case_number=game.round_number).first()

    plaintiff_token = _token_for(game, case.plaintiff_name)
    defendant_token = _token_for(game, case.defendant_name)
    submit_argument(game.join_code, plaintiff_token, "It's obviously a sandwich.")
    submit_argument(game.join_code, defendant_token, "It is not.")

    reloaded = db.session.get(Case, case.id)
    assert reloaded.plaintiff_argument == "It's obviously a sandwich."
    assert reloaded.defendant_argument == "It is not."


def test_submit_argument_rejects_before_arguments_phase(db):
    game = _room_ready_for_arguments(db)  # still in CASE_REVEAL, not ARGUMENTS
    assert game.state == CASE_REVEAL
    case = Case.query.filter_by(game_id=game.id, case_number=game.round_number).first()

    with pytest.raises(RoomError):
        submit_argument(game.join_code, _token_for(game, case.plaintiff_name), "Too soon.")


def test_submit_argument_rejects_non_litigant(db):
    game = create_room()
    join_room(game.join_code, "Alex")
    join_room(game.join_code, "Sam")
    join_room(game.join_code, "Jordan")
    game = start_game(game.join_code, game.host_token)
    advance_to_arguments(game.join_code, game.host_token)

    case = Case.query.filter_by(game_id=game.id, case_number=game.round_number).first()
    juror_name = next(
        n for n in ("Alex", "Sam", "Jordan") if n not in (case.plaintiff_name, case.defendant_name)
    )

    with pytest.raises(RoomError):
        submit_argument(game.join_code, _token_for(game, juror_name), "I have thoughts.")


def test_submit_argument_rejects_empty_text(db):
    game = _room_ready_for_arguments(db)
    advance_to_arguments(game.join_code, game.host_token)
    case = Case.query.filter_by(game_id=game.id, case_number=game.round_number).first()

    with pytest.raises(RoomError):
        submit_argument(game.join_code, _token_for(game, case.plaintiff_name), "   ")


def _token_for(game, player_name):
    return next(p.token for p in game.players if p.name == player_name)


def test_argue_and_argument_routes_work_end_to_end(client, db):
    create_resp = client.post("/api/rooms")
    body = create_resp.get_json()
    join_code, host_token = body["join_code"], body["host_token"]

    p1 = client.post(f"/api/rooms/{join_code}/join", json={"name": "Alex"}).get_json()
    p2 = client.post(f"/api/rooms/{join_code}/join", json={"name": "Sam"}).get_json()

    start_resp = client.post(f"/api/rooms/{join_code}/start", json={"host_token": host_token})
    assert start_resp.get_json()["phase"] == CASE_REVEAL

    argue_resp = client.post(f"/api/rooms/{join_code}/argue", json={"host_token": host_token})
    assert argue_resp.get_json()["phase"] == ARGUMENTS

    plaintiff_name = argue_resp.get_json()["plaintiff"]["name"]
    plaintiff_token = p1["player_token"] if plaintiff_name == "Alex" else p2["player_token"]

    submit_resp = client.post(
        f"/api/rooms/{join_code}/argument",
        json={"token": plaintiff_token, "text": "It is a sandwich."},
    )
    assert submit_resp.get_json()["success"] is True
