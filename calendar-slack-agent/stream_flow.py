from agent import agent

for chunk in agent.stream(
    {"messages": [{"role": "user", "content": "다음 주 월요일 오후 2시에 LangGraph 스터디 일정 잡아줘. 2시간짜리야."}]},
    config={"configurable": {"thread_id": "study-session-stream"}},
    stream_mode="updates",
):
    for node, data in chunk.items():
        print(f"\n[{node}]")
        for msg in data.get("messages", []):
            print(f"  {msg.type}: {str(msg.content)[:120]}")
