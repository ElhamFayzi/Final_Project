from app.db import db


class Vote(db.Model):
    __tablename__ = "votes"
    __table_args__ = (db.UniqueConstraint("case_id", "player_id", name="uq_vote_case_player"),)

    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey("cases.id"), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey("players.id"), nullable=False)
    choice = db.Column(db.String(16), nullable=False)                                # Either "plaintiff" or "defendant"
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    case = db.relationship("Case", back_populates="votes")
