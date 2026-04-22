import os
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_tavily import TavilySearch
from langgraph.checkpoint.memory import MemorySaver

load_dotenv()

memory = MemorySaver()

# 1. Configuración de herramientas
tavily_tool = TavilySearch(max_results=2)
from huawei_tools import run_koocli_command

# Eliminamos temporalmente la herramienta Tavily para forzar al agente a depender exclusivamente de la consola local y comandos `--help`.
tools = [run_koocli_command]

# 2. Configuración para Huawei Cloud MaaS
# Usamos "openai" como provider porque MaaS es compatible con su API
llm = init_chat_model(
    model="deepseek-v3.2", 
    model_provider="openai", 
    openai_api_base="https://api-ap-southeast-1.modelarts-maas.com/openai/v1",
    openai_api_key=os.getenv("MAAS_API_KEY") # Asegúrate de que en tu .env se llame así
)

llm_with_tools = llm.bind_tools(tools)

graph_config = {
    "configurable": {"thread_id": "1"}
}