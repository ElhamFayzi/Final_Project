import random

STARTER_PROMPTS = [
    "Who has to be the one to kill the spider",
    "Whether cereal is a soup",
    "Who left one square of toilet paper on the roll",
    "The correct way to load a dishwasher",
    "Who ate the last of the good snacks and denied it",
    "The thermostat: 68°F vs. 78°F",
    "Who used the last of the coffee and put the empty bag back in the cabinet",
    "Who keeps 'borrowing' chargers and never giving them back",
    "Who ate the leftovers with someone else's name written right on the container",
    "Who never refills the ice tray",
    "Who parked so badly it took up two spots",
    "Who microwaved fish in a shared kitchen",
    "Who cranked the thermostat to an unlivable temperature without asking",
    "Who left dishes 'to soak' for four days",
    "Who subtweeted someone in a group chat that person was also in",
    "Who 'forgot' to invite them but posted the group photo anyway",
    "Who let the dog out and blamed the cat",
    "Who cut the line for the last parking spot",
    "Who never says thank you when the door gets held",
    "Who hogged the WiFi for a four-hour gaming session during finals week",
    "Who put the empty milk carton back in the fridge",
    "Who snoozed the alarm eleven times and let everyone else suffer",
    "Who spoiled the finale before anyone else could watch it",
    "Who borrowed the good hoodie and returned it with a mystery stain",
    "Who reheated the leftover garlic shrimp in a shared office microwave",
    "Who ghosted the group project until midnight before it was due",
    "Who ate the last slice that was very clearly promised to someone else",
    "Who used 'reply all' for something that should have been a DM",
    "Who left a passive-aggressive sticky note instead of just saying something",
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