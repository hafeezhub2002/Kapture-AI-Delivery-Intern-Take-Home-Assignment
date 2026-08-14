import unittest

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app import create_call
from backend.database.database import DB
from backend.services.account_service import get_account_details
from backend.services.authentication import verify_customer


class AuthenticationTests(unittest.TestCase):
    def setUp(self) -> None:
        DB.reset()

    def test_requires_authentication_before_disclosure(self) -> None:
        with self.assertRaises(PermissionError):
            get_account_details("CUST-1001")

    def test_successful_authentication_unlocks_disclosure(self) -> None:
        call = create_call("CUST-1001")
        result = verify_customer("CUST-1001", "Rahul Sharma", call_session=DB.get_session(call["call_id"]))
        self.assertTrue(result["success"])
        details = get_account_details("CUST-1001", call_id=call["call_id"])
        self.assertEqual(details["customer_name"], "Rahul Sharma")
        self.assertIn("overdue_amount", details)

    def test_failed_authentication_does_not_unlock_disclosure(self) -> None:
        result = verify_customer("CUST-1001", "not rahul")
        self.assertFalse(result["success"])
        with self.assertRaises(PermissionError):
            get_account_details("CUST-1001")
