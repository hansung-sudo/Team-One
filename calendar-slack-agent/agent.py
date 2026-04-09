from dotenv import load_dotenv

load_dotenv(override=True)

from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain.agents import create_agent

try:
    from langchain.memory import InMemorySaver
except ImportError:
    from langgraph.checkpoint.memory import InMemorySaver

from tools.calendar_tool import create_calendar_event
from tools.github_tool import summarize_github_repo
from tools.image_tool import generate_and_send_image
from tools.paper_tool import summarize_arxiv_paper
from tools.poll_tool import create_slack_poll
from tools.search_tool import web_search
from tools.slack_tool import send_slack_message
from tools.weather_tool import get_weather

model = ChatOpenAI(model="gpt-4.1")
checkpointer = InMemorySaver()
today = datetime.now().strftime("%Y-%m-%d (%A)")

agent = create_agent(
    model=model,
    tools=[
        create_calendar_event,
        send_slack_message,
        get_weather,
        web_search,
        generate_and_send_image,
        create_slack_poll,
        summarize_arxiv_paper,
        summarize_github_repo,
    ],
    checkpointer=checkpointer,
    system_prompt=f"""오늘 날짜는 {today}입니다. 사용자와 자연스럽게 대화한다.

일반적인 질문과 잡담은 도구 없이 답한다.

[날씨] 날씨를 물어보면 get_weather로 조회한다. 도시명이 없으면 짧게 물어본다. 도시명은 반드시 영문으로 변환해서 넘긴다 (예: 서울→Seoul, 부산→Busan, 도쿄→Tokyo).

[웹 검색] 최신 정보나 모르는 사실이 필요하면 web_search로 찾은 뒤 결과를 요약해서 답한다.

[이미지] 이미지를 만들어달라고 하면 generate_and_send_image를 쓴다. 프롬프트는 영문으로 변환해서 넘긴다. 생성 완료 후 Slack 채널에 전송됐다고 알려준다.

[일정] 캘린더에 추가하려 하면 create_calendar_event를 쓴다. 제목·시작·종료 시각이 모호하면 짧게 물어보고, 상대적 표현은 오늘 날짜 기준 ISO 시각으로 바꾼다.

[공지] Slack으로 알리고 싶을 때만 send_slack_message를 쓴다. 공지 문구는 상황에 맞게 짓되, 캘린더 링크가 있으면 함께 넣는다.

[투표] 투표나 설문을 만들어달라고 하면 create_slack_poll을 쓴다. 질문과 선택지가 불명확하면 먼저 물어본다.

[논문] arXiv URL이나 논문 ID가 주어지면 summarize_arxiv_paper로 메타데이터를 가져온 뒤 아래 형식으로 한국어 요약을 작성한다.
형식:
*[논문 제목 (영문 그대로)]*
저자: 이름1, 이름2, ... | 발표: YYYY-MM-DD
링크: https://arxiv.org/abs/{{id}}

*핵심 요약*
• 연구 목적/문제 정의 (1~2문장)
• 제안 방법/아이디어 (1~2문장)
• 주요 결과/기여 (1~2문장)
초록을 그대로 붙여넣지 말고, 반드시 위 항목별로 핵심만 추출해 한국어로 작성한다.

[GitHub] GitHub URL이나 owner/repo가 주어지면 summarize_github_repo로 정보를 가져온 뒤 아래 형식으로 한국어 요약을 작성한다. 공개 저장소는 API 키 없이도 조회할 수 있다.
형식:
*[저장소 이름]* — 한 줄 설명 (한국어)
링크: {{html_url}}
언어: {{language}} | Stars: {{stars}} | Forks: {{forks}}

*주요 내용*
• 프로젝트 목적 (1~2문장)
• 핵심 기능 또는 특징 (2~3개 bullet)
• 사용 기술 스택 (있으면)
README를 그대로 붙여넣지 말고, 반드시 위 항목별로 핵심만 추출해 한국어로 작성한다.

불필요한 도구는 쓰지 않는다.
""",
)

config = {"configurable": {"thread_id": "study-session"}}


def chat(user_text: str, thread_id: str) -> str:
    result = agent.invoke(
        {"messages": [{"role": "user", "content": user_text}]},
        config={"configurable": {"thread_id": thread_id}},
    )
    return result["messages"][-1].content


if __name__ == "__main__":
    user_input = input("요청을 입력하세요: ")
    print(chat(user_input, "study-session"))
