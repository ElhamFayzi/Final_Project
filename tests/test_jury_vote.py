import pytest

from app.db import db
from app.game_logic.rooms import (
    RoomError,
    advance_to_jury_vote,
    cast_vote,
    create_room,
    get_room_by_code,
    join_room,
    start_game,
)
from app.game_logic.state_machine import JURY_VOTE, VERDICT
from app.models import Case, Vote


def _room_ready_for_jury_vote(names):
    game = create_room()
    for name in names:
        join_room(game.join_code, name)
    game = start_game(game.join_code, game.host_token)
    game.state = VERDICT
    db.session.commit()
    return game


def _current_case(game):
    return Case.query.filter_by(game_id=game.id, case_number=game.round_number).first()


def _token_for(game, player_name):
    return next(p.token for p in game.players if p.name == player_name)


def test_advance_to_jury_vote_moves_phase_forward(db):
    game = _room_ready_for_jury_vote(["Alex", "Sam"])

    updated = advance_to_jury_vote(game.join_code, game.host_token)

    assert updated.state == JURY_VOTE


def test_advance_to_jury_vote_rejects_wrong_host_token(db):
    game = _room_ready_for_jury_vote(["Alex", "Sam"])

    with pytest.raises(RoomError):
        advance_to_jury_vote(game.join_code, "not-the-real-token")


def test_advance_to_jury_vote_rejects_from_wrong_state(db):
    game = create_room()
    join_room(game.join_code, "Alex")
    join_room(game.join_code, "Sam")
    game = start_game(game.join_code, game.host_token)  # CASE_REVEAL, not VERDICT

    with pytest.raises(RoomError):
        advance_to_jury_vote(game.join_code, game.host_token)


def test_cast_vote_records_choice(db):
    game = _room_ready_for_jury_vote(["Alex", "Sam", "Jordan"])
    advance_to_jury_vote(game.join_code, game.host_token)
    case = _current_case(game)
    juror = next(
        n for n in ("Alex", "Sam", "Jordan") if n not in (case.plaintiff_name, case.defendant_name)
    )

    cast_vote(game.join_code, _token_for(game, juror), "plaintiff")

    votes = Vote.query.filter_by(case_id=case.id).all()
    assert len(votes) == 1
    assert votes[0].choice == "plaintiff"


def test_cast_vote_allows_changing_choice(db):
    game = _room_ready_for_jury_vote(["Alex", "Sam", "Jordan"])
    advance_to_jury_vote(game.join_code, game.host_token)
    case = _current_case(game)
    juror = next(
        n for n in ("Alex", "Sam", "Jordan") if n not in (case.plaintiff_name, case.defendant_name)
    )
    juror_token = _token_for(game, juror)

    cast_vote(game.join_code, juror_token, "plaintiff")
    cast_vote(game.join_code, juror_token, "defendant")

    votes = Vote.query.filter_by(case_id=case.id).all()
    assert len(votes) == 1
    assert votes[0].choice == "defendant"


def test_cast_vote_rejects_litigant_voting(db):
    game = _room_ready_for_jury_vote(["Alex", "Sam"])
    advance_to_jury_vote(game.join_code, game.host_token)
    case = _current_case(game)

    with pytest.raises(RoomError):
        cast_vote(game.join_code, _token_for(game, case.plaintiff_name), "plaintiff")


def test_cast_vote_rejects_invalid_choice(db):
    game = _room_ready_for_jury_vote(["Alex", "Sam", "Jordan"])
    advance_to_jury_vote(game.join_code, game.host_token)
    case = _current_case(game)
    juror = next(
        n for n in ("Alex", "Sam", "Jordan") if n not in (case.plaintiff_name, case.defendant_name)
    )

    with pytest.raises(RoomError):
        cast_vote(game.join_code, _token_for(game, juror), "nobody")


def test_cast_vote_rejects_before_jury_vote_phase(db):
    game = _room_ready_for_jury_vote(["Alex", "Sam", "Jordan"])  # state is VERDICT, not JURY_VOTE yet
    case = _current_case(game)
    juror = next(
        n for n in ("Alex", "Sam", "Jordan") if n not in (case.plaintiff_name, case.defendant_name)
    )

    with pytest.raises(RoomError):
        cast_vote(game.join_code, _token_for(game, juror), "plaintiff")


def test_deliberate_and_vote_routes_work_end_to_end(client, db):
    create_resp = client.post("/api/rooms")
    body = create_resp.get_json()
    join_code, host_token = body["join_code"], body["host_token"]

    players = {}
    for name in ("Alex", "Sam", "Jordan"):
        join_resp = client.post(f"/api/rooms/{join_code}/join", json={"name": name})
        players[name] = join_resp.get_json()

    start_resp = client.post(
        f"/api/rooms/{join_code}/start", json={"host_token": host_token}
    ).get_json()
    litigants = {start_resp["plaintiff"]["name"], start_resp["defendant"]["name"]}
    juror_name = next(name for name in players if name not in litigants)

    game = get_room_by_code(join_code)
    game.state = VERDICT
    db.session.commit()

    deliberate_resp = client.post(f"/api/rooms/{join_code}/deliberate", json={"host_token": host_token})
    assert deliberate_resp.get_json()["phase"] == JURY_VOTE

    vote_resp = client.post(
        f"/api/rooms/{join_code}/vote",
        json={"token": players[juror_name]["player_token"], "choice": "plaintiff"},
    )
    assert vote_resp.get_json()["success"] is True
