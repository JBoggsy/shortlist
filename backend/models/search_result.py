from backend.database import db


class SearchResult(db.Model):
    __tablename__ = "search_results"

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey("conversations.id"), nullable=False)

    # Job data (mirrors Job model fields for easy promotion to tracker)
    company = db.Column(db.String(200), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    url = db.Column(db.String(500))
    salary_min = db.Column(db.Integer)
    salary_max = db.Column(db.Integer)
    location = db.Column(db.String(200))
    remote_type = db.Column(db.String(50))
    source = db.Column(db.String(200))
    description = db.Column(db.Text)
    requirements = db.Column(db.Text)
    nice_to_haves = db.Column(db.Text)

    # AI evaluation
    job_fit = db.Column(db.Integer)
    fit_reason = db.Column(db.Text)

    # State
    added_to_tracker = db.Column(db.Boolean, default=False)
    tracker_job_id = db.Column(db.Integer, db.ForeignKey("jobs.id"), nullable=True)

    created_at = db.Column(db.DateTime, server_default=db.func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "company": self.company,
            "title": self.title,
            "url": self.url,
            "salary_min": self.salary_min,
            "salary_max": self.salary_max,
            "location": self.location,
            "remote_type": self.remote_type,
            "source": self.source,
            "description": self.description,
            "requirements": self.requirements,
            "nice_to_haves": self.nice_to_haves,
            "job_fit": self.job_fit,
            "fit_reason": self.fit_reason,
            "added_to_tracker": self.added_to_tracker,
            "tracker_job_id": self.tracker_job_id,
            "created_at": (self.created_at.isoformat() + "+00:00") if self.created_at else None,
        }
