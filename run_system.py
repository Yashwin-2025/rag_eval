"""
AETHER-OT + RAG chatbot: Root System Launcher
Bootstraps the SOP knowledge base (pgvector), Modbus TCP server, warehouse simulation, and the
FastAPI dashboard, which also serves the RAG chatbot API.
"""

import app  # noqa: F401  (must be first: blocks the slow optional `transformers` import, see app/__init__.py)
import uvicorn
import logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("aether_ot.launcher")

if __name__ == "__main__":
    # Must run before aether_ot.dashboard.backend.main is imported below (by uvicorn.run),
    # since that module builds LangGraphAIDetective() at import time and reads
    # OPENROUTER_API_KEY from the environment then.
    if load_dotenv():
        logger.info("Loaded environment variables from .env")
    else:
        logger.warning("No .env file found — OPENROUTER_API_KEY and other settings must be set in the environment")

    logger.info("Initializing AETHER-OT Cyber-Physical Digital Twin...")
    # SOP manuals are seeded into pgvector in the background once the server is up
    # (see startup_event in the dashboard backend), so they no longer delay startup.
    logger.info("Starting FastAPI & WebSocket Dashboard on http://localhost:8000 (chatbot UI at /chatbot) ...")
    logger.info("Modbus TCP PLC bridge will listen on 127.0.0.1:5020 ...")

    # Run FastAPI server
    uvicorn.run("aether_ot.dashboard.backend.main:app", host="0.0.0.0", port=8000, log_level="info")
