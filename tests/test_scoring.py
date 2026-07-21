from app.game_logic.scoring import JURY_BONUS, calculate_score_deltas


def test_winner_gets_the_damages_awarded():
    deltas = calculate_score_deltas("Alex", "Sam", winner="plaintiff", damages=400, votes=[])

    assert deltas == {"Alex": 400}


def test_defendant_can_win_too():
    deltas = calculate_score_deltas("Alex", "Sam", winner="defendant", damages=250, votes=[])

    assert deltas == {"Sam": 250}


def test_jurors_who_agreed_with_the_judge_get_a_bonus():
    votes = [("Jordan", "plaintiff"), ("Casey", "defendant")]

    deltas = calculate_score_deltas("Alex", "Sam", winner="plaintiff", damages=400, votes=votes)

    assert deltas == {"Alex": 400, "Jordan": JURY_BONUS}
    assert "Casey" not in deltas


def test_multiple_jurors_can_each_earn_the_bonus():
    votes = [("Jordan", "plaintiff"), ("Casey", "plaintiff")]

    deltas = calculate_score_deltas("Alex", "Sam", winner="plaintiff", damages=400, votes=votes)

    assert deltas["Jordan"] == JURY_BONUS
    assert deltas["Casey"] == JURY_BONUS


def test_zero_damages_still_records_the_winner():
    deltas = calculate_score_deltas("Alex", "Sam", winner="plaintiff", damages=0, votes=[])

    assert deltas == {"Alex": 0}


def test_missing_damages_defaults_to_zero():
    deltas = calculate_score_deltas("Alex", "Sam", winner="plaintiff", damages=None, votes=[])

    assert deltas == {"Alex": 0}
