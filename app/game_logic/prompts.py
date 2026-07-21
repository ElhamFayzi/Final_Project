import random

STARTER_PROMPTS = [
    "Who has to be the one to kill the spider",
    "Whether cereal is a soup",
    "Who left one square of toilet paper on the roll",
    "The correct way to load a dishwasher",
    "Who ate the last of the good snacks and denied it",
    "The thermostat: 68°F vs. 78°F",
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