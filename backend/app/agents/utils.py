import os
import re
from typing import List, Dict, Optional, Any
from langchain_core.tools import tool
from app.services.git_service import GitService

@tool
def read_file(file_path: str, max_lines: int = 100) -> str:
    """Read a file from the repository. Provide the full file path."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            if len(lines) > max_lines:
                return ''.join(lines[:max_lines//2]) + '\n... [truncated] ...\n' + ''.join(lines[-max_lines//2:])
            return ''.join(lines)
    except Exception as e:
        return f"Error reading file: {str(e)}"

@tool
def search_code(repo_path: str, pattern: str, file_extension: Optional[str] = None) -> str:
    """Search for a pattern in the repository code."""
    matches = []
    for root, dirs, files in os.walk(repo_path):
        # Skip common non-source directories
        dirs[:] = [d for d in dirs if d not in ['node_modules', '.git', '__pycache__', 'venv', '.venv', 'dist', 'build']]

        for file in files:
            if file_extension and not file.endswith(file_extension):
                continue

            file_path = os.path.join(root, file)
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    if re.search(pattern, content, re.IGNORECASE):
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            if re.search(pattern, line, re.IGNORECASE):
                                rel_path = os.path.relpath(file_path, repo_path)
                                matches.append(f"{rel_path}:{i+1}: {line.strip()}")
                                if len(matches) >= 20:
                                    break
                        if len(matches) >= 20:
                            break
            except:
                continue
        if len(matches) >= 20:
            break

    if not matches:
        return "No matches found."
    return "\n".join(matches[:20])

@tool
def get_directory_structure(repo_path: str, max_depth: int = 3) -> str:
    """Get the directory structure of the repository."""
    structure = []

    for root, dirs, files in os.walk(repo_path):
        depth = root.replace(repo_path, '').count(os.sep)
        if depth > max_depth:
            del dirs[:]
            continue

        dirs[:] = [d for d in dirs if d not in ['node_modules', '.git', '__pycache__', 'venv', '.venv', 'dist', 'build', '.idea', '.vscode']]

        indent = '  ' * depth
        rel_path = os.path.relpath(root, repo_path)
        if rel_path == '.':
            rel_path = os.path.basename(repo_path) or 'root'
        structure.append(f"{indent}{os.path.basename(root)}/")

        subindent = '  ' * (depth + 1)
        for file in sorted(files)[:10]:  # Limit files per dir
            structure.append(f"{subindent}{file}")
        if len(files) > 10:
            structure.append(f"{subindent}... and {len(files) - 10} more files")

    return "\n".join(structure)

@tool
def analyze_dependencies(repo_path: str) -> str:
    """Analyze project dependencies from package files."""
    results = []

    # Python
    req_file = os.path.join(repo_path, 'requirements.txt')
    if os.path.exists(req_file):
        with open(req_file, 'r') as f:
            results.append("Python requirements.txt:")
            results.append(f.read()[:2000])

    pyproject = os.path.join(repo_path, 'pyproject.toml')
    if os.path.exists(pyproject):
        with open(pyproject, 'r') as f:
            results.append("\npyproject.toml:")
            results.append(f.read()[:2000])

    # Node.js
    package_json = os.path.join(repo_path, 'package.json')
    if os.path.exists(package_json):
        with open(package_json, 'r') as f:
            results.append("\npackage.json:")
            results.append(f.read()[:2000])

    if not results:
        return "No dependency files found."
    return "\n".join(results)

def get_file_language(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    lang_map = {
        '.py': 'python', '.js': 'javascript', '.ts': 'typescript', '.jsx': 'jsx', '.tsx': 'tsx',
        '.java': 'java', '.go': 'go', '.rs': 'rust', '.cpp': 'cpp', '.c': 'c', '.h': 'c',
        '.cs': 'csharp', '.rb': 'ruby', '.php': 'php', '.swift': 'swift', '.kt': 'kotlin',
        '.scala': 'scala', '.r': 'r', '.m': 'objc', '.sql': 'sql', '.sh': 'bash',
        '.yml': 'yaml', '.yaml': 'yaml', '.json': 'json', '.xml': 'xml', '.md': 'markdown'
    }
    return lang_map.get(ext, 'unknown')

def truncate_diff(diff: str, max_chars: int = 15000) -> str:
    if len(diff) <= max_chars:
        return diff
    return diff[:max_chars//2] + "\n\n... [diff truncated for brevity] ...\n\n" + diff[-max_chars//2:]
