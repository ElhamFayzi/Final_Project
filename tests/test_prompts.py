from app.game_logic.prompts import STARTER_PROMPTS, random_prompt


def test_random_prompt_returns_something_from_the_bank():
    assert random_prompt() in STARTER_PROMPTS


def test_random_prompt_avoids_excluded_prompts():
    exclude = set(STARTER_PROMPTS[:-1])  # exclude everything but the last one

    for _ in range(20):
        assert random_prompt(exclude=exclude) == STARTER_PROMPTS[-1]


def test_random_prompt_falls_back_to_the_full_bank_once_exhausted():
    exclude = set(STARTER_PROMPTS)  # every prompt already used

    result = random_prompt(exclude=exclude)

    assert result in STARTER_PROMPTS
