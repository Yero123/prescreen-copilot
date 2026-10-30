"""Every test run uses a throwaway database and no demo seed."""

import os
import tempfile

os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(prefix="prescreen-test-"), "test.db")
os.environ["SEED_DEMO"] = "0"
