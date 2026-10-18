"""Streamlit UI smoke test (headless AppTest) on the offline synthetic scenario."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "ui" / "streamlit_app.py")


def test_ui_runs_synthetic_demo(monkeypatch, tmp_path):
    for k in ("NEBIUS_API_KEY", "TAVILY_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.chdir(tmp_path)  # no project .env is picked up
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    assert at.sidebar.radio[0].value.startswith("Synthetic")
    at.button[0].click().run()
    assert not at.exception
    labels = {m.label: m.value for m in at.metric}
    assert labels["Evidence status"] == "LIKELY"  # the synthetic scenario is deterministic
    assert "roots" in labels["Independent sources"]
    assert len(at.tabs) == 6
    assert any("SYNTHETIC" in w.value for w in at.warning)
