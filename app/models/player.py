from app.db import db
from app.game_logic.tokens import generate_token


class Player(db.Model):
    __tablename__ = "players"

    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey("games.id"), nullable=False)
    token = db.Column(db.String(64), nullable=False, default=generate_token)
    name = db.Column(db.String(32), nullable=False)
    avatar = db.Column(db.String(32), nullable=True)
    connected = db.Column(db.Boolean, nullable=False, default=True)
    score = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    game = db.relationship("Game", back_populates="players")