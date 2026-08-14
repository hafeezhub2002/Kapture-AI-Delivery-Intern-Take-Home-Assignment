import pathlib
import sys
import unittest

from fastapi.testclient import TestClient

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.database.database import DB
from backend.http_api import api


class HttpApiTests(unittest.TestCase):
    def setUp(self) -> None:
        DB.reset()
        self.client = TestClient(api)

    def test_health_endpoint(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_create_verify_and_disclose_flow(self) -> None:
        create_resp = self.client.post("/calls", json={"customer_id": "CUST-1001"})
        self.assertEqual(create_resp.status_code, 200)
        call_id = create_resp.json()["call_id"]

        verify_resp = self.client.post(
            "/verify",
            json={"customer_id": "CUST-1001", "verification_value": "Rahul Sharma", "call_id": call_id},
        )
        self.assertEqual(verify_resp.status_code, 200)
        self.assertTrue(verify_resp.json()["success"])

        details_resp = self.client.get("/accounts/CUST-1001/details", params={"call_id": call_id})
        self.assertEqual(details_resp.status_code, 200)
        self.assertEqual(details_resp.json()["customer_name"], "Rahul Sharma")

    def test_message_flow_records_ptp(self) -> None:
        create_resp = self.client.post("/calls", json={"customer_id": "CUST-1001"})
        call_id = create_resp.json()["call_id"]
        self.client.post(
            "/verify",
            json={"customer_id": "CUST-1001", "verification_value": "Rahul Sharma", "call_id": call_id},
        )
        message_resp = self.client.post("/messages", json={"call_id": call_id, "message": "I'll pay 8499 tomorrow"})
        self.assertEqual(message_resp.status_code, 200)
        self.assertEqual(message_resp.json()["intent"], "WILL_PAY")
        self.assertEqual(message_resp.json()["disposition"], "PROMISE_TO_PAY")

    def test_conversation_webhook_returns_next_turn(self) -> None:
        response = self.client.post(
            "/webhooks/conversation",
            json={
                "customer_id": "CUST-1001",
                "verification_value": "Rahul Sharma",
                "message": "I'll pay tomorrow",
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("call_id", payload)
        self.assertIn("next_turn", payload)
        self.assertIn("messages", payload)
        self.assertIn("tool_calls", payload)
        self.assertEqual(payload["messages"][0]["role"], "assistant")
        self.assertEqual(payload["tool_calls"][0]["name"], "verify_customer")
        self.assertEqual(payload["state"], "PTP_COLLECTED")
        self.assertEqual(payload["disposition"], "PROMISE_TO_PAY")

    def test_no_input_retries_then_closes(self) -> None:
        create_resp = self.client.post("/calls", json={"customer_id": "CUST-1001"})
        call_id = create_resp.json()["call_id"]

        first = self.client.post("/messages", json={"call_id": call_id, "message": ""})
        second = self.client.post("/messages", json={"call_id": call_id, "message": "voicemail"})
        third = self.client.post("/messages", json={"call_id": call_id, "message": ""})

        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["state"], "AUTH_PENDING")
        self.assertEqual(first.json()["no_input_attempts"], 1)

        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json()["state"], "AUTH_PENDING")
        self.assertEqual(second.json()["no_input_attempts"], 2)

        self.assertEqual(third.status_code, 200)
        self.assertEqual(third.json()["state"], "CALL_ENDED")
        self.assertEqual(third.json()["disposition"], "NO_CONTACT")

    def test_agent_handoff_webhook_returns_handoff_payload(self) -> None:
        create_resp = self.client.post("/calls", json={"customer_id": "CUST-1001"})
        call_id = create_resp.json()["call_id"]
        response = self.client.post(
            "/webhooks/agent-handoff",
            json={"customer_id": "CUST-1001", "call_id": call_id, "reason": "Customer asked for a human agent"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["handoff"])
        self.assertEqual(payload["messages"][0]["role"], "assistant")
        tool_names = [tool["name"] for tool in payload["tool_calls"]]
        self.assertIn("escalate_to_agent", tool_names)
        self.assertIn("mark_disposition", tool_names)
        self.assertEqual(payload["reason"], "Customer asked for a human agent")

    def test_metrics_endpoint_reports_snapshot(self) -> None:
        create_resp = self.client.post("/calls", json={"customer_id": "CUST-1001"})
        call_id = create_resp.json()["call_id"]
        self.client.post(
            "/verify",
            json={"customer_id": "CUST-1001", "verification_value": "Rahul Sharma", "call_id": call_id},
        )
        self.client.post("/messages", json={"call_id": call_id, "message": "I'll pay 8499 tomorrow"})
        metrics_resp = self.client.get("/metrics")
        self.assertEqual(metrics_resp.status_code, 200)
        metrics = metrics_resp.json()
        self.assertGreaterEqual(metrics["total_calls"], 1)
        self.assertIn("ptp_rate", metrics)
        self.assertIn("containment_rate", metrics)

    def test_hostile_user_gets_warning_then_escalation(self) -> None:
        create_resp = self.client.post("/calls", json={"customer_id": "CUST-1001"})
        call_id = create_resp.json()["call_id"]
        first = self.client.post("/messages", json={"call_id": call_id, "message": "You are harassing me"})
        second = self.client.post("/messages", json={"call_id": call_id, "message": "This is harassment"})
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["state"], "AUTH_PENDING")
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json()["state"], "ESCALATED")
