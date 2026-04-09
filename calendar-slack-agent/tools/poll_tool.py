import os

from langchain.tools import tool
from pydantic import BaseModel, Field

_NUMBER_EMOJIS = ["one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
_NUMBER_CHARS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]


class PollInput(BaseModel):
    question: str = Field(description="투표 질문")
    options: list[str] = Field(description="투표 선택지 목록 (최대 9개)")


@tool(args_schema=PollInput)
def create_slack_poll(question: str, options: list[str]) -> str:
    """Slack 채널에 이모지 반응 투표를 생성합니다."""
    if not options:
        return "선택지를 하나 이상 입력해주세요."

    options = options[:9]

    try:
        from slack_sdk import WebClient
        from slack_sdk.errors import SlackApiError
    except ImportError:
        return "slack-sdk 미설치"

    token = os.environ.get("SLACK_BOT_TOKEN")
    channel = os.environ.get("SLACK_CHANNEL_ID")
    if not token or not channel:
        return "Slack 환경변수 미설정"

    lines = [f"📊 *{question}*", ""]
    for i, opt in enumerate(options):
        lines.append(f"{_NUMBER_CHARS[i]}  {opt}")
    lines += ["", "위 이모지를 눌러 투표해주세요!"]

    client = WebClient(token=token)
    try:
        result = client.chat_postMessage(channel=channel, text="\n".join(lines))
        ts = result["ts"]

        for i in range(len(options)):
            try:
                client.reactions_add(channel=channel, name=_NUMBER_EMOJIS[i], timestamp=ts)
            except SlackApiError:
                # reactions:write 스코프 없어도 투표 메시지 자체는 전송됨
                pass

        return f"투표 생성 완료: '{question}' ({len(options)}개 선택지)"
    except SlackApiError as e:
        err = e.response.get("error", str(e)) if e.response else str(e)
        return f"투표 생성 실패: {err}"
