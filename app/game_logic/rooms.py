from app.db import db
from app.game_logic.tokens import generate_join_code
from app.game_logic.state_machine import (
    CASE_REVEAL,
    ARGUMENTS,
    VERDICT,
    JURY_VOTE,
    SCOREBOARD,
    FINALE,
    can_advance_to,
    next_state,
)
from app.game_logic.role_assignment import select_litigants, NotEnoughPlayers
from app.game_logic.prompts import random_prompt
from app.game_logic.scoring import calculate_score_deltas
from app.game_logic.judge import judge_case, fallback_verdict, JudgeClientError
from app.llm_client import make_client
from app.models import Game, Player, Case, Vote

MAX_PLAYERS = 200
MAX_NAME_LENGTH = 20
MAX_ARGUMENT_LENGTH = 1000
JOIN_CODE_LENGTH = 4
JOIN_CODE_MAX_ATTEMPTS = 20
MIN_PLAYERS_TO_START = 2
VALID_VOTE_CHOICES = ("plaintiff", "defendant")
DEFAULT_TARGET_TURNS = 2
MIN_TARGET_TURNS = 1
MAX_TARGET_TURNS = 20


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


def _clean_target_turns(value):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return DEFAULT_TARGET_TURNS
    return max(MIN_TARGET_TURNS, min(MAX_TARGET_TURNS, value))


def create_room(target_turns=None):
    clean_target_turns = _clean_target_turns(target_turns) if target_turns is not None else DEFAULT_TARGET_TURNS
    for _ in range(JOIN_CODE_MAX_ATTEMPTS):
        code = generate_join_code(JOIN_CODE_LENGTH)
        if get_room_by_code(code) is None:
            game = Game(join_code=code, target_turns=clean_target_turns)
            db.session.add(game)
            db.session.commit()
            return game
    raise RoomError("Could not generate a unique room code, please try again.")


def set_target_turns(join_code, host_token, target_turns):
    game = get_room_by_code(join_code)
    if game is None:
        raise RoomError("Room not found.")
    if game.host_token != host_token:
        raise RoomError("Not authorized to change this game's settings.")
    if game.state != "lobby":
        raise RoomError("Can't change settings after the game has started.")

    game.target_turns = _clean_target_turns(target_turns)
    db.session.commit()
    return game


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


def _begin_new_round(game, players):
    """Pick this round's litigants, create its Case, and advance the game
    into CASE_REVEAL. Shared by start_game (round 1) and advance_to_next_case
    (round 2+), since both are "begin a fresh round" moments.
    """
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

    _begin_new_round(game, players)
    db.session.commit()
    return game


def _current_case(game):
    return (
        Case.query.filter_by(game_id=game.id, case_number=game.round_number)
        .order_by(Case.id.desc())
        .first()
    )


def _game_is_complete(game, players):
    """Whether every currently connected player has litigated at least
    game.target_turns times. role_assignment's fairness guarantee (spread
    between most- and least-litigated stays <= 1) is what makes this a
    reliable stopping point rather than an arbitrary round count.
    """
    counts = _litigation_counts(game, players)
    return all(counts.get(p.id, 0) >= game.target_turns for p in players)


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


def advance_to_verdict(join_code, host_token, client_factory=None):
    client_factory = client_factory or make_client

    game = get_room_by_code(join_code)
    if game is None:
        raise RoomError("Room not found.")
    if game.host_token != host_token:
        raise RoomError("Not authorized to advance this game.")
    if not can_advance_to(game.state, VERDICT):
        raise RoomError(f"Cannot reach a verdict from state '{game.state}'.")

    case = _current_case(game)
    if case is None:
        raise RoomError("No case is currently in progress.")

    try:
        client = client_factory()
    except JudgeClientError:
        client = None

    if client is None:
        verdict = fallback_verdict()
    else:
        verdict = judge_case(
            case.prompt,
            case.plaintiff_name,
            case.plaintiff_argument,
            case.defendant_name,
            case.defendant_argument,
            client,
        )

    case.ruling = verdict.ruling
    case.reasoning = verdict.reasoning
    case.winner = verdict.winner
    case.damages = verdict.damages

    game.state = VERDICT
    db.session.commit()
    return game


