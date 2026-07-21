from app.db import db
from app.game_logic.rooms import create_room, join_room, start_game, RoomError
from app.game_logic.state_view import build_state
from app.game_logic.state_machine import LOBBY, CASE_REVEAL, SCOREBOARD
from app.models import Case


def test_build_state_lobby_shape(db):
    game = create_room()
    join_room(game.join_code, "Alex")
    join_room(game.join_code, "Sam")

    state = build_state(game)

    assert state["phase"] == LOBBY
    assert state["join_code"] == game.join_code
    assert state["round"] == 0
    names = {p["name"] for p in state["players"]}
    assert names == {"Alex", "Sam"}
    assert "prompt" not in state  # no case yet in lobby


def test_start_game_creates_case_and_advances_phase(db):
    game = create_room()
    join_room(game.join_code, "Alex")
    join_room(game.join_code, "Sam")

    updated = start_game(game.join_code, game.host_token)

    assert updated.state == CASE_REVEAL
    assert updated.round_number == 1

    state = build_state(updated)
    assert state["phase"] == CASE_REVEAL
    assert "prompt" in state
    assert {state["plaintiff"]["name"], state["defendant"]["name"]} == {"Alex", "Sam"}


def test_start_game_rejects_wrong_host_token(db):
    game = create_room()
    join_room(game.join_code, "Alex")
    join_room(game.join_code, "Sam")

    try:
        start_game(game.join_code, "not-the-real-token")
        assert False, "expected RoomError"
    except RoomError:
        pass


def test_start_game_rejects_too_few_players(db):
    game = create_room()
    join_room(game.join_code, "Alex")  # only one player

    try:
        start_game(game.join_code, game.host_token)
        assert False, "expected RoomError"
    except RoomError:
        pass


def test_litigation_rotation_is_fair_across_many_rounds_in_one_game(db):
    game = create_room()
    names = ["Alex", "Sam", "Jordan", "Casey"]
    for name in names:
        join_room(game.join_code, name)

    counts = {name: 0 for name in names}
    for _ in range(8):  # 8 rounds x 2 slots = 16 slots / 4 players -> 4 turns each if fair
        game = start_game(game.join_code, game.host_token)
        case = Case.query.filter_by(game_id=game.id, case_number=game.round_number).first()
        counts[case.plaintiff_name] += 1
        counts[case.defendant_name] += 1
        game.state = SCOREBOARD
        db.session.commit()

    assert max(counts.values()) - min(counts.values()) <= 1


def test_polling_endpoint_returns_full_state(client, db):
    create_resp = client.post("/api/rooms")
    join_code = create_resp.get_json()["join_code"]
    host_token = create_resp.get_json()["host_token"]

    client.post(f"/api/rooms/{join_code}/join", json={"name": "Alex"})
    client.post(f"/api/rooms/{join_code}/join", json={"name": "Sam"})

    poll_resp = client.get(f"/api/rooms/{join_code}")
    data = poll_resp.get_json()
    assert data["phase"] == LOBBY
    assert len(data["players"]) == 2

    start_resp = client.post(f"/api/rooms/{join_code}/start", json={"host_token": host_token})
    assert start_resp.get_json()["phase"] == CASE_REVEAL

    poll_resp_2 = client.get(f"/api/rooms/{join_code}")
    assert poll_resp_2.get_json()["phase"] == CASE_REVEAL
    assert "prompt" in poll_resp_2.get_json()