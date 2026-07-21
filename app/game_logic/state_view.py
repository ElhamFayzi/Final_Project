from app.models import Case
from app.game_logic.state_machine import (
    CASE_REVEAL,
    ARGUMENTS,
    VERDICT,
    JURY_VOTE,
    SCOREBOARD,
    FINALE,
)


def _player_public(player):
    return {
        "name": player.name,
        "avatar": player.avatar,
        "score": player.score,
        "connected": player.connected,
    }


def _current_case(game):
    return (
        Case.query.filter_by(game_id=game.id, case_number=game.round_number)
        .order_by(Case.id.desc())
        .first()
    )


def _score_rows(game):
    return sorted(
        (
            {"name": p.name, "pts": p.score, "connected": p.connected}
            for p in game.players
        ),
        key=lambda r: -r["pts"],
    )


def build_state(game):
    """
    Contract A — the single object every polling client renders from.
    Pure read: takes a Game row (with its related Players/Cases/Votes
    already committed) and returns a plain dict. No mutation, no network
    call, so this is easy to unit test with app-context fixtures alone.
    """
    state = {
        "phase": game.state,
        "join_code": game.join_code,
        "round": game.round_number,
        "target_turns": game.target_turns,
        "players": [_player_public(p) for p in game.players],
    }

    if game.state in (CASE_REVEAL, ARGUMENTS, VERDICT, JURY_VOTE):
        case = _current_case(game)
        if case:
            state["prompt"] = case.prompt
            state["plaintiff"] = {"name": case.plaintiff_name, "avatar": case.plaintiff_avatar}
            state["defendant"] = {"name": case.defendant_name, "avatar": case.defendant_avatar}

    if game.state == VERDICT:
        case = _current_case(game)
        if case:
            state["ruling"] = case.ruling
            state["reasoning"] = case.reasoning
            state["winner"] = case.winner
            state["damages"] = case.damages

    if game.state == JURY_VOTE:
        case = _current_case(game)
        if case:
            counts = {"plaintiff": 0, "defendant": 0}
            for vote in case.votes:
                counts[vote.choice] += 1
            state["votes"] = counts

    if game.state == SCOREBOARD:
        state["score_rows"] = _score_rows(game)

    if game.state == FINALE and game.players:
        champ = max(game.players, key=lambda p: p.score)
        state["champ_name"] = champ.name
        state["champ_pts"] = champ.score
        state["score_rows"] = _score_rows(game)

    return state