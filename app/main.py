from graph.graph import build_graph
from graph.invoke import invoke_graph

graph = build_graph()


def ask_copilot(question: str) -> str:
    result = invoke_graph(graph, {"question": question, "response_language": "en"})
    return result.get("answer", "(No answer generated)")


if __name__ == "__main__":
    print("🔹 SupplyChain Copilot started (powered by RAG + LangGraph)")
    print("Type your question and press Enter; press Enter with no input to exit.\n")

    while True:
        q = input("You: ").strip()
        if not q:
            print("Exiting.")
            break

        ans = ask_copilot(q)
        print("\nCopilot:")
        print(ans)
        print("-" * 60 + "\n")
