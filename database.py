"""
Database configuration and initialization for the Library Management System.
Uses SQLite for persistent storage of Books, Members, and Loan transactions.
"""

import sqlite3
import os

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'library.db')


def get_db_connection(db_path=None):
    """
    Establish and return a connection to the SQLite database.
    Configures row factory to sqlite3.Row for dict-like access.
    Enables foreign key enforcement.
    """
    path = db_path if db_path else DEFAULT_DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path=None):
    """
    Initialize database schema with Books, Members, and Loans tables.
    Safe to call multiple times (IF NOT EXISTS).
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    # Table 1: Books
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        isbn TEXT NOT NULL UNIQUE,
        category TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Available' CHECK(status IN ('Available', 'Issued')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Table 2: Members
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_code TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        phone TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Table 3: Loans (Issue/Return audit tracking)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS loans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        book_id INTEGER NOT NULL,
        member_id INTEGER NOT NULL,
        issue_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        due_date TEXT NOT NULL,
        return_date TIMESTAMP DEFAULT NULL,
        status TEXT NOT NULL DEFAULT 'Active' CHECK(status IN ('Active', 'Returned')),
        FOREIGN KEY (book_id) REFERENCES books (id) ON DELETE CASCADE,
        FOREIGN KEY (member_id) REFERENCES members (id) ON DELETE CASCADE
    );
    """)

    # Create helpful indexes for performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_books_isbn ON books(isbn);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_books_status ON books(status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_members_code ON members(member_code);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_loans_book_id ON loans(book_id);")

    conn.commit()
    conn.close()


if __name__ == '__main__':
    print("Initializing Library Management System database...")
    init_db()
    print("Database initialized successfully at:", DEFAULT_DB_PATH)
