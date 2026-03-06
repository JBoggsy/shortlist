"""DspyExample model — stores training examples for DSPy module optimization."""

from backend.database import db


class DspyExample(db.Model):
    __tablename__ = "dspy_examples"

    id = db.Column(db.Integer, primary_key=True)
    module_name = db.Column(db.String(100), nullable=False, index=True)
    inputs_json = db.Column(db.Text, nullable=False)
    output_json = db.Column(db.Text, nullable=False)
    score = db.Column(db.Float, nullable=True)
    metadata_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    scored_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "module_name": self.module_name,
            "inputs_json": self.inputs_json,
            "output_json": self.output_json,
            "score": self.score,
            "metadata_json": self.metadata_json,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "scored_at": self.scored_at.isoformat() if self.scored_at else None,
        }
