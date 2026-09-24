from app.handlers import subscription


def test_is_owner_true_for_matching_id(monkeypatch):
    monkeypatch.setattr(subscription, "OWNER_CHAT_ID", "12345")
    assert subscription._is_owner(12345) is True


def test_is_owner_false_for_other_id(monkeypatch):
    monkeypatch.setattr(subscription, "OWNER_CHAT_ID", "12345")
    assert subscription._is_owner(999) is False


def test_is_owner_false_when_not_configured(monkeypatch):
    monkeypatch.setattr(subscription, "OWNER_CHAT_ID", "")
    assert subscription._is_owner(12345) is False
