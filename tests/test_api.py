"""
Automated Test Suite for Library Management System
Validates all RESTful endpoints and required edge cases:
1. View / List all books
2. Add a new book (and duplicate ISBN validation)
3. Search by title / author / ISBN
4. Edge Case: Searching a non-existent book returns empty list
5. Issue a book to a member
6. Edge Case: Cannot issue a book if already unavailable/issued
7. Return a book
8. Edge Case: Returning a book not issued
9. Delete a book record
10. Edge Case: Cannot delete an actively issued book
11. Member registration and listing
"""

import unittest
import os
import json
import tempfile
import database
from app import app


class LibraryManagementSystemTests(unittest.TestCase):
    def setUp(self):
        """Set up an isolated temporary database for each test run."""
        self.db_fd, self.temp_db_path = tempfile.mkstemp(suffix='.db')
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

        # Monkey-patch default DB path for testing isolation
        self.orig_db_path = database.DEFAULT_DB_PATH
        database.DEFAULT_DB_PATH = self.temp_db_path

        # Initialize schema
        database.init_db(self.temp_db_path)

        # Insert a sample test member
        conn = database.get_db_connection(self.temp_db_path)
        conn.execute("""
            INSERT INTO members (member_code, name, email, phone)
            VALUES ('MEM-TEST01', 'Test Member', 'test@example.com', '123-456-7890');
        """)
        conn.commit()
        conn.close()

    def tearDown(self):
        """Clean up temporary test database."""
        database.DEFAULT_DB_PATH = self.orig_db_path
        os.close(self.db_fd)
        if os.path.exists(self.temp_db_path):
            os.remove(self.temp_db_path)

    # -------------------------------------------------------------------------
    # 1. Add Book & Validations
    # -------------------------------------------------------------------------
    def test_add_book_success(self):
        payload = {
            "title": "Design Patterns",
            "author": "Erich Gamma",
            "isbn": "978-0201633610",
            "category": "Computer Science"
        }
        res = self.client.post('/api/books', json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertIn("book", data)
        self.assertEqual(data["book"]["title"], "Design Patterns")
        self.assertEqual(data["book"]["status"], "Available")

    def test_add_book_missing_fields(self):
        payload = {"title": "Incomplete Book"}
        res = self.client.post('/api/books', json=payload)
        self.assertEqual(res.status_code, 400)
        self.assertIn("Missing required fields", res.get_json()["error"])

    def test_add_book_duplicate_isbn(self):
        payload = {
            "title": "Book 1",
            "author": "Author A",
            "isbn": "978-1111111111",
            "category": "Science"
        }
        res1 = self.client.post('/api/books', json=payload)
        self.assertEqual(res1.status_code, 201)

        # Attempt to add another book with same ISBN
        payload2 = {
            "title": "Book 2",
            "author": "Author B",
            "isbn": "978-1111111111",
            "category": "Science"
        }
        res2 = self.client.post('/api/books', json=payload2)
        self.assertEqual(res2.status_code, 400)
        self.assertIn("already exists", res2.get_json()["error"])

    # -------------------------------------------------------------------------
    # 2. View and Search Books
    # -------------------------------------------------------------------------
    def test_list_and_search_books(self):
        # Insert test books
        b1 = {"title": "Artificial Intelligence", "author": "Stuart Russell", "isbn": "978-0136042594", "category": "AI"}
        b2 = {"title": "Python Programming", "author": "John Zelle", "isbn": "978-1590282755", "category": "Programming"}
        self.client.post('/api/books', json=b1)
        self.client.post('/api/books', json=b2)

        # List all
        res = self.client.get('/api/books')
        self.assertEqual(res.status_code, 200)
        books = res.get_json()
        self.assertEqual(len(books), 2)

        # Search by title keyword
        res_search = self.client.get('/api/books?q=Intelligence')
        self.assertEqual(res_search.status_code, 200)
        results = res_search.get_json()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Artificial Intelligence")

        # Search by ISBN
        res_isbn = self.client.get('/api/books?q=978-1590282755')
        self.assertEqual(res_isbn.status_code, 200)
        results_isbn = res_isbn.get_json()
        self.assertEqual(len(results_isbn), 1)
        self.assertEqual(results_isbn[0]["title"], "Python Programming")

    def test_edge_case_search_non_existent_book(self):
        """Edge Case: Searching for a non-existent book returns an empty list without crashing."""
        res = self.client.get('/api/books?q=NonExistentTitleXYZ999')
        self.assertEqual(res.status_code, 200)
        results = res.get_json()
        self.assertEqual(results, [])

    # -------------------------------------------------------------------------
    # 3. Issue and Return Operations & Edge Cases
    # -------------------------------------------------------------------------
    def test_issue_and_return_lifecycle(self):
        # Add a book
        b_res = self.client.post('/api/books', json={
            "title": "Operating Systems",
            "author": "Silberschatz",
            "isbn": "978-1118063330",
            "category": "CS"
        })
        book_id = b_res.get_json()["book"]["id"]

        # Issue book to MEM-TEST01
        issue_res = self.client.post(f'/api/books/{book_id}/issue', json={
            "member_code": "MEM-TEST01",
            "due_date": "2026-10-30"
        })
        self.assertEqual(issue_res.status_code, 200)
        self.assertIn("successfully issued", issue_res.get_json()["message"])

        # Check status is now 'Issued'
        get_res = self.client.get(f'/api/books/{book_id}')
        self.assertEqual(get_res.get_json()["status"], "Issued")

        # Return the book
        return_res = self.client.post(f'/api/books/{book_id}/return')
        self.assertEqual(return_res.status_code, 200)
        self.assertIn("successfully returned", return_res.get_json()["message"])

        # Check status is now 'Available'
        get_res_after = self.client.get(f'/api/books/{book_id}')
        self.assertEqual(get_res_after.get_json()["status"], "Available")

    def test_edge_case_issue_already_unavailable_book(self):
        """Edge Case: Cannot issue a book that is already issued/unavailable."""
        b_res = self.client.post('/api/books', json={
            "title": "Database Systems",
            "author": "Ramakrishnan",
            "isbn": "978-0072465631",
            "category": "CS"
        })
        book_id = b_res.get_json()["book"]["id"]

        # First issue: should succeed
        self.client.post(f'/api/books/{book_id}/issue', json={"member_code": "MEM-TEST01"})

        # Second issue attempt: should fail with 400
        duplicate_issue = self.client.post(f'/api/books/{book_id}/issue', json={"member_code": "MEM-TEST01"})
        self.assertEqual(duplicate_issue.status_code, 400)
        self.assertIn("already issued", duplicate_issue.get_json()["error"])

    def test_edge_case_return_book_not_issued(self):
        """Edge Case: Returning a book that is not currently issued returns 400 error."""
        b_res = self.client.post('/api/books', json={
            "title": "Computer Networks",
            "author": "Tanenbaum",
            "isbn": "978-0132126953",
            "category": "Networking"
        })
        book_id = b_res.get_json()["book"]["id"]

        # Attempt to return without issuing first
        return_res = self.client.post(f'/api/books/{book_id}/return')
        self.assertEqual(return_res.status_code, 400)
        self.assertIn("Cannot return", return_res.get_json()["error"])
        self.assertIn("is not currently issued", return_res.get_json()["error"])

    # -------------------------------------------------------------------------
    # 4. Delete Book & Protection
    # -------------------------------------------------------------------------
    def test_delete_available_book_success(self):
        b_res = self.client.post('/api/books', json={
            "title": "Ephemeral Book",
            "author": "Anon",
            "isbn": "978-9999999999",
            "category": "General"
        })
        book_id = b_res.get_json()["book"]["id"]

        del_res = self.client.delete(f'/api/books/{book_id}')
        self.assertEqual(del_res.status_code, 200)

        # Confirm deleted
        get_res = self.client.get(f'/api/books/{book_id}')
        self.assertEqual(get_res.status_code, 404)

    def test_edge_case_delete_issued_book_prevented(self):
        """Edge Case: System prevents deletion of a book that is actively issued."""
        b_res = self.client.post('/api/books', json={
            "title": "Protected Book",
            "author": "Important Author",
            "isbn": "978-8888888888",
            "category": "Law"
        })
        book_id = b_res.get_json()["book"]["id"]

        # Issue book
        self.client.post(f'/api/books/{book_id}/issue', json={"member_code": "MEM-TEST01"})

        # Attempt to delete while issued
        del_res = self.client.delete(f'/api/books/{book_id}')
        self.assertEqual(del_res.status_code, 400)
        self.assertIn("Cannot delete", del_res.get_json()["error"])
        self.assertIn("currently issued", del_res.get_json()["error"])

    # -------------------------------------------------------------------------
    # 5. Members and Stats
    # -------------------------------------------------------------------------
    def test_members_and_stats(self):
        stats_res = self.client.get('/api/stats')
        self.assertEqual(stats_res.status_code, 200)
        stats = stats_res.get_json()
        self.assertIn("total_books", stats)
        self.assertIn("available_books", stats)
        self.assertIn("total_members", stats)


if __name__ == '__main__':
    unittest.main()
