from graph import build_graph
from config import graph_config

def stream_graph_updates(user_input: str):
    graph = build_graph()
    for event in graph.stream(
        {"messages": [{"role":"user","content":user_input}]},
        config=graph_config,
        stream_mode="values"
    ):
        event["messages"][-1].pretty_print()
        
def run_chat_loop():
    while True:
        try:
            user_input = input("User: ")
            if user_input.lower() in ["quit","exit","q"]:
                print("Goodbye!")
                break
            stream_graph_updates(user_input)
        except:
            stream_graph_updates(user_input="Tell goodbye!")
            break