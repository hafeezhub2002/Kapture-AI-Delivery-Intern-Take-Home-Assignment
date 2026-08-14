import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app import create_call, orchestrator
from backend.database.database import DB


class DoNotCallTests(unittest.TestCase):
    def setUp(self) -> None:
        DB.reset()

    def test_dnc_flow(self) -> None:
        call = create_call("CUST-1001")
        orchestrator.verify(call["call_id"], "Rahul Sharma")
        response = orchestrator.handle_message(call["call_id"], "Do not call me again")
        self.assertEqual(response["disposition"], "DO_NOT_CALL")
        self.assertTrue(DB.get_account("CUST-1001").is_dnc)

