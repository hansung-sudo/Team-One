from langchain.tools import tool
from pydantic import BaseModel, Field


class SearchInput(BaseModel):
    query: str = Field(description="검색할 내용")


@tool(args_schema=SearchInput)
def web_search(query: str) -> str:
    """DuckDuckGo로 인터넷을 검색해 최신 정보를 가져옵니다."""
    try:
        from ddgs import DDGS
    except ImportError:
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            return "ddgs 패키지가 필요합니다: pip install ddgs"

    try:
        results = DDGS().text(query, max_results=5)
        if not results:
            return "검색 결과가 없습니다."
        lines = []
        for r in results:
            lines.append(f"[{r['title']}]\n{r['body']}\n{r['href']}")
        return "\n\n".join(lines)
    except Exception as e:
        return f"검색 실패: {e}"
