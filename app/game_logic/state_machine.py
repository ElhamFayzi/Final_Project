LOBBY = "lobby"
CASE_REVEAL = "case_reveal"
ARGUMENTS = "arguments"
VERDICT = "verdict"
JURY_VOTE = "jury_vote"
SCOREBOARD = "scoreboard"
FINALE = "finale"

ALL_STATES = (LOBBY, CASE_REVEAL, ARGUMENTS, VERDICT, JURY_VOTE, SCOREBOARD, FINALE)

_LINEAR_ORDER = [LOBBY, CASE_REVEAL, ARGUMENTS, VERDICT, JURY_VOTE, SCOREBOARD]


class InvalidTransition(Exception):
    pass


def next_state(current_state, *, is_last_round=False):
    """Return the phase that follows current_state.
    is_last_round only matters when leaving SCOREBOARD: the game either loops back for another round (CASE_REVEAL) or ends (FINALE).
    """
    if current_state == SCOREBOARD:
        return FINALE if is_last_round else CASE_REVEAL

    if current_state == FINALE:
        raise InvalidTransition("FINALE is a terminal state")

    try:
        return _LINEAR_ORDER[_LINEAR_ORDER.index(current_state) + 1]
    except ValueError:
        raise InvalidTransition(f"Unknown state: {current_state!r}")


def can_advance_to(current_state, target_state):
    """Whether moving directly from current_state to target_state is legal."""
    if current_state == FINALE:
        return False
    if current_state == SCOREBOARD:
        return target_state in (CASE_REVEAL, FINALE)
    try:
        return _LINEAR_ORDER[_LINEAR_ORDER.index(current_state) + 1] == target_state
    except ValueError:
        return False
