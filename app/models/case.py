from app.db import db


class Case(db.Model):
    __tablename__ = "cases"

    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey("games.id"), nullable=True)
    case_number = db.Column(db.Integer, nullable=False)

    prompt = db.Column(db.Text, nullable=False)

    plaintiff_name = db.Column(db.String(32), nullable=False)
    plaintiff_avatar = db.Column(db.String(32), nullable=True)
    defendant_name = db.Column(db.String(32), nullable=False)
    defendant_avatar = db.Column(db.String(32), nullable=True)

    plaintiff_argument = db.Column(db.Text, nullable=True)
    defendant_argument = db.Column(db.Text, nullable=True)

    ruling = db.Column(db.Text, nullable=True)
    reasoning = db.Column(db.Text, nullable=True)
    winner = db.Column(db.String(16), nullable=True)             # Either "plaintiff" or "defendant"
    damages = db.Column(db.Integer, nullable=True)

    created_at = db.Column(db.DateTime, server_default=db.func.now())

    votes = db.relationship("Vote", back_populates="case", cascade="all, delete-orphan")
