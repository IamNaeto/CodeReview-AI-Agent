from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class FindingCreate(BaseModel):
    title: str
    category: str
    severity: str = Field(..., pattern="^(critical|high|medium|low|optional)$")
    confidence: str = Field(..., pattern="^(high|medium|low)$")
    file_path: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    explanation: str
    impact: str
    recommended_fix: Optional[str] = None
    agent_name: str
    cross_validated: bool = False

class FindingResponse(FindingCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class AgentActivityCreate(BaseModel):
    agent_name: str
    status: str
    findings_count: int = 0
    log: Optional[str] = None

class AgentActivityResponse(AgentActivityCreate):
    id: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True

class ReviewCreate(BaseModel):
    repo_url: Optional[str] = None
    pr_number: Optional[int] = None
    commit_sha: Optional[str] = None
    diff_content: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None

class ReviewResponse(BaseModel):
    id: int
    repo_url: Optional[str]
    pr_number: Optional[int]
    commit_sha: Optional[str]
    status: str
    overall_recommendation: Optional[str]
    summary: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]
    findings: List[FindingResponse] = []
    agent_activities: List[AgentActivityResponse] = []
    metadata_json: Optional[Dict[str, Any]]

    class Config:
        from_attributes = True

class ReviewRequest(BaseModel):
    repo_url: Optional[str] = None
    pr_number: Optional[int] = None
    commit_sha: Optional[str] = None
    diff_content: Optional[str] = None
    local_path: Optional[str] = None
    branch: Optional[str] = None
    custom_rules: Optional[str] = None

class GitHubPRRequest(BaseModel):
    owner: str
    repo: str
    pr_number: int

class GitLabMRRequest(BaseModel):
    project_id: str
    mr_iid: int

class ReviewStatus(BaseModel):
    review_id: int
    status: str
    progress: float
    current_agent: Optional[str]
    message: Optional[str]
