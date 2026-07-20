from flask import Blueprint, jsonify, request

from app.game_logic.rooms import (
    RoomError,
    connected_players,
    create_room,
    get_room_by_code,
    join_room,
    leave_room,
)

rooms_bp = Blueprint("rooms", __name__, url_prefix="/api/rooms")


def _error(message, status=400):
    return jsonify({"success": False, "error": message}), status


def _player_public_dict(player):
    return {
        "id": player.id,
        "name": player.name,
        "avatar": player.avatar,
        "score": player.score,
        "connected": player.connected,
    }


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

    return jsonify({
        "success": True,
        "join_code": game.join_code,
        "state": game.state,
        "round_number": game.round_number,
        "players": [_player_public_dict(p) for p in connected_players(game)],
    })