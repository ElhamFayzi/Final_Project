from flask import Blueprint, jsonify, request

from app.game_logic.rooms import (
    RoomError,
    create_room,
    get_room_by_code,
    join_room,
    leave_room,
    start_game,
)
from app.game_logic.state_view import build_state

rooms_bp = Blueprint("rooms", __name__, url_prefix="/api/rooms")


def _error(message, status=400):
    return jsonify({"success": False, "error": message}), status


@rooms_bp.route("", methods=["POST"])
def create():
    game = create_room()
    return jsonify({"success": True, "join_code": game.join_code, "host_token": game.host_token})


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