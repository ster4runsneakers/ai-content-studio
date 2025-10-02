# models.py
from datetime import datetime
from uuid import uuid4
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Index

db = SQLAlchemy()

def gen_id():
    return uuid4().hex[:12]

class ABTest(db.Model):
    __tablename__ = "ab_tests"
    id = db.Column(db.String(12), primary_key=True, default=gen_id)
    name = db.Column(db.String(120), nullable=False)
    platform = db.Column(db.String(32), default="tiktok")
    target_url = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    variants = db.relationship("CaptionVariant", backref="test",
                               lazy="select", cascade="all, delete-orphan",
                               passive_deletes=True)
    events = db.relationship("ABEvent", backref="test",
                             lazy="select", cascade="all, delete-orphan",
                             passive_deletes=True)

class CaptionVariant(db.Model):
    __tablename__ = "caption_variants"
    id = db.Column(db.String(12), primary_key=True, default=gen_id)
    test_id = db.Column(db.String(12),
                        db.ForeignKey("ab_tests.id", ondelete="CASCADE"),
                        index=True, nullable=False)
    label = db.Column(db.String(32), nullable=False)  # A/B/C/D
    text = db.Column(db.Text, nullable=False)
    weight = db.Column(db.Float, default=1.0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    impressions = db.Column(db.Integer, default=0, nullable=False)
    copies = db.Column(db.Integer, default=0, nullable=False)
    clicks = db.Column(db.Integer, default=0, nullable=False)

Index("ix_caption_variants_test_label",
      CaptionVariant.test_id, CaptionVariant.label, unique=False)

class ABEvent(db.Model):
    __tablename__ = "ab_events"
    id = db.Column(db.String(12), primary_key=True, default=gen_id)
    test_id = db.Column(db.String(12),
                        db.ForeignKey("ab_tests.id", ondelete="CASCADE"),
                        index=True, nullable=False)
    variant_id = db.Column(db.String(12),
                           db.ForeignKey("caption_variants.id", ondelete="CASCADE"),
                           index=True, nullable=False)
    event = db.Column(db.String(32), nullable=False)  # impression|copy|click
    user_agent = db.Column(db.Text, nullable=True)
    ip_hash = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
