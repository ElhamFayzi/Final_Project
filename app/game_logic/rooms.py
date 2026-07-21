from app.db import db
from app.game_logic.tokens import generate_join_code
from app.game_logic.state_machine import CASE_REVEAL, ARGUMENTS, can_advance_to
from app.game_logic.role_assignment import select_litigants, NotEnoughPlayers
from app.game_logic.prompts import random_prompt
from app.models import Game, Player, Case

MAX_PLAYERS = 200
MAX_NAME_LENGTH = 20
MAX_ARGUMENT_LENGTH = 1000
JOIN_CODE_LENGTH = 4
JOIN_CODE_MAX_ATTEMPTS = 20
MIN_PLAYERS_TO_START = 2


class RoomError(ValueError):
    pass


def get_room_by_code(join_code):
    if not join_code:
        return None
    return Game.query.filter_by(join_code=join_code.strip().upper()).first()


def connected_players(game):
    return [p for p in game.players if p.connected]


def _litigation_counts(game, players):
    """How many times each player has already been plaintiff/defendant
    in this game. Matches on name rather than a foreign key, since Case
    snapshots names as plain text (see app/models/case.py) and join_room
    already enforces unique names within a single game.
    """
    counts = {p.id: 0 for p in players}
    name_to_id = {p.name: p.id for p in players}
    for case in Case.query.filter_by(game_id=game.id).all():
        if case.plaintiff_name in name_to_id:
            counts[name_to_id[case.plaintiff_name]] += 1
        if case.defendant_name in name_to_id:
            counts[name_to_id[case.defendant_name]] += 1
    return counts


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


def start_game(join_code, host_token):
    game = get_room_by_code(join_code)
    if game is None:
        raise RoomError("Room not found.")
    if game.host_token != host_token:
        raise RoomError("Not authorized to start this game.")
    if not can_advance_to(game.state, CASE_REVEAL):
        raise RoomError(f"Cannot start a game from state '{game.state}'.")

    players = connected_players(game)
    if len(players) < MIN_PLAYERS_TO_START:
        raise RoomError(f"Need at least {MIN_PLAYERS_TO_START} players to start.")

    litigation_counts = _litigation_counts(game, players)
    try:
        plaintiff_id, defendant_id = select_litigants(
            [p.id for p in players], litigation_counts
        )
    except NotEnoughPlayers as exc:
        raise RoomError(str(exc)) from exc

    plaintiff = next(p for p in players if p.id == plaintiff_id)
    defendant = next(p for p in players if p.id == defendant_id)

    game.round_number += 1
    game.state = CASE_REVEAL
    case = Case(
        game_id=game.id,
        case_number=game.round_number,
        prompt=random_prompt(),
        plaintiff_name=plaintiff.name,
        plaintiff_avatar=plaintiff.avatar,
        defendant_name=defendant.name,
        defendant_avatar=defendant.avatar,
    )
    db.session.add(case)
    db.session.commit()
    return game


def _current_case(game):
    return (
        Case.query.filter_by(game_id=game.id, case_number=game.round_number)
        .order_by(Case.id.desc())
        .first()
    )


def advance_to_arguments(join_code, host_token):
    game = get_room_by_code(join_code)
    if game is None:
        raise RoomError("Room not found.")
    if game.host_token != host_token:
        raise RoomError("Not authorized to advance this game.")
    if not can_advance_to(game.state, ARGUMENTS):
        raise RoomError(f"Cannot hear arguments from state '{game.state}'.")

    game.state = ARGUMENTS
    db.session.commit()
    return game


def submit_argument(join_code, player_token, text):
    game = get_room_by_code(join_code)
    if game is None:
        raise RoomError("Room not found.")
    if game.state != ARGUMENTS:
        raise RoomError("Arguments aren't open for this case.")

    player = get_player_by_token(game, player_token)
    if player is None:
        raise RoomError("Player not found in this room.")

    case = _current_case(game)
    if case is None:
        raise RoomError("No case is currently in progress.")

    clean_text = (text or "").strip()[:MAX_ARGUMENT_LENGTH]
    if not clean_text:
        raise RoomError("Enter an argument before submitting.")

    if player.name == case.plaintiff_name:
        case.plaintiff_argument = clean_text
    elif player.name == case.defendant_name:
        case.defendant_argument = clean_text
    else:
        raise RoomError("You are not a litigant in this case.")

    db.session.commit()
    return case