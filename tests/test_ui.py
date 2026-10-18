"""Streamlit UI smoke test (headless AppTest) on both offline synthetic scenarios."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "ui" / "streamlit_app.py")


@pytest.mark.parametrize("mode", ["Synthetic demo: business (offline)", "Synthetic demo: science (offline)"])
def test_ui_runs_synthetic_demo(monkeypatch, tmp_path, mode):
    monkeypatch.setenv("EVIDENCE_NO_DOTENV", "1")
    for k in ("NEBIUS_API_KEY", "TAVILY_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    at.sidebar.radio[0].set_value(mode).run()
    at.button[0].click().run()
    assert not at.exception
    labels = {m.label: m.value for m in at.metric}
    assert labels["Evidence status"] == "LIKELY"  # both scenarios are deterministic
    assert len(at.tabs) == 8
    assert any("SYNTHETIC" in w.value for w in at.warning)
