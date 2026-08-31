import os
import json
import logging
import re
from typing import List, Dict, Optional, Any
from abc import ABC, abstractmethod
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from app.config import settings

logger = logging.getLogger(__name__)


def extract_json_payload(text: Optional[str]) -> Optional[str]:
    if text is None:
        return None

    cleaned = text.strip()
    if not cleaned:
        return None

    if cleaned.startswith('[') or cleaned.startswith('{'):
        return cleaned

    code_block_matches = re.findall(r'```(?:json)?\s*(null|\[[\s\S]*?\]|\{[\s\S]*?\})\s*```', cleaned, flags=re.IGNORECASE)
    if code_block_matches:
        return code_block_matches[0].strip()

    for marker in ('```json', '```'):
        if marker in cleaned:
            parts = cleaned.split(marker)
            for part in parts[1:]:
                candidate = part.strip()
                if candidate.lower().startswith('null') or candidate.startswith('[') or candidate.startswith('{'):
                    return candidate.split('```')[0].strip()

    if cleaned.lower().startswith('null'):
        return None

    return None


class BaseReviewAgent(ABC):
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.llm = ChatOpenAI(
            model=settings.MODEL_NAME,
            api_key=settings.OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
            temperature=0.1,
            max_tokens=4000
        )

    @abstractmethod
    def get_system_prompt(self) -> str:
        pass

    def format_diff(self, diff_info) -> str:
        lines = [f"""You are reviewing CODE CHANGES. Lines prefixed with '+' are NEW CODE being added. Lines prefixed with '-' are code being removed. Lines without '+' or '-' are context.

IMPORTANT: Focus your analysis on ALL lines, especially those marked with '+' as they represent the actual changes.

Reviewing changes from {diff_info.source} to {diff_info.target}
"""]
        lines.append(f"Total files changed: {len(diff_info.changes)}")
        lines.append(f"Additions: {diff_info.total_additions}, Deletions: {diff_info.total_deletions}")

        for change in diff_info.changes[:20]:
            lines.append(f"\n=== File: {change.file_path} ({change.change_type}) ===")
            lines.append(f"Additions: {change.additions}, Deletions: {change.deletions}")
            lines.append("\n" + change.diff[:10000])
            lines.append("")

        if len(diff_info.changes) > 20:
            lines.append(f"\n... and {len(diff_info.changes) - 20} more files ...")

        return "\n".join(lines)

    def parse_findings(self, response_text: str) -> List[Dict[str, Any]]:
        findings = []
        parsed_json = False

        try:
            json_match = extract_json_payload(response_text)
            if json_match:
                data = json.loads(json_match.strip())
                parsed_json = True
                if isinstance(data, list):
                    findings = data
                elif isinstance(data, dict) and 'findings' in data:
                    findings = data['findings']
        except Exception as e:
            logger.warning(f"[{self.name}] JSON parse failed: {e}")

        if not findings and not parsed_json:
            findings = self._parse_text_findings(response_text)

        validated = []
        for f in findings:
            if isinstance(f, dict) and 'title' in f:
                validated.append({
                    'title': f.get('title', 'Unnamed Finding'),
                    'category': f.get('category', self.name),
                    'severity': self._normalize_severity(f.get('severity', 'medium')),
                    'confidence': self._normalize_confidence(f.get('confidence', 'medium')),
                    'file_path': f.get('file_path') or f.get('file') or f.get('path'),
                    'line_start': f.get('line_start') or f.get('line') or f.get('start_line'),
                    'line_end': f.get('line_end') or f.get('line_start') or f.get('line'),
                    'explanation': f.get('explanation', f.get('description', '')),
                    'impact': f.get('impact', f.get('description', '')),
                    'recommended_fix': f.get('recommended_fix') or f.get('fix') or f.get('recommendation'),
                    'agent_name': self.name
                })

        return validated

    def _parse_text_findings(self, text: str) -> List[Dict]:
        findings = []
        sections = text.split('\n\n---\n\n')
        for section in sections:
            if not section.strip():
                continue
            lines = section.strip().split('\n')
            if len(lines) < 3:
                continue

            finding = {
                'title': lines[0].replace('**', '').replace('# ', '').strip(),
                'explanation': '\n'.join(lines[1:]),
                'severity': 'medium',
                'confidence': 'medium',
                'agent_name': self.name
            }

            for line in lines:
                if 'severity:' in line.lower() or 'priority:' in line.lower():
                    finding['severity'] = line.split(':')[-1].strip().lower()
                if 'file:' in line.lower() or 'path:' in line.lower():
                    finding['file_path'] = line.split(':')[-1].strip()
                if 'line:' in line.lower():
                    try:
                        finding['line_start'] = int(line.split(':')[-1].strip().split('-')[0])
                    except:
                        pass

            findings.append(finding)

        return findings

    def _normalize_severity(self, severity: str) -> str:
        s = severity.lower()
        if s in ['critical', 'blocker', 'blocking']:
            return 'critical'
        elif s in ['high', 'major', 'important']:
            return 'high'
        elif s in ['medium', 'moderate']:
            return 'medium'
        elif s in ['low', 'minor', 'trivial']:
            return 'low'
        else:
            return 'optional'

    def _normalize_confidence(self, confidence: str) -> str:
        c = confidence.lower()
        if c in ['high', 'certain', 'definite']:
            return 'high'
        elif c in ['medium', 'moderate', 'likely']:
            return 'medium'
        else:
            return 'low'

    async def review(self, diff_info, repo_context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Execute the review and return findings. Raises exception on API failure."""
        prompt = self.get_system_prompt()
        diff_text = self.format_diff(diff_info)

        messages = [
            SystemMessage(content=prompt),
            HumanMessage(content=diff_text)
        ]

        if repo_context:
            context_text = "\n\nRepository Context:\n"
            for key, value in repo_context.items():
                context_text += f"\n=== {key} ===\n{str(value)[:3000]}\n"
            messages.append(HumanMessage(content=context_text))

        # Let API errors propagate — don't silently swallow them
        response = await self.llm.ainvoke(messages)

        if response is None or response.content is None:
            logger.warning(f"[{self.name}] Empty LLM response received")
            return []

        logger.info(f"[{self.name}] LLM response length: {len(response.content)} chars")
        preview = response.content[:500].replace('\n', ' ')
        logger.info(f"[{self.name}] Response preview: {preview}...")

        findings = self.parse_findings(response.content)
        logger.info(f"[{self.name}] Parsed {len(findings)} findings")

        for finding in findings:
            finding['agent_name'] = self.name

        return findings