def advance_to_jury_vote(join_code, host_token):
    game = get_room_by_code(join_code)
    if game is None:
        raise RoomError("Room not found.")
    if game.host_token != host_token:
        raise RoomError("Not authorized to advance this game.")
    if not can_advance_to(game.state, JURY_VOTE):
        raise RoomError(f"Cannot open jury voting from state '{game.state}'.")

    game.state = JURY_VOTE
    db.session.commit()
    return game


def cast_vote(join_code, player_token, choice):
    game = get_room_by_code(join_code)
    if game is None:
        raise RoomError("Room not found.")
    if game.state != JURY_VOTE:
        raise RoomError("Voting isn't open for this case.")

    player = get_player_by_token(game, player_token)
    if player is None:
        raise RoomError("Player not found in this room.")

    if choice not in VALID_VOTE_CHOICES:
        raise RoomError("Choice must be 'plaintiff' or 'defendant'.")

    case = _current_case(game)
    if case is None:
        raise RoomError("No case is currently in progress.")

    if player.name in (case.plaintiff_name, case.defendant_name):
        raise RoomError("Litigants can't vote on their own case.")

    vote = Vote.query.filter_by(case_id=case.id, player_id=player.id).first()
    if vote is None:
        vote = Vote(case_id=case.id, player_id=player.id, choice=choice)
        db.session.add(vote)
    else:
        vote.choice = choice

    db.session.commit()
    return vote


def advance_to_scoreboard(join_code, host_token):
    game = get_room_by_code(join_code)
    if game is None:
        raise RoomError("Room not found.")
    if game.host_token != host_token:
        raise RoomError("Not authorized to advance this game.")
    if not can_advance_to(game.state, SCOREBOARD):
        raise RoomError(f"Cannot open the scoreboard from state '{game.state}'.")

    case = _current_case(game)
    if case is None or case.winner not in VALID_VOTE_CHOICES:
        raise RoomError("This case doesn't have a verdict yet.")

    id_to_name = {p.id: p.name for p in game.players}
    votes = [(id_to_name[v.player_id], v.choice) for v in case.votes if v.player_id in id_to_name]
    deltas = calculate_score_deltas(case.plaintiff_name, case.defendant_name, case.winner, case.damages, votes)

    name_to_player = {p.name: p for p in game.players}
    for player_name, points in deltas.items():
        player = name_to_player.get(player_name)
        if player is not None:
            player.score += points

    game.state = SCOREBOARD
    db.session.commit()
    return game


def advance_to_next_case(join_code, host_token):
    game = get_room_by_code(join_code)
    if game is None:
        raise RoomError("Room not found.")
    if game.host_token != host_token:
        raise RoomError("Not authorized to advance this game.")
    if game.state != SCOREBOARD:
        raise RoomError(f"Cannot start the next case from state '{game.state}'.")

    players = connected_players(game)
    target = next_state(game.state, is_last_round=_game_is_complete(game, players))

    if target == FINALE:
        game.state = FINALE
        db.session.commit()
        return game

    if len(players) < MIN_PLAYERS_TO_START:
        raise RoomError(f"Need at least {MIN_PLAYERS_TO_START} players to continue.")

    _begin_new_round(game, players)
    db.session.commit()
    return game


def end_game_now(join_code, host_token):
    game = get_room_by_code(join_code)
    if game is None:
        raise RoomError("Room not found.")
    if game.host_token != host_token:
        raise RoomError("Not authorized to end this game.")
    if game.state == FINALE:
        raise RoomError("This game has already ended.")

    game.state = FINALE
    db.session.commit()
    return game