"""Authenticated command-line import and correction helper for a running studio."""
import argparse
import getpass
import json
from pathlib import Path
import httpx


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8088")
    parser.add_argument("--username", default="demo.teacher")
    commands = parser.add_subparsers(dest="command",required=True)
    commands.add_parser("list")
    for name in ("import", "moodle", "correct"):
        command = commands.add_parser(name)
        command.add_argument("learner_id")
        command.add_argument("file",type=Path)
        if name == "correct":
            command.add_argument("--reason",required=True)
    args = parser.parse_args()
    with httpx.Client(base_url=args.url,timeout=60,follow_redirects=False) as client:
        login = client.post("/api/login",json={"username":args.username,"password":getpass.getpass("Studio password: ")})
        login.raise_for_status()
        client.headers["x-csrf-token"] = login.json()["csrf"]
        if args.command == "list":
            response = client.get("/api/learners")
        else:
            value = json.loads(args.file.read_text(encoding="utf-8"))
            if args.command == "import":
                body={"consent_confirmed":True,"records":value if isinstance(value,list) else value["records"]}
                endpoint="evidence"
            elif args.command == "moodle":
                body={**value,"consent_confirmed":True}
                endpoint="moodle"
            else:
                learner=client.get(f"/api/learners/{args.learner_id}")
                learner.raise_for_status()
                body={"record":value,"consent_confirmed":True,"expected_revision":learner.json()["revision"],"reason":args.reason}
                endpoint="correction"
            print(json.dumps(body,indent=2,ensure_ascii=False))
            if input("Confirm these records are synthetic or you have consent, and apply this action? [yes/no] ").strip().lower() != "yes":
                raise SystemExit("No changes made.")
            response=client.post(f"/api/learners/{args.learner_id}/{endpoint}",json=body)
        if response.status_code >= 400:
            raise SystemExit(f"HTTP {response.status_code}: {response.text}")
        print(json.dumps(response.json(),indent=2,ensure_ascii=False))


if __name__ == "__main__":
    main()
