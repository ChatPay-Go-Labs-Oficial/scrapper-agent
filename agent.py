"""
Agente de pesquisa de produtos.
"""

import os
from dotenv import load_dotenv

load_dotenv()

from agno.agent import Agent
from agno.os import AgentOS
from agno.models.openai import OpenAIChat
from agno.models.google import Gemini
from agno.db.sqlite import SqliteDb
from agno.db.postgres import PostgresDb

from tools import buscar_conteudo_completo_site
from config import MODEL_CONFIG, AGENT_INSTRUCTIONS, AGENT_CONFIG

database_url = os.getenv("DATABASE_URL", "sqlite:///tmp/agno_scraper_agent.db")

if database_url.startswith("postgresql://") or database_url.startswith("postgres://"):
    db = PostgresDb(db_url=database_url)
    print(
        f"✅ Usando PostgreSQL: {database_url.split('@')[-1] if '@' in database_url else 'database'}"
    )
else:
    db_file = database_url.replace("sqlite:///", "")
    db = SqliteDb(db_file=db_file)
    print(f"✅ Usando SQLite: {db_file}")


agent = Agent(
    name=AGENT_CONFIG["name"],
    role=AGENT_CONFIG["role"],
    # model=OpenAIChat("gpt-4o-mini"),
    model=Gemini("gemini-2.5-flash"),
    db=db,
    tools=[buscar_conteudo_completo_site],
    add_name_to_context=AGENT_CONFIG["add_name_to_context"],
    instructions=AGENT_INSTRUCTIONS,
    enable_agentic_memory=True,
    enable_user_memories=True,
    add_history_to_context=True,
    markdown=AGENT_CONFIG["markdown"],
)


agent_os = AgentOS(agents=[agent])
app = agent_os.get_app()


if __name__ == "__main__":
    agent_os.serve(app="agent:app", reload=True)

