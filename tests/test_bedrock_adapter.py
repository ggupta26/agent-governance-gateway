import importlib


def load_handler(tmp_path, monkeypatch):
    monkeypatch.setenv("AUDIT_LOG_PATH", str(tmp_path / "audit.jsonl"))
    import governed_agent.adapters.bedrock_lambda as mod

    return importlib.reload(mod)


def event(function, params):
    return {
        "messageVersion": "1.0",
        "actionGroup": "support-actions",
        "function": function,
        "sessionId": "sess-123",
        "agent": {"name": "support-agent"},
        "inputText": "please refund me",
        "parameters": [{"name": k, "type": t, "value": v} for k, (t, v) in params.items()],
        "sessionAttributes": {"tier": "gold"},
        "promptSessionAttributes": {},
    }


def test_allowed_call_returns_tool_output(tmp_path, monkeypatch):
    mod = load_handler(tmp_path, monkeypatch)
    out = mod.lambda_handler(event("issue_refund", {"customer_id": ("string", "C-1001"), "amount": ("number", "25")}))
    fr = out["response"]["functionResponse"]
    assert out["messageVersion"] == "1.0"
    assert out["response"]["actionGroup"] == "support-actions"
    assert "responseState" not in fr
    assert '"amount": 25' in fr["responseBody"]["TEXT"]["body"]
    assert out["sessionAttributes"] == {"tier": "gold"}


def test_denied_call_reprompts_agent(tmp_path, monkeypatch):
    mod = load_handler(tmp_path, monkeypatch)
    out = mod.lambda_handler(event("delete_customer", {"customer_id": ("string", "C-1001")}))
    fr = out["response"]["functionResponse"]
    assert fr["responseState"] == "REPROMPT"
    assert "not permitted" in fr["responseBody"]["TEXT"]["body"]


def test_approval_needed_reports_pending(tmp_path, monkeypatch):
    mod = load_handler(tmp_path, monkeypatch)
    out = mod.lambda_handler(event("issue_refund", {"customer_id": ("string", "C-1002"), "amount": ("number", "300")}))
    assert "pending review" in out["response"]["functionResponse"]["responseBody"]["TEXT"]["body"]


def test_calls_are_audited(tmp_path, monkeypatch):
    mod = load_handler(tmp_path, monkeypatch)
    mod.lambda_handler(event("lookup_customer", {"customer_id": ("string", "C-1001")}))
    records = list(mod._get_gateway().audit.records())
    assert records[-1]["session_id"] == "sess-123" and records[-1]["agent_id"] == "support-agent"
