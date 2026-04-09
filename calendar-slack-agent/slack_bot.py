"""
Slack 봇 — Socket Mode.

이벤트:
  - 멘션(@봇): 자유 대화 (에이전트)
  - DM: 자유 대화 (에이전트)

슬래시 커맨드 (Slack 앱 설정에서 등록 필요):
  /날씨   [도시]          현재 날씨 조회
  /검색   <검색어>        DuckDuckGo 웹 검색
  /논문   <arXiv ID/URL>  논문 요약
  /레포   <owner/repo>    GitHub 저장소 요약
  /이미지 <설명>          DALL-E 3 이미지 생성·전송
  /투표   <질문> | <A> | <B> ...  이모지 투표 생성
  /일정   <자연어>        Google Calendar 일정 등록
  /공지   <내용>          채널 공지 전송

.env:
  SLACK_BOT_TOKEN=xoxb-...
  SLACK_APP_TOKEN=xapp-1-...   (Basic Information → App-Level Tokens, connections:write)

Slack 앱 OAuth 스코프:
  chat:write, app_mentions:read, im:history, reactions:write, files:write

실행:
  python slack_bot.py
"""

from __future__ import annotations

import os
import re

from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

load_dotenv(override=True)

from agent import chat
from tools.poll_tool import create_slack_poll
from tools.slack_tool import send_slack_message

_SLACK_MSG_MAX = 3500
_MENTION_RE = re.compile(r"<@[^>]+>\s*")


def _key(event: dict) -> str:
    team = event.get("team") or event.get("source_team") or "default"
    ch = event.get("channel") or "unknown"
    uid = event.get("user") or "unknown"
    return f"slack-{team}-{ch}-{uid}"


def _clip(text: str) -> str:
    text = text.strip()
    return text if len(text) <= _SLACK_MSG_MAX else text[: _SLACK_MSG_MAX - 3] + "..."


def _arg(command: dict) -> str:
    return (command.get("text") or "").strip()


def main() -> None:
    app = App(token=os.environ["SLACK_BOT_TOKEN"])

    # ── 이벤트 핸들러 ──────────────────────────────────────────────

    @app.event("app_mention")
    def on_mention(event, say):
        text = _MENTION_RE.sub("", event.get("text") or "", count=1).strip()
        if not text:
            say("무엇을 도와드릴까요?")
            return
        try:
            say(_clip(chat(text, _key(event))))
        except Exception as e:
            say(f"오류: {e}")

    @app.event("message")
    def on_dm(event, say):
        if event.get("bot_id") or event.get("subtype"):
            return
        if not (event.get("channel") or "").startswith("D"):
            return
        text = (event.get("text") or "").strip()
        if not text or not event.get("user"):
            return
        try:
            say(_clip(chat(text, _key(event))))
        except Exception as e:
            say(f"오류: {e}")

    # ── 슬래시 커맨드 ──────────────────────────────────────────────

    @app.command("/날씨")
    def cmd_weather(ack, command, say):
        ack()
        city = _arg(command) or "Seoul"
        try:
            say(_clip(chat(f"{city} 날씨 알려줘", _key(command))))
        except Exception as e:
            say(f"오류: {e}")

    @app.command("/검색")
    def cmd_search(ack, command, say):
        ack()
        query = _arg(command)
        if not query:
            say("사용법: `/검색 <검색어>`")
            return
        try:
            say(_clip(chat(f"검색해줘: {query}", _key(command))))
        except Exception as e:
            say(f"오류: {e}")

    @app.command("/논문")
    def cmd_paper(ack, command, say):
        ack()
        arg = _arg(command)
        if not arg:
            say("사용법: `/논문 <arXiv ID 또는 URL>`\n예) `/논문 2303.08774`")
            return
        try:
            say(_clip(chat(f"이 논문 요약해줘: {arg}", _key(command))))
        except Exception as e:
            say(f"오류: {e}")

    @app.command("/레포")
    def cmd_repo(ack, command, say):
        ack()
        arg = _arg(command)
        if not arg:
            say("사용법: `/레포 <owner/repo 또는 GitHub URL>`\n예) `/레포 langchain-ai/langchain`")
            return
        try:
            say(_clip(chat(f"이 GitHub 저장소 설명해줘: {arg}", _key(command))))
        except Exception as e:
            say(f"오류: {e}")

    @app.command("/이미지")
    def cmd_image(ack, command, say):
        ack()
        prompt = _arg(command)
        if not prompt:
            say("사용법: `/이미지 <이미지 설명>`\n예) `/이미지 cyberpunk cityscape at night`")
            return
        try:
            say(_clip(chat(f"이미지 만들어줘: {prompt}", _key(command))))
        except Exception as e:
            say(f"오류: {e}")

    @app.command("/투표")
    def cmd_poll(ack, command, say):
        """형식: /투표 질문 | 선택지1 | 선택지2 | ..."""
        ack()
        arg = _arg(command)
        if not arg:
            say("사용법: `/투표 질문 | 선택지1 | 선택지2 | ...`\n예) `/투표 스터디 주제 | Transformer | RAG | LoRA`")
            return
        parts = [p.strip() for p in arg.split("|")]
        if len(parts) < 2:
            say("선택지를 `|`로 구분해 입력해주세요.\n예) `/투표 스터디 주제 | Transformer | RAG | LoRA`")
            return
        question, options = parts[0], parts[1:]
        say(_clip(create_slack_poll.invoke({"question": question, "options": options})))

    @app.command("/일정")
    def cmd_calendar(ack, command, say):
        """자연어를 에이전트가 해석해 일정을 등록합니다."""
        ack()
        text = _arg(command)
        if not text:
            say("사용법: `/일정 <내용>`\n예) `/일정 다음 주 월요일 오후 2시 스터디 2시간`")
            return
        try:
            say(_clip(chat(f"캘린더에 추가해줘: {text}", _key(command))))
        except Exception as e:
            say(f"오류: {e}")

    @app.command("/공지")
    def cmd_notice(ack, command, say):
        ack()
        text = _arg(command)
        if not text:
            say("사용법: `/공지 <공지 내용>`")
            return
        say(_clip(send_slack_message.invoke({"message": text})))

    # ── 실행 ───────────────────────────────────────────────────────

    app_token = os.environ.get("SLACK_APP_TOKEN")
    if not app_token:
        raise ValueError(
            "SLACK_APP_TOKEN 이 필요합니다. "
            "App-Level Token(Socket Mode, connections:write)을 .env 에 넣으세요."
        )

    print("Slack Socket Mode 연결 중… (Ctrl+C 로 종료)")
    SocketModeHandler(app, app_token).start()


if __name__ == "__main__":
    main()
