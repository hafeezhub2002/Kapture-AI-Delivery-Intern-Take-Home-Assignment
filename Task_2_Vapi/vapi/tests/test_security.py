import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app import create_call, orchestrator
from backend.database.database import DB
from backend.services.account_service import get_account_details


class SecurityTests(unittest.TestCase):
    def setUp(self) -> None:
        DB.reset()

    def test_unverified_overdue_amount_is_not_disclosed(self) -> None:
        call = create_call("CUST-1001")
        response = orchestrator.handle_message(call["call_id"], "How much do I owe?")
        self.assertEqual(response["state"], "AUTH_PENDING")
        self.assertNotIn("8499", response["response"])

    def test_direct_account_lookup_without_verification_is_blocked(self) -> None:
        with self.assertRaises(PermissionError):
            get_account_details("CUST-1001")
