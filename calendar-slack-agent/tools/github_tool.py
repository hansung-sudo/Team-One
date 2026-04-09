import base64
import os
import re

import requests
from langchain.tools import tool
from pydantic import BaseModel, Field

_README_MAX = 2000


class RepoInput(BaseModel):
    url_or_path: str = Field(
        description="GitHub 저장소 URL 또는 owner/repo "
        "(예: https://github.com/langchain-ai/langchain 또는 langchain-ai/langchain)"
    )


def _extract_repo_path(text: str) -> str:
    match = re.search(r"github\.com/([^/\s]+/[^/\s#?]+)", text)
    if match:
        return re.sub(r"\.git$", "", match.group(1).rstrip("/"))
    return text.strip()


def _github_headers() -> dict:
    headers = {"Accept": "application/vnd.github.v3+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


@tool(args_schema=RepoInput)
def summarize_github_repo(url_or_path: str) -> str:
    """GitHub 저장소의 정보와 README를 가져옵니다. 에이전트가 이를 한국어로 요약합니다."""
    repo_path = _extract_repo_path(url_or_path)
    headers = _github_headers()
    base = f"https://api.github.com/repos/{repo_path}"

    try:
        repo = requests.get(base, headers=headers, timeout=10)
        repo.raise_for_status()
        r = repo.json()

        lines = [
            f"저장소: {r['full_name']}",
            f"설명: {r.get('description') or '(없음)'}",
            f"언어: {r.get('language') or '(없음)'}",
            f"Stars: {r['stargazers_count']:,}  Forks: {r['forks_count']:,}  Issues: {r['open_issues_count']:,}",
            f"최근 업데이트: {r['updated_at'][:10]}",
            f"URL: {r['html_url']}",
        ]
        if r.get("topics"):
            lines.append(f"토픽: {', '.join(r['topics'])}")

        readme_resp = requests.get(f"{base}/readme", headers=headers, timeout=10)
        if readme_resp.status_code == 200:
            content = base64.b64decode(readme_resp.json()["content"]).decode("utf-8", errors="replace")
            preview = content[:_README_MAX].strip()
            if len(content) > _README_MAX:
                preview += "\n... (이하 생략)"
            lines.append(f"\nREADME:\n{preview}")
        else:
            lines.append("\nREADME: 없음")

        return "\n".join(lines)

    except requests.HTTPError as e:
        code = e.response.status_code if e.response is not None else "?"
        if code == 404:
            return f"저장소를 찾을 수 없습니다: {repo_path}"
        if code == 403:
            return "GitHub API 요청 한도 초과. .env에 GITHUB_TOKEN을 추가하면 한도가 늘어납니다."
        return f"GitHub API 오류 ({code}): {e}"
    except Exception as e:
        return f"저장소 조회 실패: {e}"
