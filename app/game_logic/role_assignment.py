import random

class NotEnoughPlayers(Exception):
    pass

def select_litigants(player_ids, litigation_counts, random_number_gen=None):
    """Pick this round's plaintiff and defendant.
    Players who have litigated the fewest times so far are preferred, so everyone gets a turn before anyone goes twice. 
    Ties are broken randomly, as is which of the two chosen players is the plaintiff vs. defendant.
    Returns (plaintiff_id, defendant_id).
    """
    random_number_gen = random_number_gen or random

    player_ids = list(player_ids)
    if len(player_ids) < 2:
        raise NotEnoughPlayers("Need at least 2 players to assign roles")

    counts = {pid: litigation_counts.get(pid, 0) for pid in player_ids}
    min_count = min(counts.values())
    least_litigated = [pid for pid in player_ids if counts[pid] == min_count]

    if len(least_litigated) >= 2:
        chosen = random_number_gen.sample(least_litigated, 2)
    else:
        remaining = [pid for pid in player_ids if pid not in least_litigated]
        next_min = min(counts[pid] for pid in remaining)
        next_tier = [pid for pid in remaining if counts[pid] == next_min]
        chosen = least_litigated + [random_number_gen.choice(next_tier)]

    plaintiff, defendant = random_number_gen.sample(chosen, 2)
    return plaintiff, defendant
