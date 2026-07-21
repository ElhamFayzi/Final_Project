import pytest

from app.db import db
from app.game_logic.rooms import (
    RoomError,
    advance_to_jury_vote,
    advance_to_scoreboard,
    cast_vote,
    create_room,
    join_room,
    start_game,
)
from app.game_logic.scoring import JURY_BONUS
from app.game_logic.state_machine import SCOREBOARD, VERDICT
from app.models import Case, Player


def _room_ready_for_scoreboard(names, winner="plaintiff", damages=400):
    game = create_room()
    for name in names:
        join_room(game.join_code, name)
    game = start_game(game.join_code, game.host_token)

    case = Case.query.filter_by(game_id=game.id, case_number=game.round_number).first()
    case.winner = winner
    case.damages = damages
    db.session.commit()

    game.state = VERDICT
    db.session.commit()
    advance_to_jury_vote(game.join_code, game.host_token)
    return game, case


def test_advance_to_scoreboard_moves_phase_forward(db):
    game, _ = _room_ready_for_scoreboard(["Alex", "Sam"])

    updated = advance_to_scoreboard(game.join_code, game.host_token)

    assert updated.state == SCOREBOARD


def test_advance_to_scoreboard_rejects_wrong_host_token(db):
    game, _ = _room_ready_for_scoreboard(["Alex", "Sam"])

    with pytest.raises(RoomError):
        advance_to_scoreboard(game.join_code, "not-the-real-token")


def test_advance_to_scoreboard_rejects_without_a_verdict(db):
    game = create_room()
    join_room(game.join_code, "Alex")
    join_room(game.join_code, "Sam")
    game = start_game(game.join_code, game.host_token)  # case has no winner/damages yet
    game.state = VERDICT
    db.session.commit()
    advance_to_jury_vote(game.join_code, game.host_token)

    with pytest.raises(RoomError):
        advance_to_scoreboard(game.join_code, game.host_token)


def test_winner_receives_the_damages_awarded(db):
    game, case = _room_ready_for_scoreboard(["Alex", "Sam"], winner="plaintiff", damages=400)

    advance_to_scoreboard(game.join_code, game.host_token)

    winner_name = case.plaintiff_name
    winner = Player.query.filter_by(game_id=game.id, name=winner_name).first()
    assert winner.score == 400


def test_juror_who_agreed_with_the_judge_gets_the_bonus(db):
    game, case = _room_ready_for_scoreboard(["Alex", "Sam", "Jordan"], winner="plaintiff", damages=400)
    juror_name = next(
        n for n in ("Alex", "Sam", "Jordan") if n not in (case.plaintiff_name, case.defendant_name)
    )
    juror_token = next(p.token for p in game.players if p.name == juror_name)
    cast_vote(game.join_code, juror_token, "plaintiff")

    advance_to_scoreboard(game.join_code, game.host_token)

    juror = Player.query.filter_by(game_id=game.id, name=juror_name).first()
    assert juror.score == JURY_BONUS


def test_juror_who_disagreed_gets_nothing(db):
    game, case = _room_ready_for_scoreboard(["Alex", "Sam", "Jordan"], winner="plaintiff", damages=400)
    juror_name = next(
        n for n in ("Alex", "Sam", "Jordan") if n not in (case.plaintiff_name, case.defendant_name)
    )
    juror_token = next(p.token for p in game.players if p.name == juror_name)
    cast_vote(game.join_code, juror_token, "defendant")

    advance_to_scoreboard(game.join_code, game.host_token)

    juror = Player.query.filter_by(game_id=game.id, name=juror_name).first()
    assert juror.score == 0


def test_tally_route_works_end_to_end(client, db):
    create_resp = client.post("/api/rooms")
    body = create_resp.get_json()
    join_code, host_token = body["join_code"], body["host_token"]

    client.post(f"/api/rooms/{join_code}/join", json={"name": "Alex"})
    client.post(f"/api/rooms/{join_code}/join", json={"name": "Sam"})

    start_resp = client.post(f"/api/rooms/{join_code}/start", json={"host_token": host_token})
    plaintiff_name = start_resp.get_json()["plaintiff"]["name"]

    from app.game_logic.rooms import get_room_by_code

    game = get_room_by_code(join_code)
    case = Case.query.filter_by(game_id=game.id, case_number=game.round_number).first()
    case.winner = "plaintiff"
    case.damages = 400
    game.state = VERDICT
    db.session.commit()

    client.post(f"/api/rooms/{join_code}/deliberate", json={"host_token": host_token})
    tally_resp = client.post(f"/api/rooms/{join_code}/tally", json={"host_token": host_token})

    assert tally_resp.get_json()["phase"] == SCOREBOARD
    winner = Player.query.filter_by(game_id=game.id, name=plaintiff_name).first()
    assert winner.score == 400
