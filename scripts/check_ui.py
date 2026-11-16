"""Launch the API and test the JavaScript interface against it using jsdom."""
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

root = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix="learner-ui-test-") as temporary:
    env = dict(os.environ, STUDIO_DATA_DIR=temporary, STUDIO_PASSWORD="lesson-demo-2026")
    process = subprocess.Popen([sys.executable,"-m","uvicorn","studio.web:app","--host","127.0.0.1","--port","8088"],cwd=root,env=env)
    try:
        for _ in range(100):
            try:
                urllib.request.urlopen("http://127.0.0.1:8088/health",timeout=1).close()
                break
            except OSError:
                if process.poll() is not None:
                    raise RuntimeError("Test server did not start")
                time.sleep(.1)
        result = subprocess.run(["node","tests/ui-smoke.cjs"],cwd=root,env=env,check=True,capture_output=True,text=True,timeout=240)
        print(result.stdout)
        (root/"evaluation"/"ui-results.json").write_text(result.stdout,encoding="utf-8")
    finally:
        process.terminate()
        process.wait(timeout=15)
