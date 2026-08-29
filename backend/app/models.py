from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Float, Boolean, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from app.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    repo_url = Column(String, nullable=True)
    pr_number = Column(Integer, nullable=True)
    commit_sha = Column(String, nullable=True)
    diff_content = Column(Text, nullable=True)
    status = Column(String, default="pending")  # pending, running, completed, failed
    overall_recommendation = Column(String, nullable=True)
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    metadata_json = Column(JSON, default=dict)

    findings = relationship("Finding", back_populates="review", cascade="all, delete-orphan")
    agent_activities = relationship("AgentActivity", back_populates="review", cascade="all, delete-orphan")

class Finding(Base):
    __tablename__ = "findings"

    id = Column(Integer, primary_key=True, index=True)
    review_id = Column(Integer, ForeignKey("reviews.id"))
    title = Column(String)
    category = Column(String)
    severity = Column(String)  # critical, high, medium, low, optional
    confidence = Column(String)  # high, medium, low
    file_path = Column(String, nullable=True)
    line_start = Column(Integer, nullable=True)
    line_end = Column(Integer, nullable=True)
    explanation = Column(Text)
    impact = Column(Text)
    recommended_fix = Column(Text, nullable=True)
    agent_name = Column(String)
    cross_validated = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    review = relationship("Review", back_populates="findings")

class AgentActivity(Base):
    __tablename__ = "agent_activities"

    id = Column(Integer, primary_key=True, index=True)
    review_id = Column(Integer, ForeignKey("reviews.id"))
    agent_name = Column(String)
    status = Column(String)  # pending, running, completed, failed
    findings_count = Column(Integer, default=0)
    log = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    review = relationship("Review", back_populates="agent_activities")

class ReviewHistory(Base):
    __tablename__ = "review_history"

    id = Column(Integer, primary_key=True, index=True)
    repo_url = Column(String)
    pr_number = Column(Integer, nullable=True)
    commit_sha = Column(String, nullable=True)
    review_id = Column(Integer, ForeignKey("reviews.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
