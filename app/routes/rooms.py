from flask import Blueprint, jsonify, request

from app.game_logic.rooms import (
    RoomError,
    advance_to_arguments,
    advance_to_jury_vote,
    advance_to_next_case,
    advance_to_scoreboard,
    advance_to_verdict,
    cast_vote,
    create_room,
    end_game_now,
    get_room_by_code,
    join_room,
    leave_room,
    set_target_turns,
    start_game,
    submit_argument,
)
from app.game_logic.state_view import build_state

rooms_bp = Blueprint("rooms", __name__, url_prefix="/api/rooms")


def _error(message, status=400):
    return jsonify({"success": False, "error": message}), status


@rooms_bp.route("", methods=["POST"])
def create():
    payload = request.get_json(silent=True) or {}
    game = create_room(payload.get("target_turns"))
    return jsonify({
        "success": True,
        "join_code": game.join_code,
        "host_token": game.host_token,
        "target_turns": game.target_turns,
    })


@rooms_bp.route("/<code>/join", methods=["POST"])
def join(code):
    payload = request.get_json(silent=True) or {}
    try:
        player = join_room(code, payload.get("name", ""))
    except RoomError as exc:
        return _error(str(exc))

    return jsonify({
        "success": True,
        "join_code": player.game.join_code,
        "player_token": player.token,
        "player_id": player.id,
    })


@rooms_bp.route("/<code>/leave", methods=["POST"])
def leave(code):
    payload = request.get_json(silent=True) or {}
    try:
        leave_room(code, payload.get("token", ""))
    except RoomError as exc:
        return _error(str(exc))
    return jsonify({"success": True})


@rooms_bp.route("/<code>", methods=["GET"])
def get_room(code):
    game = get_room_by_code(code)
    if game is None:
        return _error("Room not found.", 404)

    return jsonify({"success": True, **build_state(game)})


@rooms_bp.route("/<code>/start", methods=["POST"])
def start(code):
    payload = request.get_json(silent=True) or {}
    try:
        game = start_game(code, payload.get("host_token", ""))
    except RoomError as exc:
        return _error(str(exc))

    return jsonify({"success": True, **build_state(game)})


@rooms_bp.route("/<code>/argue", methods=["POST"])
def argue(code):
    payload = request.get_json(silent=True) or {}
    try:
        game = advance_to_arguments(code, payload.get("host_token", ""))
    except RoomError as exc:
        return _error(str(exc))

    return jsonify({"success": True, **build_state(game)})


@rooms_bp.route("/<code>/argument", methods=["POST"])
def argument(code):
    payload = request.get_json(silent=True) or {}
    try:
        submit_argument(code, payload.get("token", ""), payload.get("text", ""))
    except RoomError as exc:
        return _error(str(exc))

    return jsonify({"success": True})


@rooms_bp.route("/<code>/verdict", methods=["POST"])
def verdict(code):
    payload = request.get_json(silent=True) or {}
    try:
        game = advance_to_verdict(code, payload.get("host_token", ""))
    except RoomError as exc:
        return _error(str(exc))

    return jsonify({"success": True, **build_state(game)})


@rooms_bp.route("/<code>/deliberate", methods=["POST"])
def deliberate(code):
    payload = request.get_json(silent=True) or {}
    try:
        game = advance_to_jury_vote(code, payload.get("host_token", ""))
    except RoomError as exc:
        return _error(str(exc))

    return jsonify({"success": True, **build_state(game)})


@rooms_bp.route("/<code>/vote", methods=["POST"])
def vote(code):
    payload = request.get_json(silent=True) or {}
    try:
        cast_vote(code, payload.get("token", ""), payload.get("choice", ""))
    except RoomError as exc:
        return _error(str(exc))

    return jsonify({"success": True})


@rooms_bp.route("/<code>/tally", methods=["POST"])
def tally(code):
    payload = request.get_json(silent=True) or {}
    try:
        game = advance_to_scoreboard(code, payload.get("host_token", ""))
    except RoomError as exc:
        return _error(str(exc))

    return jsonify({"success": True, **build_state(game)})


@rooms_bp.route("/<code>/settings", methods=["POST"])
def settings(code):
    payload = request.get_json(silent=True) or {}
    try:
        game = set_target_turns(code, payload.get("host_token", ""), payload.get("target_turns"))
    except RoomError as exc:
        return _error(str(exc))

    return jsonify({"success": True, **build_state(game)})


@rooms_bp.route("/<code>/next-case", methods=["POST"])
def next_case(code):
    payload = request.get_json(silent=True) or {}
    try:
        game = advance_to_next_case(code, payload.get("host_token", ""))
    except RoomError as exc:
        return _error(str(exc))

    return jsonify({"success": True, **build_state(game)})


@rooms_bp.route("/<code>/end", methods=["POST"])
def end(code):
    payload = request.get_json(silent=True) or {}
    try:
        game = end_game_now(code, payload.get("host_token", ""))
    except RoomError as exc:
        return _error(str(exc))

    return jsonify({"success": True, **build_state(game)})