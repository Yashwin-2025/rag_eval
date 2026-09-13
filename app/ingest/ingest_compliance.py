import os
import sys
import ssl
import urllib.request
from pathlib import Path

from app.ingest.run import ingest_file

NIST_URL = "https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=936225"
EU_AI_ACT_URL = "https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=OJ:L_202401689"

def download_file(url: str, dest_path: Path) -> bool:
    print(f"Downloading {url} to {dest_path}...")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    req = urllib.request.Request(
        url, 
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"}
    )
    
    try:
        with urllib.request.urlopen(req, context=ctx) as response:
            with open(dest_path, "wb") as out_file:
                out_file.write(response.read())
        print(f"Successfully downloaded to {dest_path}")
        return True
    except Exception as e:
        print(f"Failed to download from {url}: {e}")
        return False

def main() -> None:
    root_dir = Path(__file__).resolve().parent.parent.parent
    data_dir = root_dir / "data"
    data_dir.mkdir(exist_ok=True)
    
    nist_path = data_dir / "nist_ai_rmf.pdf"
    eu_act_path = data_dir / "eu_ai_act.pdf"
    
    # 1. Download PDFs if they don't exist
    if not nist_path.exists():
        if not download_file(NIST_URL, nist_path):
            print("Error: Could not download NIST AI RMF PDF.")
            sys.exit(1)
            
    if not eu_act_path.exists():
        if not download_file(EU_AI_ACT_URL, eu_act_path):
            print("Error: Could not download EU AI Act PDF.")
            sys.exit(1)
            
    # 2. Ingest into the vector database
    user_id = "compliance-officer"
    
    print("\n--- Ingesting NIST AI RMF 1.0 ---")
    try:
        nist_chunks = ingest_file(str(nist_path), doc_id="nist_ai_rmf", user_id=user_id)
        print(f"Successfully ingested NIST AI RMF: stored {nist_chunks} chunks.")
    except Exception as e:
        print(f"Failed to ingest NIST AI RMF: {e}")
        
    print("\n--- Ingesting EU AI Act ---")
    try:
        eu_chunks = ingest_file(str(eu_act_path), doc_id="eu_ai_act", user_id=user_id)
        print(f"Successfully ingested EU AI Act: stored {eu_chunks} chunks.")
    except Exception as e:
        print(f"Failed to ingest EU AI Act: {e}")

if __name__ == "__main__":
    main()
