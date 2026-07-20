from app.db import db
from app.game_logic.tokens import generate_join_code
from app.models import Game, Player

MAX_PLAYERS = 200
MAX_NAME_LENGTH = 20
JOIN_CODE_LENGTH = 4
JOIN_CODE_MAX_ATTEMPTS = 20


class RoomError(ValueError):
    pass


def get_room_by_code(join_code):
    if not join_code:
        return None
    return Game.query.filter_by(join_code=join_code.strip().upper()).first()


def connected_players(game):
    return [p for p in game.players if p.connected]


def create_room():
    for _ in range(JOIN_CODE_MAX_ATTEMPTS):
        code = generate_join_code(JOIN_CODE_LENGTH)
        if get_room_by_code(code) is None:
            game = Game(join_code=code)
            db.session.add(game)
            db.session.commit()
            return game
    raise RoomError("Could not generate a unique room code, please try again.")


def join_room(join_code, name):
    game = get_room_by_code(join_code)
    if game is None:
        raise RoomError("Room not found.")
    if game.state != "lobby":
        raise RoomError("This game has already started.")

    clean_name = (name or "").strip()[:MAX_NAME_LENGTH]
    if not clean_name:
        raise RoomError("Enter a name.")

    existing = connected_players(game)
    if len(existing) >= MAX_PLAYERS:
        raise RoomError("Room is full.")
    if any(p.name.lower() == clean_name.lower() for p in existing):
        raise RoomError("Name already taken.")

    player = Player(game_id=game.id, name=clean_name)
    db.session.add(player)
    db.session.commit()
    return player


def get_player_by_token(game, token):
    if not token:
        return None
    return next((p for p in game.players if p.token == token), None)


def leave_room(join_code, token):
    game = get_room_by_code(join_code)
    if game is None:
        raise RoomError("Room not found.")

    player = get_player_by_token(game, token)
    if player is None:
        raise RoomError("Player not found in this room.")

    if game.state == "lobby":
        db.session.delete(player)
    else:
        player.connected = False
    db.session.commit()