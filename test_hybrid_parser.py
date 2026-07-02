import unittest
import os
from parsers.hybrid_parser import validate_pdf, extract_and_preview_tables, parse_hybrid_transactions

class TestHybridParser(unittest.TestCase):
    def setUp(self):
        self.test_pdf = "sbi_statement.pdf"
        
    def test_pdf_validation(self):
        if not os.path.exists(self.test_pdf):
            self.skipTest(f"{self.test_pdf} does not exist for testing")
        is_valid, msg = validate_pdf(self.test_pdf)
        self.assertTrue(is_valid)
        self.assertEqual(msg, "PDF validation succeeded.")
        
    def test_table_extraction_and_inference(self):
        if not os.path.exists(self.test_pdf):
            self.skipTest(f"{self.test_pdf} does not exist for testing")
        res = extract_and_preview_tables(self.test_pdf)
        self.assertTrue(res["success"])
        self.assertIn("headers", res)
        self.assertIn("preview_rows", res)
        self.assertIn("auto_mapping", res)
        
        # Verify inferred mappings exist (Date, Narration, etc.)
        mapping = res["auto_mapping"]
        self.assertNotEqual(mapping["date"], -1)
        self.assertNotEqual(mapping["narration"], -1)
        
    def test_transaction_parsing(self):
        if not os.path.exists(self.test_pdf):
            self.skipTest(f"{self.test_pdf} does not exist for testing")
        
        # First extract table to get auto mapping
        res = extract_and_preview_tables(self.test_pdf)
        self.assertTrue(res["success"])
        mapping = res["auto_mapping"]
        
        transactions = parse_hybrid_transactions(self.test_pdf, mapping)
        self.assertTrue(len(transactions) > 0)
        
        # Verify transaction structure
        first_txn = transactions[0]
        self.assertIn("gl_date", first_txn)
        self.assertIn("narration", first_txn)
        self.assertIn("amount", first_txn)
        self.assertIn("type", first_txn)
        self.assertIn("balance", first_txn)
        
        # Date should be standard DD-MM-YYYY format
        self.assertRegex(first_txn["gl_date"], r"^\d{2}-\d{2}-\d{4}$")
        self.assertTrue(isinstance(first_txn["amount"], float))
        self.assertTrue(isinstance(first_txn["balance"], float))
        self.assertIn(first_txn["type"], ["DEBIT", "CREDIT"])

if __name__ == "__main__":
    unittest.main()
