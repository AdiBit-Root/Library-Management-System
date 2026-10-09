"""
Seed script to populate initial sample records for Books, Members, and Loans.
Ensures the application displays realistic data out-of-the-box for evaluation.
"""

from database import get_db_connection, init_db
from datetime import datetime, timedelta


def seed_database(db_path=None):
    # Ensure tables exist first
    init_db(db_path)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    # Clear existing data for clean seed
    cursor.execute("DELETE FROM loans;")
    cursor.execute("DELETE FROM books;")
    cursor.execute("DELETE FROM members;")

    sample_members = [
        ("MEM-101", "Alice Johnson", "alice.johnson@university.edu", "555-0101"),
        ("MEM-102", "Bob Smith", "bob.smith@university.edu", "555-0102"),
        ("MEM-103", "Charlie Patel", "charlie.patel@university.edu", "555-0103"),
        ("MEM-104", "Diana Prince", "diana.prince@university.edu", "555-0104"),
    ]

    for member in sample_members:
        cursor.execute(
            "INSERT INTO members (member_code, name, email, phone) VALUES (?, ?, ?, ?)",
            member
        )

    sample_books = [
        ("The Pragmatic Programmer", "David Thomas, Andrew Hunt", "978-0201616224", "Computer Science", "Available"),
        ("Clean Code: Agile Craftsmanship", "Robert C. Martin", "978-0132350884", "Computer Science", "Issued"),
        ("Introduction to Algorithms", "Thomas H. Cormen", "978-0262033848", "Computer Science", "Available"),
        ("To Kill a Mockingbird", "Harper Lee", "978-0061120084", "Fiction", "Available"),
        ("1984", "George Orwell", "978-0451524935", "Fiction", "Available"),
        ("A Brief History of Time", "Stephen Hawking", "978-0553380163", "Science", "Available"),
        ("Sapiens: A Brief History of Humankind", "Yuval Noah Harari", "978-0062316097", "History", "Available"),
        ("Meditations", "Marcus Aurelius", "978-0140449334", "Philosophy", "Available"),
    ]

    for book in sample_books:
        cursor.execute(
            "INSERT INTO books (title, author, isbn, category, status) VALUES (?, ?, ?, ?, ?)",
            book
        )

    # Fetch IDs to create an initial active loan
    cursor.execute("SELECT id FROM books WHERE isbn = '978-0132350884'")
    clean_code_id = cursor.fetchone()["id"]

    cursor.execute("SELECT id FROM members WHERE member_code = 'MEM-101'")
    alice_id = cursor.fetchone()["id"]

    due_date = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")
    cursor.execute(
        """
        INSERT INTO loans (book_id, member_id, due_date, status)
        VALUES (?, ?, ?, 'Active')
        """,
        (clean_code_id, alice_id, due_date)
    )

    conn.commit()
    conn.close()
    print("Database successfully seeded with sample books, members, and an active loan transaction!")


if __name__ == '__main__':
    seed_database()
