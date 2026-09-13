"""
AETHER-OT: Root System Launcher
Bootstraps Qdrant embedded index, Modbus TCP server, warehouse simulation, and FastAPI dashboard.
"""

import uvicorn
import logging
from aether_ot.agent.qdrant_indexer import get_qdrant_indexer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("aether_ot.launcher")

if __name__ == "__main__":
    logger.info("Initializing AETHER-OT Cyber-Physical Digital Twin...")
    # 1. Ensure Qdrant embedded collections and manuals exist
    indexer = get_qdrant_indexer("./qdrant_data")
    logger.info(f"Qdrant vector collection '{indexer.collection_name}' ready.")

    logger.info("Starting FastAPI & WebSocket Dashboard on http://localhost:8000 ...")
    logger.info("Modbus TCP PLC bridge will listen on 127.0.0.1:5020 ...")
    
    # 2. Run FastAPI server
    uvicorn.run("aether_ot.dashboard.backend.main:app", host="0.0.0.0", port=8000, log_level="info")
