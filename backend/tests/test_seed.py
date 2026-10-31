"""The demo seed must keep loading: it is what the UI opens with, in Docker and in production."""

import json

import pytest
from fastapi.testclient import TestClient

import app.main as main
from app import store, views
from app.roles import load_role
from app.seed import SEED_FILE, load_seed


@pytest.fixture
def empty_db(monkeypatch, tmp_path):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "seed.db"))


def test_every_seed_item_renders(empty_db):
    expected = len(json.loads(SEED_FILE.read_text(encoding="utf-8")))
    assert load_seed() == expected > 0
    subs = store.list_latest_submissions()
    assert len(subs) == expected
    for sub in subs:
        assert views.row(sub, load_role(sub["role_id"]))["status"] == "done"


def test_startup_seeds_an_empty_database_once(empty_db, monkeypatch):
    monkeypatch.setenv("SEED_DEMO", "1")
    with TestClient(main.app) as c:
        first = len(c.get("/api/submissions").json())
    with TestClient(main.app) as c:
        assert len(c.get("/api/submissions").json()) == first > 0
