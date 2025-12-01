import os
from models.justcall_credential import JustCallCredential
import services.sms_service as sms_service


def test_send_sms_uses_db_credentials(app_module, session, monkeypatch):
    session.add(JustCallCredential(api_key="key", api_secret="secret"))
    session.commit()

    called = {}

    class DummyResp:
        def raise_for_status(self):
            pass

    def fake_post(url, json, auth, timeout):
        called["url"] = url
        called["auth"] = auth
        called["json"] = json
        return DummyResp()

    monkeypatch.setattr(sms_service.requests, "post", fake_post)
    assert sms_service.send_sms("123", "hi", from_number="456")
    assert called["url"] == sms_service.JUSTCALL_SMS_URL
    assert called["auth"] == ("key", "secret")
    assert called["json"]["justcall_number"] == "456"
    assert called["json"]["contact_number"] == "123"


def test_send_sms_env_fallback(app_module, session, monkeypatch):
    os.environ["JUSTCALL_API_KEY"] = "ekey"
    os.environ["JUSTCALL_API_SECRET"] = "esecret"

    called = {}

    class DummyResp:
        def raise_for_status(self):
            pass

    def fake_post(url, json, auth, timeout):
        called["url"] = url
        called["auth"] = auth
        called["json"] = json
        return DummyResp()

    monkeypatch.setattr(sms_service.requests, "post", fake_post)
    assert sms_service.send_sms("123", "hi", from_number="789")
    assert called["url"] == sms_service.JUSTCALL_SMS_URL
    assert called["auth"] == ("ekey", "esecret")
    assert called["json"]["justcall_number"] == "789"
    assert called["json"]["contact_number"] == "123"

    del os.environ["JUSTCALL_API_KEY"]
    del os.environ["JUSTCALL_API_SECRET"]


def test_fetch_sms_numbers(app_module, session, monkeypatch):
    session.add(JustCallCredential(api_key="k", api_secret="s"))
    session.commit()

    def fake_get(url, auth, timeout):
        assert url == sms_service.JUSTCALL_NUMBERS_URL
        assert auth == ("k", "s")
        class DummyResp:
            def raise_for_status(self):
                pass
            def json(self):
                return {"numbers": [{"phone_number": "+123"}, {"number": "+456"}]}
        return DummyResp()

    monkeypatch.setattr(sms_service.requests, "get", fake_get)
    numbers = sms_service.fetch_sms_numbers()
    assert numbers == ["+123", "+456"]



def test_fetch_sms_numbers_root_list(app_module, session, monkeypatch):
    session.add(JustCallCredential(api_key="k", api_secret="s"))
    session.commit()

    def fake_get(url, auth, timeout):
        assert url == sms_service.JUSTCALL_NUMBERS_URL
        assert auth == ("k", "s")

        class DummyResp:
            def raise_for_status(self):
                pass

            def json(self):
                return [
                    {"phone_number": "+123"},
                    {"number": "+456"},
                    "+789",
                ]

        return DummyResp()

    monkeypatch.setattr(sms_service.requests, "get", fake_get)
    numbers = sms_service.fetch_sms_numbers()
    assert numbers == ["+123", "+456", "+789"]


def test_fetch_sms_numbers_nested_list(app_module, session, monkeypatch):
    session.add(JustCallCredential(api_key="k", api_secret="s"))
    session.commit()

    def fake_get(url, auth, timeout):
        assert url == sms_service.JUSTCALL_NUMBERS_URL
        assert auth == ("k", "s")

        class DummyResp:
            def raise_for_status(self):
                pass

            def json(self):
                return {"data": ["+111", {"number": "+222"}]}

        return DummyResp()

    monkeypatch.setattr(sms_service.requests, "get", fake_get)
    numbers = sms_service.fetch_sms_numbers()
    assert numbers == ["+111", "+222"]


def test_fetch_sms_numbers_all_keys(app_module, session, monkeypatch):
    session.add(JustCallCredential(api_key="k", api_secret="s"))
    session.commit()

    def fake_get(url, auth, timeout):
        assert url == sms_service.JUSTCALL_NUMBERS_URL
        assert auth == ("k", "s")

        class DummyResp:
            def raise_for_status(self):
                pass

            def json(self):
                return {
                    "numbers": [
                        {"phone_number": "1111111111"},
                        {"number": "+2222222222"},
                        {"justcall_number": "3333333333"},
                        {
                            "friendly_number": "+4444444444",
                            "justcall_number": "4444444444",
                        },
                        {
                            "friendly_number": "5555555555",
                            "justcall_number": "+5555555555",
                        },
                        "6666666666",
                    ]
                }

        return DummyResp()

    monkeypatch.setattr(sms_service.requests, "get", fake_get)
    numbers = sms_service.fetch_sms_numbers()
    assert numbers == [
        "+1111111111",
        "+2222222222",
        "+3333333333",
        "+4444444444",
        "+5555555555",
        "+6666666666",
    ]

def test_default_number_used(app_module, session, monkeypatch):
    session.add(
        JustCallCredential(api_key="key", api_secret="secret", sms_number="999")
    )
    session.commit()

    captured = {}

    class DummyResp:
        def raise_for_status(self):
            pass

    def fake_post(url, json, auth, timeout):
        captured["json"] = json
        return DummyResp()

    monkeypatch.setattr(sms_service.requests, "post", fake_post)
    assert sms_service.send_sms("123", "hi")
    assert captured["json"]["justcall_number"] == "999"

