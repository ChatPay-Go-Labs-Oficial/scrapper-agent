"""
Agente de pesquisa de produtos.
"""

from dotenv import load_dotenv
load_dotenv()

from agno.agent import Agent
from agno.os import AgentOS
from agno.models.openai import OpenAIChat
from agno.models.google import Gemini
from agno.db.sqlite import SqliteDb

# NOTA: A ferramenta de scraping foi removida do agente
# A API agora chama a ferramenta diretamente antes de passar ao agente
# Isso previne prompt injection e garante que apenas URLs validadas sejam usadas
from config import MODEL_CONFIG, AGENT_INSTRUCTIONS, AGENT_CONFIG

db = SqliteDb(db_file="tmp/agno_scraper_agent.db")


agent = Agent(
    name=AGENT_CONFIG["name"],
    role=AGENT_CONFIG["role"],
    # model=OpenAIChat("gpt-4o-mini"),
    model=Gemini("gemini-2.5-flash"),
    db=db,
    tools=[],  # Sem ferramentas - o conteúdo já vem pré-extraído da API
    add_name_to_context=AGENT_CONFIG["add_name_to_context"],
    instructions=AGENT_INSTRUCTIONS,
    enable_agentic_memory=True,
    enable_user_memories=True,
    add_history_to_context=True,
    markdown=AGENT_CONFIG["markdown"]
)


agent_os = AgentOS(agents=[agent])
app = agent_os.get_app()
    

if __name__ == "__main__":
    agent_os.serve(app="agent:app", reload=True)
    
