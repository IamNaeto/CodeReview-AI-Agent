import os
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.models import get_db, Review, Finding, AgentActivity
from app.api.schemas import (
    ReviewCreate, ReviewResponse, ReviewRequest, ReviewStatus,
    GitHubPRRequest, GitLabMRRequest, FindingResponse
)
from app.services.review_service import ReviewService
from app.services.github_service import GitHubService
from app.config import settings

router = APIRouter()
review_service = ReviewService()

class StartReviewResponse(BaseModel):
    review_id: int
    status: str
    message: str

def _check_config():
    """Raise HTTPException if configuration is invalid."""
    errors = settings.validate()
    if errors:
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Server configuration error",
                "errors": errors,
                "hint": "Check your .env file and ensure OPENROUTER_API_KEY is set correctly."
            }
        )

@router.post("/reviews/start", response_model=StartReviewResponse)
async def start_review(
    request: ReviewRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Start a new code review."""
    _check_config()

    try:
        review = await review_service.start_review(
            db=db,
            repo_url=request.repo_url,
            pr_number=request.pr_number,
            commit_sha=request.commit_sha,
            diff_content=request.diff_content,
            local_path=request.local_path,
            branch=request.branch,
            custom_rules=request.custom_rules
        )

        return StartReviewResponse(
            review_id=review.id,
            status=review.status,
            message="Review started successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/reviews/{review_id}", response_model=ReviewResponse)
async def get_review(review_id: int, db: Session = Depends(get_db)):
    """Get review details and findings."""
    review = review_service.get_review(db, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return review

@router.get("/reviews/{review_id}/status", response_model=ReviewStatus)
async def get_review_status(review_id: int, db: Session = Depends(get_db)):
    """Get review execution status."""
    status = review_service.get_review_status(db, review_id)
    if not status:
        raise HTTPException(status_code=404, detail="Review not found")
    return status

@router.get("/reviews", response_model=List[ReviewResponse])
async def list_reviews(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List all reviews with pagination."""
    return review_service.list_reviews(db, skip=skip, limit=limit)

@router.post("/reviews/github-pr")
async def review_github_pr(
    request: GitHubPRRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Review a GitHub pull request."""
    _check_config()
    repo_url = f"https://github.com/{request.owner}/{request.repo}.git"

    review = await review_service.start_review(
        db=db,
        repo_url=repo_url,
        pr_number=request.pr_number
    )

    return StartReviewResponse(
        review_id=review.id,
        status=review.status,
        message=f"Started review of PR #{request.pr_number} in {request.owner}/{request.repo}"
    )

@router.post("/reviews/{review_id}/post-github-comments")
async def post_github_comments(
    review_id: int,
    owner: str,
    repo: str,
    pr_number: int,
    db: Session = Depends(get_db)
):
    """Post review findings as GitHub PR comments."""
    if not settings.GITHUB_TOKEN:
        raise HTTPException(status_code=400, detail="GitHub token not configured")

    review = review_service.get_review(db, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    if review.status != "completed":
        raise HTTPException(status_code=400, detail="Review not yet completed")

    github = GitHubService()

    findings = db.query(Finding).filter(Finding.review_id == review_id).all()
    findings_data = [
        {
            "title": f.title,
            "severity": f.severity,
            "file_path": f.file_path,
            "line_start": f.line_start,
            "explanation": f.explanation,
            "impact": f.impact,
            "recommended_fix": f.recommended_fix
        }
        for f in findings
    ]

    pr_info = github.get_pr(owner, repo, pr_number)
    commit_id = pr_info.get('head', {}).get('sha')

    high_findings = [f for f in findings_data if f['severity'] in ['critical', 'high']]
    for finding in high_findings[:20]:
        if finding.get('file_path') and finding.get('line_start'):
            try:
                github.post_pr_comment(
                    owner, repo, pr_number,
                    body=f"**[{finding['severity'].upper()}] {finding['title']}**\n\n"
                         f"{finding['explanation']}\n\n"
                         f"**Impact:** {finding['impact']}\n"
                         f"**Fix:** {finding.get('recommended_fix', 'N/A')}",
                    commit_id=commit_id,
                    path=finding['file_path'],
                    line=finding['line_start']
                )
            except Exception as e:
                pass

    event_map = {
        "BLOCK MERGE": "REQUEST_CHANGES",
        "REQUEST CHANGES": "REQUEST_CHANGES",
        "APPROVE WITH COMMENTS": "COMMENT",
        "APPROVE": "APPROVE"
    }

    try:
        github.create_review(
            owner, repo, pr_number,
            findings=[],
            overall_comment=review.summary or "Code review completed.",
            event=event_map.get(review.overall_recommendation, "COMMENT")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to post review: {str(e)}")

    return {"message": "Comments posted successfully"}

@router.get("/github/repos/{owner}/{repo}/prs")
async def list_github_prs(owner: str, repo: str, state: str = "open"):
    """List pull requests from a GitHub repository."""
    if not settings.GITHUB_TOKEN:
        raise HTTPException(status_code=400, detail="GitHub token not configured")

    try:
        github = GitHubService()
        prs = github.list_prs(owner, repo, state)
        return prs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/github/repos/{owner}/{repo}/commits")
async def list_github_commits(
    owner: str, 
    repo: str, 
    sha: Optional[str] = None,
    per_page: int = Query(30, ge=1, le=100)
):
    """List commits from a GitHub repository."""
    if not settings.GITHUB_TOKEN:
        raise HTTPException(status_code=400, detail="GitHub token not configured")

    try:
        github = GitHubService()
        commits = github.get_commits(owner, repo, sha)
        return commits[:per_page]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
