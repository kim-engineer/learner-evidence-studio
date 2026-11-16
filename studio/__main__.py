import os
from pathlib import Path
from dotenv import load_dotenv
import uvicorn

load_dotenv(Path(__file__).resolve().parents[1]/".env")
if __name__ == "__main__":
    uvicorn.run("studio.web:app",host=os.environ.get("STUDIO_HOST","127.0.0.1"),
                port=int(os.environ.get("STUDIO_PORT","8088")),workers=1)
