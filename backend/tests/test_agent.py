import json
from typing import List

import pytest

import agent as fraud_module


def _seed_cases(path, cases: List[dict]) -> None:
    path.write_text(json.dumps(cases), encoding="utf-8")


@pytest.fixture
def sample_cases(tmp_path, monkeypatch):
    data_path = tmp_path / "fraud_cases.json"
    monkeypatch.setattr(fraud_module, "FRAUD_CASES_PATH", data_path)
    cases = [
        {
            "caseId": "CASE-001",
            "userName": "John",
            "securityIdentifier": "12345",
            "securityQuestion": "What is your favorite color?",
            "securityAnswer": "blue",
            "cardMask": "**** 4242",
            "transactionAmount": 150.25,
            "currency": "USD",
            "transactionName": "Acme Gadgets",
            "transactionCategory": "e-commerce",
            "transactionSource": "acme.example",
            "location": "New York, USA",
            "transactionTime": "2025-11-20T02:15:00Z",
            "channel": "online",
            "status": "pending_review",
            "outcomeNote": "",
            "createdAt": "2025-11-20T02:20:00Z",
            "updatedAt": "2025-11-20T02:20:00Z",
        }
    ]
    _seed_cases(data_path, cases)
    return data_path, cases


@pytest.mark.asyncio
async def test_loads_fraud_case(sample_cases):
    data_path, _ = sample_cases
    agent = fraud_module.FraudAlertAgent()

    result = await agent.load_fraud_case(context=None, user_name="John")

    assert result["status"] == "loaded"
    assert result["case"]["transactionName"] == "Acme Gadgets"
    assert agent.active_case is not None
    assert data_path.exists()


@pytest.mark.asyncio
async def test_verifies_security_answer(sample_cases):
    agent = fraud_module.FraudAlertAgent()
    await agent.load_fraud_case(context=None, user_name="John")

    good = await agent.verify_security_answer(context=None, answer="Blue ")
    bad = await agent.verify_security_answer(context=None, answer="green")

    assert good["verified"] is True
    assert bad["verified"] is False
    assert bad["attempts_left"] == fraud_module.MAX_VERIFICATION_ATTEMPTS - 2


@pytest.mark.asyncio
async def test_updates_case_status(sample_cases):
    data_path, _ = sample_cases
    agent = fraud_module.FraudAlertAgent()
    await agent.load_fraud_case(context=None, user_name="John")

    await agent.update_case_status(
        context=None,
        status="confirmed_fraud",
        note="Customer denied transaction and card was frozen.",
    )

    persisted = json.loads(data_path.read_text(encoding="utf-8"))
    assert persisted[0]["status"] == "confirmed_fraud"
    assert (
        persisted[0]["outcomeNote"]
        == "Customer denied transaction and card was frozen."
    )
