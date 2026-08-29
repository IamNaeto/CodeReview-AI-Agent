import os
import json
import asyncio
from typing import List, Dict, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
from app.models import Review, Finding, AgentActivity, get_db
from app.config import settings
from app.services.git_service import GitService, DiffInfo

class ReviewService:
    def __init__(self):
        self.git_service = GitService()
        self.active_reviews: Dict[int, asyncio.Task] = {}

    async def start_review(self, db: Session, repo_url: Optional[str] = None,
                          pr_number: Optional[int] = None,
                          commit_sha: Optional[str] = None,
                          diff_content: Optional[str] = None,
                          local_path: Optional[str] = None,
                          branch: Optional[str] = None,
                          custom_rules: Optional[str] = None) -> Review:
        """Start a new code review."""

        review = Review(
            repo_url=repo_url,
            pr_number=pr_number,
            commit_sha=commit_sha,
            diff_content=diff_content,
            status="pending",
            metadata_json={
                "local_path": local_path,
                "branch": branch,
                "custom_rules": custom_rules
            }
        )
        db.add(review)
        db.commit()
        db.refresh(review)

        # Start review in background
        task = asyncio.create_task(
            self._execute_review(review.id, repo_url, pr_number, commit_sha, 
                               diff_content, local_path, branch, custom_rules)
        )
        self.active_reviews[review.id] = task

        return review

    async def _execute_review(self, review_id: int, repo_url: Optional[str],
                             pr_number: Optional[int], commit_sha: Optional[str],
                             diff_content: Optional[str], local_path: Optional[str],
                             branch: Optional[str], custom_rules: Optional[str]):
        """Execute the full review process."""
        from app.agents.supervisor import SupervisorAgent

        db = next(get_db())

        try:
            review = db.query(Review).filter(Review.id == review_id).first()
            review.status = "running"
            db.commit()

            # Get diff information
            diff_info = await self._get_diff_info(
                repo_url, pr_number, commit_sha, diff_content, local_path, branch
            )

            # Initialize supervisor
            supervisor = SupervisorAgent(db, review_id, custom_rules)

            # Run review
            result = await supervisor.review(diff_info, repo_url or local_path)

            # Update review with results
            review.status = "completed"
            review.overall_recommendation = result.get('recommendation', 'APPROVE WITH COMMENTS')
            review.summary = result.get('summary', '')
            review.completed_at = datetime.utcnow()
            db.commit()

        except Exception as e:
            review = db.query(Review).filter(Review.id == review_id).first()
            review.status = "failed"
            review.summary = f"Review failed: {str(e)}"
            review.completed_at = datetime.utcnow()
            db.commit()
        finally:
            db.close()
            if review_id in self.active_reviews:
                del self.active_reviews[review_id]

    async def _get_diff_info(self, repo_url, pr_number, commit_sha, diff_content, local_path, branch) -> DiffInfo:
        if diff_content:
            return self.git_service._parse_diff(diff_content, source="provided diff", target="unknown")
        elif pr_number and repo_url:
            return self.git_service.get_pr_diff(repo_url, pr_number, settings.GITHUB_TOKEN)
        elif commit_sha and repo_url:
            return self.git_service.get_commit_diff(repo_url, commit_sha)
        elif local_path:
            return self.git_service.get_local_diff(local_path, branch)
        else:
            raise ValueError("No valid review target provided")

    def get_review_status(self, db: Session, review_id: int) -> Dict[str, Any]:
        review = db.query(Review).filter(Review.id == review_id).first()
        if not review:
            return None

        activities = db.query(AgentActivity).filter(AgentActivity.review_id == review_id).all()
        total_agents = len(activities) if activities else 6  # Default expected
        completed = sum(1 for a in activities if a.status == "completed")

        current_agent = None
        for a in activities:
            if a.status == "running":
                current_agent = a.agent_name
                break

        progress = (completed / total_agents * 100) if total_agents > 0 else 0

        return {
            "review_id": review_id,
            "status": review.status,
            "progress": progress,
            "current_agent": current_agent,
            "message": review.summary if review.status == "completed" else None
        }

    def get_review(self, db: Session, review_id: int) -> Optional[Review]:
        return db.query(Review).filter(Review.id == review_id).first()

    def list_reviews(self, db: Session, skip: int = 0, limit: int = 50) -> List[Review]:
        return db.query(Review).order_by(Review.created_at.desc()).offset(skip).limit(limit).all()

    def cleanup(self):
        self.git_service.cleanup()
