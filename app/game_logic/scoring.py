JURY_BONUS = 50


def calculate_score_deltas(plaintiff_name, defendant_name, winner, damages, votes):
    """Given the outcome of a completed case, return a dict of player_name -> points earned this round.

    winner: "plaintiff" or "defendant"; damages: points awarded to the winning litigant
    votes: iterable of (player_name, choice) pairs, one per juror who voted, where choice is "plaintiff" or "defendant"
    The winning litigant earns the damages awarded; each juror who voted with the judge earns a flat bonus for guessing right.
    """
    winner_name = plaintiff_name if winner == "plaintiff" else defendant_name
    deltas = {winner_name: damages or 0}

    for player_name, choice in votes:
        if choice == winner:
            deltas[player_name] = deltas.get(player_name, 0) + JURY_BONUS

    return deltas
