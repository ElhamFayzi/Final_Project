import pytest

from app.game_logic.judge import JudgeClientError
from app.game_logic.rooms import (
    RoomError,
    advance_to_arguments,
    advance_to_verdict,
    create_room,
    join_room,
    start_game,
    submit_argument,
)
from app.game_logic.state_machine import VERDICT
from app.models import Case


def _client_returning(text):
    def _call(system_text, user_text):
        return text
    return _call


def _room_mid_arguments():
    game = create_room()
    join_room(game.join_code, "Alex")
    join_room(game.join_code, "Sam")
    game = start_game(game.join_code, game.host_token)
    advance_to_arguments(game.join_code, game.host_token)

    case = Case.query.filter_by(game_id=game.id, case_number=game.round_number).first()
    plaintiff_token = next(p.token for p in game.players if p.name == case.plaintiff_name)
    defendant_token = next(p.token for p in game.players if p.name == case.defendant_name)
    submit_argument(game.join_code, plaintiff_token, "It's a sandwich, obviously.")
    submit_argument(game.join_code, defendant_token, "It is not.")
    return game, case


def test_advance_to_verdict_saves_the_judges_ruling(db):
    game, case = _room_mid_arguments()
    good_verdict = (
        '{"ruling": "Sandwich.", "reasoning": "Bread and filling.", '
        '"winner": "plaintiff", "damages": 300}'
    )

    updated = advance_to_verdict(
        game.join_code, game.host_token, client_factory=lambda: _client_returning(good_verdict)
    )

    assert updated.state == VERDICT
    reloaded = Case.query.filter_by(id=case.id).first()
    assert reloaded.ruling == "Sandwich."
    assert reloaded.winner == "plaintiff"
    assert reloaded.damages == 300


def test_advance_to_verdict_rejects_wrong_host_token(db):
    game, _ = _room_mid_arguments()

    with pytest.raises(RoomError):
        advance_to_verdict(game.join_code, "not-the-real-token")


def test_advance_to_verdict_rejects_outside_arguments_phase(db):
    game = create_room()
    join_room(game.join_code, "Alex")
    join_room(game.join_code, "Sam")
    game = start_game(game.join_code, game.host_token)  # CASE_REVEAL, not ARGUMENTS

    with pytest.raises(RoomError):
        advance_to_verdict(game.join_code, game.host_token)


def test_advance_to_verdict_falls_back_when_no_client_is_available(db):
    game, _ = _room_mid_arguments()

    def _broken_factory():
        raise JudgeClientError("GEMINI_API_KEY is not set")

    updated = advance_to_verdict(game.join_code, game.host_token, client_factory=_broken_factory)

    assert updated.state == VERDICT
    case = Case.query.filter_by(game_id=game.id, case_number=game.round_number).first()
    assert case.winner in ("plaintiff", "defendant")
    assert case.ruling  # some text, doesn't crash the round


def test_advance_to_verdict_falls_back_when_the_client_call_fails(db):
    game, _ = _room_mid_arguments()

    def _raising_client(system_text, user_text):
        raise RuntimeError("network exploded")

    updated = advance_to_verdict(
        game.join_code, game.host_token, client_factory=lambda: _raising_client
    )

    assert updated.state == VERDICT
    case = Case.query.filter_by(game_id=game.id, case_number=game.round_number).first()
    assert case.winner in ("plaintiff", "defendant")


def test_advance_to_verdict_falls_back_on_malformed_json(db):
    game, _ = _room_mid_arguments()

    updated = advance_to_verdict(
        game.join_code, game.host_token, client_factory=lambda: _client_returning("not json at all")
    )

    assert updated.state == VERDICT
    case = Case.query.filter_by(game_id=game.id, case_number=game.round_number).first()
    assert case.winner in ("plaintiff", "defendant")


def test_verdict_route_works_end_to_end(client, db):
    create_resp = client.post("/api/rooms")
    body = create_resp.get_json()
    join_code, host_token = body["join_code"], body["host_token"]

    client.post(f"/api/rooms/{join_code}/join", json={"name": "Alex"})
    client.post(f"/api/rooms/{join_code}/join", json={"name": "Sam"})
    client.post(f"/api/rooms/{join_code}/start", json={"host_token": host_token})
    client.post(f"/api/rooms/{join_code}/argue", json={"host_token": host_token})

    # No fake client injected here on purpose -- this exercises the real
    # route, which falls back gracefully if GEMINI_API_KEY isn't set in
    # this environment, and otherwise hits the real API.
    verdict_resp = client.post(f"/api/rooms/{join_code}/verdict", json={"host_token": host_token})
    data = verdict_resp.get_json()

    assert data["phase"] == VERDICT
    assert data["winner"] in ("plaintiff", "defendant")
    assert isinstance(data["damages"], int)
