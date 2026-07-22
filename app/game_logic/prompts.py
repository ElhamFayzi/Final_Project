import random

STARTER_PROMPTS = [
    "Who snoozed the alarm eleven times and let everyone else suffer",
    "Who parked so badly it took up two spots",
    "Whether cereal is a soup",
    "Who used 'reply all' for something that should have been a DM",
]


def random_prompt(exclude=()):
    """Pick a random prompt, avoiding ones already used this game where
    possible. Once every prompt has been used, allow repeats rather than
    ever failing to produce one.
    """
    pool = [p for p in STARTER_PROMPTS if p not in exclude]
    if not pool:
        pool = STARTER_PROMPTS
    return random.choice(pool)