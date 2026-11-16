"""One-command local bootstrap: Python 3.12 and Node.js 22+ must be installed."""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parent


def main():
    if sys.version_info[:2] != (3, 12):
        raise SystemExit("Use Python 3.12 for the pinned environment, or use Docker Compose.")
    node, npm = shutil.which("node"), shutil.which("npm")
    if not node or not npm:
        raise SystemExit("Install Node.js 22 or newer, including npm, then run this command again.")
    major = int(subprocess.check_output([node,"--version"],text=True).strip().lstrip("v").split(".")[0])
    if major < 22:
        raise SystemExit("Node.js 22 or newer is required.")
    environment = ROOT / ".venv"
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.exists():
        print("Creating the isolated Python environment...",flush=True)
        venv.EnvBuilder(with_pip=True).create(environment)
    requirements = ROOT/"requirements.txt"
    fingerprint = hashlib.sha256(requirements.read_bytes()).hexdigest()
    marker = environment/"studio-requirements.sha256"
    if not marker.exists() or marker.read_text() != fingerprint:
        subprocess.run([str(python),"-m","pip","install","-r",str(requirements)],check=True,cwd=ROOT)
        marker.write_text(fingerprint)
    lockhash = hashlib.sha256((ROOT/"package-lock.json").read_bytes()).hexdigest()
    node_marker = ROOT/"node_modules"/".studio-lock.sha256"
    if not node_marker.exists() or node_marker.read_text() != lockhash:
        subprocess.run([npm,"ci","--omit=dev"],check=True,cwd=ROOT)
        node_marker.write_text(lockhash)
    print("Starting Learner Evidence Studio. Press Ctrl+C to stop.",flush=True)
    try:
        subprocess.run([str(python),"-m","studio"],cwd=ROOT,check=True)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
