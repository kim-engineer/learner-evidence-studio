"""Change the local teacher account with current-password verification."""
import getpass
import secrets
from dotenv import load_dotenv
load_dotenv()
from studio.store import initialise, db, password_hash, audit


def main():
    initialise()
    current = getpass.getpass("Current teacher password: ")
    with db() as c:
        row = c.execute("SELECT * FROM teachers WHERE id='demo.teacher'").fetchone()
    if not secrets.compare_digest(password_hash(current,row["salt"]),row["password_hash"]):
        raise SystemExit("Current password is incorrect. No changes made.")
    name = input(f"Teacher display name [{row['name']}]: ").strip() or row["name"]
    new = getpass.getpass("New password (at least 12 characters): ")
    repeated = getpass.getpass("Repeat new password: ")
    if not 12 <= len(new) <= 200 or new != repeated or len(name)>100:
        raise SystemExit("Check the display-name length and matching password length. No changes made.")
    salt = secrets.token_hex(16)
    with db(True) as c:
        fresh = c.execute("SELECT password_hash FROM teachers WHERE id='demo.teacher'").fetchone()
        if fresh[0] != row["password_hash"]:
            raise SystemExit("The account changed during this operation. Retry.")
        c.execute("UPDATE teachers SET name=?,salt=?,password_hash=? WHERE id='demo.teacher'",(name,salt,password_hash(new,salt)))
        c.execute("DELETE FROM sessions WHERE teacher_id='demo.teacher'")
        audit(c,"demo.teacher","human_update_account",{}, {"display_name":name,"sessions_revoked":True})
    print("Account updated. Sign in again as demo.teacher with the new password.")


if __name__ == "__main__":
    main()
