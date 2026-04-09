import re
import xml.etree.ElementTree as ET

import requests
from langchain.tools import tool
from pydantic import BaseModel, Field

_NS = {"atom": "http://www.w3.org/2005/Atom"}


class PaperInput(BaseModel):
    url_or_id: str = Field(
        description="arXiv URL 또는 논문 ID (예: 2303.08774 또는 https://arxiv.org/abs/2303.08774)"
    )


def _extract_arxiv_id(text: str) -> str:
    match = re.search(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})", text)
    if match:
        return match.group(1)
    match = re.match(r"^(\d{4}\.\d{4,5})$", text.strip())
    if match:
        return match.group(1)
    return text.strip()


@tool(args_schema=PaperInput)
def summarize_arxiv_paper(url_or_id: str) -> str:
    """arXiv 논문의 제목·저자·초록을 가져옵니다. 에이전트가 이를 한국어로 요약합니다."""
    paper_id = _extract_arxiv_id(url_or_id)
    try:
        resp = requests.get(
            f"http://export.arxiv.org/api/query?id_list={paper_id}",
            timeout=10,
        )
        resp.raise_for_status()

        root = ET.fromstring(resp.text)
        entry = root.find("atom:entry", _NS)
        if entry is None:
            return f"논문을 찾을 수 없습니다: {paper_id}"

        title = entry.find("atom:title", _NS).text.strip().replace("\n", " ")
        abstract = entry.find("atom:summary", _NS).text.strip().replace("\n", " ")
        authors = [a.find("atom:name", _NS).text for a in entry.findall("atom:author", _NS)]
        published = entry.find("atom:published", _NS).text[:10]

        return (
            f"제목: {title}\n"
            f"저자: {', '.join(authors[:5])}{'...' if len(authors) > 5 else ''}\n"
            f"발표일: {published}\n"
            f"링크: https://arxiv.org/abs/{paper_id}\n\n"
            f"초록:\n{abstract}"
        )
    except Exception as e:
        return f"논문 조회 실패: {e}"
