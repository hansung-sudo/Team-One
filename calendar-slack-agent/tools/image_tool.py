import os

import requests
from langchain.tools import tool
from openai import OpenAI
from pydantic import BaseModel, Field

_MASCOT_KEYWORDS = ("상상부기", "sangsangbugi", "한성대 마스코트", "한성대학교 마스코트")
_MASCOT_REF_URL = (
    "https://raw.githubusercontent.com/kimstitute/Medical_AI/refs/heads/main/sangsang2.png"
)
_mascot_description_cache: str | None = None


def _get_mascot_description(client: OpenAI) -> str:
    global _mascot_description_cache
    if _mascot_description_cache:
        return _mascot_description_cache

    try:
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": _MASCOT_REF_URL},
                        },
                        {
                            "type": "text",
                            "text": (
                                "Describe this mascot character's visual appearance "
                                "in precise detail for a DALL-E image generation prompt. "
                                "Include overall shape, body structure, colors (exact shades), "
                                "facial features, style (flat vector / cartoon / etc.), "
                                "and any notable design elements. "
                                "Output only the description, no commentary."
                            ),
                        },
                    ],
                }
            ],
            max_tokens=300,
        )
        _mascot_description_cache = resp.choices[0].message.content.strip()
    except Exception as e:
        _mascot_description_cache = "a cute round turtle mascot with a navy blue shell and a friendly face"
        print(f"[image_tool] 마스코트 묘사 생성 실패, 기본값 사용: {e}")

    return _mascot_description_cache


class GenerateImageInput(BaseModel):
    prompt: str = Field(description="생성할 이미지의 설명 (영문 권장, 예: a futuristic city at sunset)")


@tool(args_schema=GenerateImageInput)
def generate_and_send_image(prompt: str) -> str:
    """DALL-E 3로 이미지를 생성하고 Slack 채널에 전송합니다."""
    client = OpenAI()

    if any(kw in prompt.lower() for kw in _MASCOT_KEYWORDS):
        mascot_desc = _get_mascot_description(client)
        prompt = (
            f"{prompt}. "
            f"The character must match this exact design: {mascot_desc} "
            f"Keep the same visual style and color palette as the reference character."
        )

    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
    except Exception as e:
        return f"이미지 생성 실패: {e}"

    image_url = response.data[0].url
    revised_prompt = response.data[0].revised_prompt or prompt

    try:
        img_bytes = requests.get(image_url, timeout=30).content
    except Exception as e:
        return f"이미지 다운로드 실패: {e} | URL: {image_url}"

    token = os.environ.get("SLACK_BOT_TOKEN")
    channel = os.environ.get("SLACK_CHANNEL_ID")
    if not token or not channel:
        return f"Slack 환경변수 미설정. 이미지 URL: {image_url}"

    try:
        from slack_sdk import WebClient
        from slack_sdk.errors import SlackApiError
    except ImportError:
        return f"slack-sdk 미설치. 이미지 URL: {image_url}"

    try:
        WebClient(token=token).files_upload_v2(
            channel=channel,
            content=img_bytes,
            filename="generated.png",
            title=prompt[:80],
            initial_comment=f"프롬프트: {revised_prompt}",
        )
        return f"이미지 생성 및 Slack 전송 완료 (프롬프트: {revised_prompt})"
    except SlackApiError as e:
        err = e.response.get("error", str(e)) if e.response else str(e)
        return f"Slack 전송 실패: {err} | 이미지 URL: {image_url}"
    except Exception as e:
        return f"Slack 전송 실패: {e} | 이미지 URL: {image_url}"
