from backend.database import db


class ApplicationTodo(db.Model):
    __tablename__ = "application_todos"

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)

    category = db.Column(db.String(50), default="other")  # document, question, assessment, reference, other
    title = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text)
    completed = db.Column(db.Boolean, default=False)
    sort_order = db.Column(db.Integer, default=0)

    created_at = db.Column(db.DateTime, server_default=db.func.now())

    # Relationship back to Job
    job = db.relationship("Job", backref=db.backref("application_todos", cascade="all, delete-orphan", lazy="dynamic"))

    def to_dict(self):
        return {
            "id": self.id,
            "job_id": self.job_id,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "completed": self.completed,
            "sort_order": self.sort_order,
            "created_at": (self.created_at.isoformat() + "+00:00") if self.created_at else None,
        }
