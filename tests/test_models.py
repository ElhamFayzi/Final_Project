import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Case, Game, Player, Vote


def test_game_defaults(db):
    game = Game(join_code="WIGZ")
    db.session.add(game)
    db.session.commit()

    assert game.id is not None
    assert game.state == "lobby"
    assert game.round_number == 0


def test_player_belongs_to_game(db):
    game = Game(join_code="WIGZ")
    db.session.add(game)
    db.session.commit()

    player = Player(game_id=game.id, name="Alice", avatar="cat")
    db.session.add(player)
    db.session.commit()

    assert player.game == game
    assert player in game.players


def test_case_can_be_created_before_verdict_is_known(db):
    case = Case(
        case_number=1,
        prompt="Is a hot dog a sandwich?",
        plaintiff_name="Alice",
        defendant_name="Bob",
    )
    db.session.add(case)
    db.session.commit()

    assert case.id is not None
    assert case.ruling is None
    assert case.winner is None
    assert case.damages is None


def test_case_can_be_updated_with_verdict(db):
    case = Case(
        case_number=1,
        prompt="Is a hot dog a sandwich?",
        plaintiff_name="Alice",
        defendant_name="Bob",
    )
    db.session.add(case)
    db.session.commit()

    case.ruling = "The hot dog is a sandwich."
    case.reasoning = "It meets the filling-between-bread standard."
    case.winner = "plaintiff"
    case.damages = 500
    db.session.commit()

    reloaded = db.session.get(Case, case.id)
    assert reloaded.winner == "plaintiff"
    assert reloaded.damages == 500


def test_vote_records_a_players_choice(db):
    game = Game(join_code="WIGZ")
    db.session.add(game)
    db.session.commit()

    juror = Player(game_id=game.id, name="Charlie", avatar="dog")
    db.session.add(juror)
    db.session.commit()

    case = Case(case_number=1, prompt="Is cereal a soup?", plaintiff_name="Alice", defendant_name="Bob")
    db.session.add(case)
    db.session.commit()

    vote = Vote(case_id=case.id, player_id=juror.id, choice="plaintiff")
    db.session.add(vote)
    db.session.commit()

    assert vote in case.votes


def test_a_player_cannot_vote_twice_on_the_same_case(db):
    game = Game(join_code="WIGZ")
    db.session.add(game)
    db.session.commit()

    juror = Player(game_id=game.id, name="Charlie", avatar="dog")
    db.session.add(juror)
    db.session.commit()

    case = Case(case_number=1, prompt="Is cereal a soup?", plaintiff_name="Alice", defendant_name="Bob")
    db.session.add(case)
    db.session.commit()

    db.session.add(Vote(case_id=case.id, player_id=juror.id, choice="plaintiff"))
    db.session.commit()

    db.session.add(Vote(case_id=case.id, player_id=juror.id, choice="defendant"))
    with pytest.raises(IntegrityError):
        db.session.commit()


def test_deleting_a_game_deletes_its_players(db):
    game = Game(join_code="WIGZ")
    db.session.add(game)
    db.session.commit()

    db.session.add(Player(game_id=game.id, name="Alice", avatar="cat"))
    db.session.commit()

    db.session.delete(game)
    db.session.commit()

    assert Player.query.count() == 0


def test_deleting_a_case_deletes_its_votes(db):
    game = Game(join_code="WIGZ")
    db.session.add(game)
    db.session.commit()

    juror = Player(game_id=game.id, name="Charlie", avatar="dog")
    db.session.add(juror)
    db.session.commit()

    case = Case(case_number=1, prompt="Is cereal a soup?", plaintiff_name="Alice", defendant_name="Bob")
    db.session.add(case)
    db.session.commit()

    db.session.add(Vote(case_id=case.id, player_id=juror.id, choice="plaintiff"))
    db.session.commit()

    db.session.delete(case)
    db.session.commit()

    assert Vote.query.count() == 0
