import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app import create_call, orchestrator
from backend.database.database import DB


class PromiseToPayTests(unittest.TestCase):
    def setUp(self) -> None:
        DB.reset()

    def test_successful_ptp_flow(self) -> None:
        call = create_call("CUST-1001")
        orchestrator.verify(call["call_id"], "Rahul Sharma")
        response = orchestrator.handle_message(call["call_id"], "I'll pay 8499 tomorrow")
        self.assertEqual(response["disposition"], "PROMISE_TO_PAY")
        self.assertEqual(response["intent"], "WILL_PAY")

        account = DB.get_account("CUST-1001")
        self.assertEqual(len(account.ptp_history), 1)
        self.assertEqual(account.ptp_history[0]["amount"], 8499.0)
        self.assertEqual(account.ptp_history[0]["ptp_date"], "tomorrow")

