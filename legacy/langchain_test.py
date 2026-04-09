import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI


def main() -> None:
    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY가 설정되어 있지 않습니다. .env 파일을 확인하세요.")

    llm = ChatOpenAI(
        model="gpt-5.4-mini",
        temperature=0,
    )

    user_input = "랭체인의 핵심 개념을 10줄로 요약해줘."
    print(f"[입력]\n{user_input}\n")

    response = llm.invoke(user_input)
    print(f"response: {response}")
    print(f"[출력]\n{response.content}")


if __name__ == "__main__":
    main()
