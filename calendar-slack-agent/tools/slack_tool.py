import os
import sys

from langchain.tools import tool


@tool
def send_slack_message(message: str) -> str:
    """Slack 스터디 채널에 메시지를 전송합니다."""
    try:
        from slack_sdk import WebClient
        from slack_sdk.errors import SlackApiError
    except ImportError:
        return (
            f"slack-sdk 미설치: \"{sys.executable}\" -m pip install slack-sdk"
        )

    token = os.environ.get("SLACK_BOT_TOKEN")
    channel = os.environ.get("SLACK_CHANNEL_ID")
    if not token or not channel:
        return "SLACK_BOT_TOKEN 또는 SLACK_CHANNEL_ID가 설정되어 있지 않습니다."

    try:
        client = WebClient(token=token)
        client.chat_postMessage(channel=channel, text=message)
        return "Slack 전송 완료"
    except SlackApiError as e:
        return f"전송 실패: {e.response['error']}"
