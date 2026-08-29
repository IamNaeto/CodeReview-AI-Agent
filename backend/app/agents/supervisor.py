import os
import json
import asyncio
from typing import List, Dict, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.config import settings
from app.models import Review, Finding, AgentActivity
from app.agents.base import extract_json_payload
from app.agents.correctness_agent import CorrectnessLogicAgent
from app.agents.security_agent import SecurityAgent
from app.agents.architecture_agent import ArchitectureAgent
from app.agents.performance_agent import PerformanceAgent
from app.agents.quality_agent import QualityAgent
from app.agents.testing_agent import TestingAgent
from app.agents.utils import get_file_language
from app.services.git_service import GitService, DiffInfo

class SupervisorAgent:
    def __init__(self, db: Session, review_id: int, custom_rules: Optional[str] = None):
        self.db = db
        self.review_id = review_id
        self.custom_rules = custom_rules
        self.llm = ChatOpenAI(
            model=settings.MODEL_NAME,
            api_key=settings.OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
            temperature=0.1,
            max_tokens=4000
        )

        self.agents = {
            'correctness': CorrectnessLogicAgent(),
            'security': SecurityAgent(),
            'architecture': ArchitectureAgent(),
            'performance': PerformanceAgent(),
            'quality': QualityAgent(),
            'testing': TestingAgent()
        }

    async def review(self, diff_info: DiffInfo, repo_path: Optional[str] = None) -> Dict[str, Any]:
        try:
            # Step 1: Determine which agents are relevant
            selected_agents = await self._select_agents(diff_info)

            # Step 2: Gather repository context if available
            repo_context = {}
            if repo_path and os.path.exists(repo_path):
                repo_context = self._gather_context(diff_info, repo_path)

            # Step 3: Execute selected agents in parallel
            all_findings = await self._execute_agents(selected_agents, diff_info, repo_context)

            # Step 4: Consolidate and deduplicate findings
            consolidated = self._consolidate_findings(all_findings)

            # Step 5: Cross-validate high-severity findings
            if settings.ENABLE_CROSS_VALIDATION:
                consolidated = await self._cross_validate(consolidated, diff_info, repo_context)

            # Step 6: Save findings to database
            self._save_findings(consolidated)

            # Step 7: Generate final report
            report = self._generate_report(consolidated)

            return report

        except Exception as e:
            # Mark review as failed and re-raise
            review = self.db.query(Review).filter(Review.id == self.review_id).first()
            if review:
                review.status = "failed"
                review.summary = f"Review failed: {str(e)}"
                review.completed_at = datetime.utcnow()
                self.db.commit()
            raise

    async def _select_agents(self, diff_info: DiffInfo) -> List[str]:
        file_types = {}
        for change in diff_info.changes:
            lang = get_file_language(change.file_path)
            file_types[lang] = file_types.get(lang, 0) + 1

        file_list = "\n".join([f"- {c.file_path} ({c.change_type}, +{c.additions}/-{c.deletions})" 
                                for c in diff_info.changes[:15]])

        prompt = f"""You are a Code Review Supervisor. Based on the following code changes, determine which specialist review agents should be invoked.

Available agents:
- correctness: Logic errors, edge cases, exception handling
- security: Authentication, injection, data exposure, vulnerabilities
- architecture: Design patterns, coupling, abstractions, layering
- performance: Algorithm efficiency, database queries, memory, blocking ops
- quality: Complexity, naming, duplication, dead code, readability
- testing: Missing tests, edge cases, error handling coverage

Changed files:
{file_list}

File type distribution: {json.dumps(file_types)}

Respond with a JSON array of agent names that are MOST relevant. Consider:
1. File types (e.g., .py files need correctness, config files need security)
2. Change patterns (e.g., new API endpoints need security and testing)
3. Size and complexity of changes
4. Presence of database queries, authentication, algorithms

Return ONLY a JSON array like ["correctness", "security", "testing"]. Include at least 3 agents."""

        try:
            response = await self.llm.ainvoke([SystemMessage(content=prompt)])
            content = response.content.strip() if response and response.content else ""
            payload = extract_json_payload(content)

            selected = json.loads(payload) if payload else []
            if not isinstance(selected, list):
                return list(self.agents.keys())

            valid = [a for a in selected if a in self.agents]
            if len(valid) < 2:
                return list(self.agents.keys())
            return valid
        except:
            return list(self.agents.keys())

    def _gather_context(self, diff_info: DiffInfo, repo_path: str) -> Dict[str, Any]:
        context = {}
        git_service = GitService()

        for change in diff_info.changes[:10]:
            file_ctx = git_service.get_repo_context(repo_path, change.file_path, max_files=5)
            context.update(file_ctx)

        context['dependencies'] = git_service.get_repo_context(repo_path, '.')
        return context

    async def _execute_agents(self, agent_names: List[str], diff_info: DiffInfo, 
                             repo_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        all_findings = []

        activities = {}
        for name in agent_names:
            activity = AgentActivity(
                review_id=self.review_id,
                agent_name=name,
                status="pending",
                started_at=datetime.utcnow()
            )
            self.db.add(activity)
            activities[name] = activity

        self.db.commit()

        tasks = []
        for name in agent_names:
            agent = self.agents[name]
            activity = activities[name]
            task = self._run_agent(agent, name, activity, diff_info, repo_context)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(results):
            name = agent_names[i]
            if isinstance(result, Exception):
                activity = activities[name]
                activity.status = "failed"
                activity.log = str(result)
                activity.completed_at = datetime.utcnow()
                # Re-raise API errors so the whole review fails
                raise result
            else:
                all_findings.extend(result)

        self.db.commit()
        return all_findings

    async def _run_agent(self, agent, name: str, activity, diff_info: DiffInfo, 
                        repo_context: Dict[str, Any]) -> List[Dict]:
        try:
            activity.status = "running"
            self.db.commit()

            findings = await agent.review(diff_info, repo_context)

            activity.status = "completed"
            activity.findings_count = len(findings)
            activity.completed_at = datetime.utcnow()
            self.db.commit()

            return findings
        except Exception as e:
            activity.status = "failed"
            activity.log = str(e)
            activity.completed_at = datetime.utcnow()
            self.db.commit()
            raise  # Propagate error up

    def _consolidate_findings(self, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not findings:
            return []

        severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3, 'optional': 4}
        findings.sort(key=lambda x: severity_order.get(x.get('severity', 'medium'), 2))

        consolidated = []
        seen = set()

        for finding in findings:
            file_path = finding.get('file_path', '') or ''
            line = str(finding.get('line_start', ''))
            title = finding.get('title', '')[:50].lower()

            sig = f"{file_path}:{line}:{title}"

            if sig in seen:
                existing = next((f for f in consolidated 
                               if f.get('file_path', '') == file_path 
                               and str(f.get('line_start', '')) == line
                               and f.get('title', '')[:50].lower() == title), None)
                if existing:
                    if severity_order.get(finding.get('severity'), 2) < severity_order.get(existing.get('severity'), 2):
                        existing['severity'] = finding['severity']
                    if finding.get('agent_name') and finding['agent_name'] not in str(existing.get('agent_name', '')):
                        existing['agent_name'] = f"{existing['agent_name']}, {finding['agent_name']}"
                    existing['cross_validated'] = True
                continue

            seen.add(sig)
            consolidated.append(finding)

        return consolidated

    async def _cross_validate(self, findings: List[Dict], diff_info: DiffInfo, 
                             repo_context: Dict) -> List[Dict]:
        high_severity = [f for f in findings if f.get('severity') in ['critical', 'high']]

        if not high_severity or len(self.agents) < 2:
            return findings

        validation_prompt = """You are a senior code reviewer validating findings from other specialists. 
For each finding below, confirm whether the issue is REAL and SIGNIFICANT, or if it might be a false positive.

Respond with a JSON array where each element has:
- "index": number
- "valid": true/false
- "reason": brief explanation

Be conservative - only mark as invalid if you are confident it's a false positive."""

        findings_text = "\n\n".join([
            f"{i+1}. [{f['severity'].upper()}] {f['title']}\n   File: {f.get('file_path', 'N/A')}:{f.get('line_start', 'N/A')}\n   {f['explanation'][:200]}"
            for i, f in enumerate(high_severity[:10])
        ])

        try:
            response = await self.llm.ainvoke([
                SystemMessage(content=validation_prompt),
                HumanMessage(content=f"Findings to validate:\n\n{findings_text}")
            ])

            content = response.content.strip() if response and response.content else ""
            payload = extract_json_payload(content)
            validations = json.loads(payload) if payload else []
            if not isinstance(validations, list):
                return findings

            for i, f in enumerate(high_severity[:10]):
                if i < len(validations):
                    validation = validations[i]
                    if isinstance(validation, dict) and not validation.get('valid', True):
                        original = f.get('severity')
                        if original == 'critical':
                            f['severity'] = 'high'
                        elif original == 'high':
                            f['severity'] = 'medium'
                        f['cross_validated'] = True
                        f['validation_note'] = validation.get('reason', 'Cross-validation suggested downgrade')
                    else:
                        f['cross_validated'] = True
                else:
                    f['cross_validated'] = True
        except:
            pass

        return findings

    def _save_findings(self, findings: List[Dict[str, Any]]):
        for finding in findings:
            db_finding = Finding(
                review_id=self.review_id,
                title=finding.get('title', 'Unnamed')[:255],
                category=finding.get('category', 'general')[:100],
                severity=finding.get('severity', 'medium')[:20],
                confidence=finding.get('confidence', 'medium')[:20],
                file_path=finding.get('file_path', '')[:500],
                line_start=finding.get('line_start'),
                line_end=finding.get('line_end'),
                explanation=finding.get('explanation', '')[:4000],
                impact=finding.get('impact', '')[:2000],
                recommended_fix=finding.get('recommended_fix', '')[:4000],
                agent_name=finding.get('agent_name', 'unknown')[:100],
                cross_validated=finding.get('cross_validated', False)
            )
            self.db.add(db_finding)

        self.db.commit()

    def _generate_report(self, findings: List[Dict[str, Any]]) -> Dict[str, Any]:
        severity_counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0, 'optional': 0}
        category_counts = {}

        for f in findings:
            sev = f.get('severity', 'medium')
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

            cat = f.get('category', 'general')
            category_counts[cat] = category_counts.get(cat, 0) + 1

        if severity_counts['critical'] > 0:
            recommendation = "BLOCK MERGE"
        elif severity_counts['high'] > 2:
            recommendation = "REQUEST CHANGES"
        elif severity_counts['high'] > 0 or severity_counts['medium'] > 5:
            recommendation = "APPROVE WITH COMMENTS"
        else:
            recommendation = "APPROVE"

        summary_parts = [f"Code Review Report\n{'='*50}\n"]
        summary_parts.append(f"Total findings: {len(findings)}")
        summary_parts.append(f"Critical: {severity_counts['critical']}, High: {severity_counts['high']}, "
                           f"Medium: {severity_counts['medium']}, Low: {severity_counts['low']}, "
                           f"Optional: {severity_counts['optional']}\n")

        if severity_counts['critical'] > 0:
            summary_parts.append(f"⚠️ {severity_counts['critical']} critical issue(s) must be resolved before merge.\n")

        if category_counts:
            summary_parts.append("Categories found:")
            for cat, count in sorted(category_counts.items(), key=lambda x: -x[1]):
                summary_parts.append(f"  - {cat}: {count}")

        summary = "\n".join(summary_parts)

        return {
            'recommendation': recommendation,
            'summary': summary,
            'severity_counts': severity_counts,
            'category_counts': category_counts,
            'findings_count': len(findings),
            'findings': findings
        }
