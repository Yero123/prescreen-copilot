"""Every test run uses a throwaway database and no demo seed."""

import os
import tempfile

os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(prefix="prescreen-test-"), "test.db")
os.environ["SEED_DEMO"] = "0"

import pytest

from app import security


@pytest.fixture(autouse=True)
def fresh_screen_budget():
    """The limits live in memory, so one test's requests must not count against the next."""
    security._by_ip.clear()
    security._all.clear()
