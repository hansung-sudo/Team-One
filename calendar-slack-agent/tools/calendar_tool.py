from pathlib import Path

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from langchain.tools import tool
from pydantic import BaseModel, Field

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

_ROOT = Path(__file__).resolve().parent.parent
_TOKEN_PATH = _ROOT / "token.json"

_calendar_service = None


def _credentials_path() -> Path:
    direct = _ROOT / "credentials.json"
    if direct.is_file():
        return direct
    matches = sorted(_ROOT.glob("client_secret*.json"))
    if matches:
        return matches[0]
    raise FileNotFoundError(
        "Google OAuth 클라이언트 JSON이 없습니다. "
        f"'{_ROOT}' 에 credentials.json 을 두거나, "
        "콘솔에서 받은 client_secret....json 파일을 이 폴더에 넣은 뒤 다시 실행하세요."
    )


def get_calendar_service():
    creds = None
    cred_file = _credentials_path()
    if _TOKEN_PATH.is_file():
        try:
            creds = Credentials.from_authorized_user_file(str(_TOKEN_PATH), SCOPES)
        except Exception:
            creds = None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except RefreshError:
                creds = None
        else:
            creds = None
        if creds is None:
            if _TOKEN_PATH.is_file():
                _TOKEN_PATH.unlink(missing_ok=True)
            flow = InstalledAppFlow.from_client_secrets_file(str(cred_file), SCOPES)
            creds = flow.run_local_server(port=0)
        with open(_TOKEN_PATH, "w", encoding="utf-8") as f:
            f.write(creds.to_json())
    return build("calendar", "v3", credentials=creds)


def _get_calendar_service_lazy():
    global _calendar_service
    if _calendar_service is None:
        _calendar_service = get_calendar_service()
    return _calendar_service


class CreateEventInput(BaseModel):
    """일정 생성 파라미터"""

    title: str = Field(description="일정 제목")
    start_datetime: str = Field(description="시작 시간 (ISO 형식: 2025-01-20T14:00:00)")
    end_datetime: str = Field(description="종료 시간 (ISO 형식: 2025-01-20T15:00:00)")
    description: str = Field(default="", description="일정 설명 (선택)")


@tool(args_schema=CreateEventInput)
def create_calendar_event(
    title: str,
    start_datetime: str,
    end_datetime: str,
    description: str = "",
) -> str:
    """Google Calendar에 새 일정을 생성합니다."""
    cal = _get_calendar_service_lazy()
    event = {
        "summary": title,
        "description": description,
        "start": {"dateTime": start_datetime, "timeZone": "Asia/Seoul"},
        "end": {"dateTime": end_datetime, "timeZone": "Asia/Seoul"},
    }
    created = cal.events().insert(calendarId="primary", body=event).execute()
    link = created.get("htmlLink", "")
    return f"일정 생성 완료: {created['summary']} ({start_datetime}) | 링크: {link}"
