import pytest

from atlas_ingest import config, http


class FakeResp:
    status_code = 200
    def __init__(self, text): self.text = text


def test_robots_disallow_blocks_and_override_is_explicit(monkeypatch):
    monkeypatch.setattr(http, "_robots", {})
    monkeypatch.setattr(http, "_throttle", lambda host: None)
    monkeypatch.setattr(http._session, "get", lambda url, **kw: FakeResp("User-agent: *\nDisallow: /"))
    assert http.robots_allows("https://api.example.test/dataset/x.csv") is False
    with pytest.raises(http.ManualReviewRequired) as exc:
        http.get("https://api.example.test/dataset/x.csv", source_key="t")
    assert "ATLAS_ROBOTS_OVERRIDE=api.example.test" in str(exc.value) and "--file" in str(exc.value)
    monkeypatch.setattr(config, "ROBOTS_OVERRIDE_HOSTS", {"api.example.test"})
    assert http.robots_allows("https://api.example.test/dataset/x.csv") is True
    assert http.robots_overridden("https://api.example.test/dataset/x.csv") is True  # recorded on the snapshot


def test_path_specific_rules_and_missing_robots(monkeypatch):
    monkeypatch.setattr(http, "_robots", {})
    monkeypatch.setattr(http, "_throttle", lambda host: None)
    monkeypatch.setattr(http._session, "get", lambda url, **kw: FakeResp("User-agent: *\nDisallow: /api/\n"))
    assert http.robots_allows("https://ods.example.test/api/explore/v2.1/x") is False
    assert http.robots_allows("https://ods.example.test/explore/dataset/x") is True
    monkeypatch.setattr(http, "_robots", {"https://nofile.example.test": None})
    assert http.robots_allows("https://nofile.example.test/anything") is True
