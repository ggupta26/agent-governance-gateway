from governed_agent.redaction import redact, redact_text


def test_email_phone_postal():
    out = redact_text("Reach avery@example.com or 604-555-0142, postal V6B 1A1")
    assert "avery@" not in out and "555-0142" not in out and "V6B" not in out
    assert "[REDACTED:EMAIL]" in out and "[REDACTED:PHONE]" in out and "[REDACTED:POSTAL_CODE]" in out


def test_sin_and_card():
    assert "[REDACTED:SIN]" in redact_text("SIN 046 454 286")
    assert "[REDACTED:CARD]" in redact_text("card 4111 1111 1111 1111")


def test_phone_not_mistaken_for_sin():
    assert redact_text("call 604-555-0142") == "call [REDACTED:PHONE]"


def test_nested_and_sensitive_keys():
    out = redact({"user": {"email": "a@b.co", "password": "hunter2"}, "notes": ["x@y.org"], "n": 5})
    assert out == {
        "user": {"email": "[REDACTED:EMAIL]", "password": "[REDACTED]"},
        "notes": ["[REDACTED:EMAIL]"],
        "n": 5,
    }


def test_plain_text_untouched():
    assert redact_text("Refund approved for order 42") == "Refund approved for order 42"
