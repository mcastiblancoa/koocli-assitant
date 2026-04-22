from langgraph.graph import StateGraph, START
from langgraph.prebuilt import ToolNode, tools_condition
from config import tools, memory, llm_with_tools
from state import State
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

def build_graph() -> StateGraph:
    graph_builder = StateGraph(State)
    
    # Prompt del sistema para darle instrucciones precisas sobre cómo manejar las APIs de Huawei
    system_prompt = """Eres un asistente experto en DevSecOps y Cloud Computing especializado en Huawei Cloud.
Tu objetivo es ayudar al usuario a administrar recursos usando EXCLUSIVAMENTE KooCLI (hcloud) de Huawei Cloud mediante la herramienta 'run_koocli_command'.

REGLA DE ORO: Tu única herramienta disponible es 'run_koocli_command'. NO PUEDES BUSCAR EN LA WEB. Si no conoces el formato o los argumentos de un comando, DEBES ejecutar 'run_koocli_command' con el flag 'help' (ej. {{"help": ""}} o string vacío, dependiendo de cómo responda el comando) para leer el manual interno de KooCLI desde la terminal y así debugear la llamada. Confía en tu conocimiento interno o en la salida de comandos help para estructurar los payload.

Instrucciones:
1. Usa la herramienta 'run_koocli_command' especificando el servicio (ej. 'vpc') y la operación correcta (ej. 'CreateVpc'). 
2. Para CREAR recursos en KooCLI (operaciones POST/PUT), asegúrate de que el dict se estructure exactamente como lo dictamina la terminal interna de Huawei (usualmente mediante dict anidado como: params = {{"vpc": {{"name": "tu_nombre"}}}} o pasando solo 'name').
3. Si la consola responde "[USE_ERROR]... Run `hcloud VPC CreateVpc --help` for details", DEBES obedecer inmediatamente invocando run_koocli_command lanzando params = {{"help": "true"}}. La lectura de ese help stdout te dará los secretos de la firma.
4. NO incluyes autenticación.
5. Explica siempre qué comando estás tratando de invocar, procesa la respuesta devuelta por KooCLI y preséntalo amigablemente.
"""

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="messages"),
    ])
    
    def chatbot(state: State):
        # Inyecta el prompt del sistema antes de pasarlo al modelo
        chain = prompt | llm_with_tools
        message = chain.invoke({"messages": state["messages"]})
        return {"messages":[message]}
    
    graph_builder.add_node("chatbot", chatbot)
    
    tool_node = ToolNode(tools)
    graph_builder.add_node("tools", tool_node)
    
    graph_builder.add_conditional_edges("chatbot", tools_condition)
    
    graph_builder.add_edge("tools", "chatbot")
    graph_builder.add_edge(START, "chatbot")
    
    return graph_builder.compile(checkpointer=memory)