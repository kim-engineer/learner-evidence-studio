import pytest
from studio import store


@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("STUDIO_PASSWORD", "lesson-demo-2026")
    monkeypatch.setattr(store, "DATA", tmp_path)
    monkeypatch.setattr(store, "DB_PATH", tmp_path / "studio.sqlite3")
    store.initialise()


@pytest.fixture
def source_record():
    with store.db() as connection:
        row = dict(connection.execute("SELECT * FROM evidence WHERE learner_id='L001' AND kind='assessment' AND reliable=1 LIMIT 1").fetchone())
    row.pop("learner_id")
    row["reliable"] = bool(row["reliable"])
    return row
