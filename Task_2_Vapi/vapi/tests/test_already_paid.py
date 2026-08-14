import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app import create_call, orchestrator
from backend.database.database import DB


class AlreadyPaidTests(unittest.TestCase):
    def setUp(self) -> None:
        DB.reset()

    def test_already_paid_flow(self) -> None:
        call = create_call("CUST-1001")
        orchestrator.verify(call["call_id"], "Rahul Sharma")
        response = orchestrator.handle_message(call["call_id"], "I already paid")
        self.assertEqual(response["disposition"], "ALREADY_PAID")
        self.assertTrue(DB.get_account("CUST-1001").is_paid)

