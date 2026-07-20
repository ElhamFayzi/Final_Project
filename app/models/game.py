from app.db import db
from app.game_logic.tokens import generate_token


class Game(db.Model):
    __tablename__ = "games"

    id = db.Column(db.Integer, primary_key=True)
    join_code = db.Column(db.String(8), unique=True, nullable=False, index=True)
    host_token = db.Column(db.String(64), nullable=False, default=generate_token)
    state = db.Column(db.String(32), nullable=False, default="lobby")
    round_number = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    players = db.relationship("Player", back_populates="game", cascade="all, delete-orphan")