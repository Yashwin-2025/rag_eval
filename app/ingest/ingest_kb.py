import os
import sys
from pathlib import Path

from app.ingest.run import ingest_file

def main() -> None:
    # Ensure correct paths
    root_dir = Path(__file__).resolve().parent.parent.parent
    file_path = root_dir / "data" / "ai_safety_handbook.md"
    doc_id = "ai_safety_handbook"
    user_id = "eval-user"

    if not file_path.exists():
        print(f"Error: {file_path} does not exist!")
        sys.exit(1)

    print(f"Ingesting {file_path} as doc_id='{doc_id}' for user_id='{user_id}'...")
    try:
        chunks = ingest_file(str(file_path), doc_id=doc_id, user_id=user_id)
        print(f"Successfully ingested handbook: stored {chunks} chunks.")
    except Exception as e:
        print(f"Ingestion failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
