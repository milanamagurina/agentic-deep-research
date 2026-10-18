import pytest

from deep_research.config import DEFAULT_BASE_URL, DEFAULT_MODEL, ConfigError, Settings


def test_defaults_and_role_fallback():
    s = Settings.from_env({"NEBIUS_API_KEY": "k1", "TAVILY_API_KEY": "k2"})
    assert s.nebius_base_url == DEFAULT_BASE_URL
    assert s.lead_model == s.worker_model == s.checker_model == DEFAULT_MODEL


def test_per_role_models():
    s = Settings.from_env({
        "NEBIUS_API_KEY": "k1", "TAVILY_API_KEY": "k2",
        "NEBIUS_MODEL": "lead/m", "NEBIUS_CHECKER_MODEL": "checker/m",
    })
    assert (s.lead_model, s.worker_model, s.checker_model) == ("lead/m", "lead/m", "checker/m")


def test_missing_keys_named_without_values():
    with pytest.raises(ConfigError) as e:
        Settings.from_env({"NEBIUS_API_KEY": "secret-value"})
    assert "TAVILY_API_KEY" in str(e.value)
    assert "secret-value" not in str(e.value)


def test_secrets_hidden_from_repr():
    s = Settings.from_env({"NEBIUS_API_KEY": "secret-nebius", "TAVILY_API_KEY": "secret-tavily"})
    assert "secret-nebius" not in repr(s) and "secret-tavily" not in repr(s)


def test_real_tools_are_configured_as_specified(env):
    from deep_research.agents import build_tools

    tools = build_tools()  # constructs clients only; no network call
    assert tools.search.name == "tavily_search"
    assert tools.search.max_results == 5
    assert tools.search.search_depth == "advanced"
    assert tools.extract.name == "tavily_extract"
