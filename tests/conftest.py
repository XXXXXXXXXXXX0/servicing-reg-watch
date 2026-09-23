import socket
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "eval"))


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Offline guarantee: any socket connection attempt fails the test."""
    def refuse(*args, **kwargs):
        raise RuntimeError("network access attempted during offline test")
    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


@pytest.fixture
def offline_run(tmp_path):
    from pipeline import run
    data, rec = tmp_path / "data", tmp_path / "records"
    rc = run.main(["--offline", "--data-dir", str(data), "--records-dir", str(rec), "--with-fixture-triage"])
    return {"rc": rc, "data": data, "records": rec}
