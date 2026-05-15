import unittest
import os
import sys

# Ensure we can import from the root directory
sys.path.append(os.getcwd())

from db_manager import (
    init_db, add_to_watchlist, get_watchlist_data, 
    update_watchlist_rule, delete_from_watchlist,
    save_global_rule, get_global_rule, get_connection
)

class TestDatabaseDEAL(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Ensure DB is initialized"""
        init_db()

    def setUp(self):
        """Clean up watchlist and settings before each test for predictability"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM watchlist")
        cursor.execute("DELETE FROM settings WHERE setting_key = 'global_rule'")
        conn.commit()
        cursor.close()
        conn.close()

    def test_add_and_list_watchlist(self):
        """Test Add and List functionality"""
        test_tickers = ["TDD1", "TDD2", "TDD3"]
        add_to_watchlist(test_tickers)
        
        data = get_watchlist_data()
        tickers_in_db = [item['ticker'] for item in data]
        
        for t in test_tickers:
            self.assertIn(t, tickers_in_db)
        self.assertEqual(len(data), 3)

    def test_edit_local_rule(self):
        """Test Edit functionality (Local Rule)"""
        add_to_watchlist(["EDIT1"])
        new_rule = "Only buy above 200MA"
        update_watchlist_rule("EDIT1", new_rule)
        
        data = get_watchlist_data()
        match = next(item for item in data if item['ticker'] == "EDIT1")
        self.assertEqual(match['local_rule'], new_rule)

    def test_delete_watchlist(self):
        """Test Delete functionality"""
        add_to_watchlist(["DEL1", "DEL2"])
        delete_from_watchlist(["DEL1"])
        
        data = get_watchlist_data()
        tickers_in_db = [item['ticker'] for item in data]
        self.assertNotIn("DEL1", tickers_in_db)
        self.assertIn("DEL2", tickers_in_db)

    def test_global_rule_settings(self):
        """Test Global Rule save and get"""
        test_rule = "# Global Strategy\n1. Check Volume\n2. Check Price"
        save_global_rule(test_rule)
        
        retrieved_rule = get_global_rule()
        self.assertEqual(retrieved_rule, test_rule)

    def test_watchlist_duplicate_ignore(self):
        """Test that adding duplicate tickers doesn't crash or create duplicates"""
        add_to_watchlist(["DUP1"])
        add_to_watchlist(["DUP1", "DUP1"])
        
        data = get_watchlist_data()
        count = sum(1 for item in data if item['ticker'] == "DUP1")
        self.assertEqual(count, 1)

if __name__ == "__main__":
    unittest.main()
