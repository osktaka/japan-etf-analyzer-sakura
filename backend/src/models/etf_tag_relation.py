"""ETF-Tag relation model for many-to-many relationship."""
from datetime import datetime

from . import db


class ETFTagRelation(db.Model):
    """ETF and Tag many-to-many relation."""

    __tablename__ = "etf_tag_relations"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    etf_code = db.Column(
        db.String(10),
        db.ForeignKey("etfs.code", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tag_id = db.Column(
        db.Integer,
        db.ForeignKey("tags.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    etf = db.relationship("ETF", back_populates="tag_relations")
    tag = db.relationship("Tag", back_populates="etf_relations")

    # Unique constraint
    __table_args__ = (
        db.UniqueConstraint("etf_code", "tag_id", name="uq_etr_etf_tag"),
    )

    def __repr__(self):
        return f"<ETFTagRelation {self.etf_code} - {self.tag_id}>"
