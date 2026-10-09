"""
Library Management System - Flask RESTful Backend Application
Provides full-stack REST API endpoints for books, members, and loan operations.
Integrated with SQLite persistent database and serves client-side interface.
"""

from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from database import get_db_connection, init_db
from datetime import datetime, timedelta
import os
import sqlite3

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

# Ensure database tables exist upon server start
init_db()


# ==========================================
# Frontend Routes
# ==========================================

@app.route('/')
def index():
    """Serves the main single-page application dashboard."""
    return render_template('index.html')


# ==========================================
# Statistics & Overview Endpoint
# ==========================================

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Returns library summary statistics for dashboard metrics cards."""
    conn = get_db_connection()
    cursor = conn.cursor()

    total_books = cursor.execute("SELECT COUNT(*) FROM books;").fetchone()[0]
    available_books = cursor.execute("SELECT COUNT(*) FROM books WHERE status = 'Available';").fetchone()[0]
    issued_books = cursor.execute("SELECT COUNT(*) FROM books WHERE status = 'Issued';").fetchone()[0]
    total_members = cursor.execute("SELECT COUNT(*) FROM members;").fetchone()[0]
    active_loans = cursor.execute("SELECT COUNT(*) FROM loans WHERE status = 'Active';").fetchone()[0]

    conn.close()
    return jsonify({
        "total_books": total_books,
        "available_books": available_books,
        "issued_books": issued_books,
        "total_members": total_members,
        "active_loans": active_loans
    }), 200


# ==========================================
# Book Categories Endpoint
# ==========================================

@app.route('/api/categories', methods=['GET'])
def get_categories():
    """Returns distinct list of book categories."""
    conn = get_db_connection()
    rows = conn.execute("SELECT DISTINCT category FROM books ORDER BY category ASC;").fetchall()
    conn.close()
    categories = [r['category'] for r in rows if r['category']]
    return jsonify(categories), 200


# ==========================================
# Books CRUD & Search Endpoints
# ==========================================

@app.route('/api/books', methods=['GET'])
def list_books():
    """
    List books with optional search query and filters.
    Query parameters:
    - q: search substring in title, author, or isbn
    - category: exact category filter
    - status: 'Available' or 'Issued' filter
    """
    query = request.args.get('q', '').strip()
    category = request.args.get('category', '').strip()
    status = request.args.get('status', '').strip()

    sql = """
        SELECT b.id, b.title, b.author, b.isbn, b.category, b.status, b.created_at,
               l.due_date, m.name AS borrower_name, m.member_code AS borrower_code
        FROM books b
        LEFT JOIN loans l ON b.id = l.book_id AND l.status = 'Active'
        LEFT JOIN members m ON l.member_id = m.id
        WHERE 1=1
    """
    params = []

    if query:
        sql += " AND (b.title LIKE ? OR b.author LIKE ? OR b.isbn LIKE ?)"
        wildcard = f"%{query}%"
        params.extend([wildcard, wildcard, wildcard])

    if category and category.lower() != 'all':
        sql += " AND b.category = ?"
        params.append(category)

    if status and status.lower() != 'all':
        sql += " AND b.status = ?"
        params.append(status)

    sql += " ORDER BY b.id DESC;"

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    conn.close()

    books = [dict(row) for row in rows]
    return jsonify(books), 200


@app.route('/api/books/<int:book_id>', methods=['GET'])
def get_book(book_id):
    """Retrieve details for a single book by ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT b.id, b.title, b.author, b.isbn, b.category, b.status, b.created_at,
               l.due_date, l.issue_date, m.name AS borrower_name, m.member_code AS borrower_code, m.email AS borrower_email
        FROM books b
        LEFT JOIN loans l ON b.id = l.book_id AND l.status = 'Active'
        LEFT JOIN members m ON l.member_id = m.id
        WHERE b.id = ?;
    """, (book_id,))
    book = cursor.fetchone()
    conn.close()

    if not book:
        return jsonify({"error": f"Book with ID {book_id} not found."}), 404

    return jsonify(dict(book)), 200


@app.route('/api/books', methods=['POST'])
def add_book():
    """
    Add a new book record.
    Payload: { title, author, isbn, category }
    Validations:
    - Required fields check
    - ISBN uniqueness check
    """
    data = request.get_json(silent=True) or {}
    title = (data.get('title') or '').strip()
    author = (data.get('author') or '').strip()
    isbn = (data.get('isbn') or '').strip()
    category = (data.get('category') or '').strip()

    # Validation: Missing required fields
    if not title or not author or not isbn or not category:
        missing = []
        if not title: missing.append('Title')
        if not author: missing.append('Author')
        if not isbn: missing.append('ISBN')
        if not category: missing.append('Category')
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}."}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    # Validation: Duplicate ISBN check
    cursor.execute("SELECT id FROM books WHERE isbn = ?;", (isbn,))
    if cursor.fetchone():
        conn.close()
        return jsonify({"error": f"A book with ISBN '{isbn}' already exists."}), 400

    try:
        cursor.execute("""
            INSERT INTO books (title, author, isbn, category, status)
            VALUES (?, ?, ?, ?, 'Available');
        """, (title, author, isbn, category))
        conn.commit()
        book_id = cursor.lastrowid
        cursor.execute("SELECT * FROM books WHERE id = ?;", (book_id,))
        created_book = cursor.fetchone()
        conn.close()
        return jsonify({
            "message": "Book added successfully.",
            "book": dict(created_book)
        }), 201
    except sqlite3.Error as e:
        conn.close()
        return jsonify({"error": f"Database error: {str(e)}"}), 500


@app.route('/api/books/<int:book_id>', methods=['PUT'])
def update_book(book_id):
    """
    Update book details (title, author, isbn, category).
    Validates book existence and ISBN uniqueness.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM books WHERE id = ?;", (book_id,))
    book = cursor.fetchone()
    if not book:
        conn.close()
        return jsonify({"error": f"Book with ID {book_id} not found."}), 404

    data = request.get_json(silent=True) or {}
    title = (data.get('title') or book['title']).strip()
    author = (data.get('author') or book['author']).strip()
    isbn = (data.get('isbn') or book['isbn']).strip()
    category = (data.get('category') or book['category']).strip()

    if not title or not author or not isbn or not category:
        conn.close()
        return jsonify({"error": "Fields title, author, isbn, and category cannot be empty."}), 400

    # Ensure updated ISBN does not collide with another book
    cursor.execute("SELECT id FROM books WHERE isbn = ? AND id != ?;", (isbn, book_id))
    if cursor.fetchone():
        conn.close()
        return jsonify({"error": f"A different book with ISBN '{isbn}' already exists."}), 400

    cursor.execute("""
        UPDATE books
        SET title = ?, author = ?, isbn = ?, category = ?
        WHERE id = ?;
    """, (title, author, isbn, category, book_id))
    conn.commit()

    cursor.execute("SELECT * FROM books WHERE id = ?;", (book_id,))
    updated_book = cursor.fetchone()
    conn.close()

    return jsonify({
        "message": "Book updated successfully.",
        "book": dict(updated_book)
    }), 200


@app.route('/api/books/<int:book_id>', methods=['DELETE'])
def delete_book(book_id):
    """
    Delete a book record.
    Validation:
    - Book must exist (404)
    - If book is currently 'Issued', prevent deletion with descriptive error (400)
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM books WHERE id = ?;", (book_id,))
    book = cursor.fetchone()
    if not book:
        conn.close()
        return jsonify({"error": f"Book with ID {book_id} not found."}), 404

    # Edge Case: Prevent deleting a book currently checked out
    if book['status'] == 'Issued':
        conn.close()
        return jsonify({
            "error": f"Cannot delete '{book['title']}' while it is currently issued to a member. Please return the book first."
        }), 400

    cursor.execute("DELETE FROM books WHERE id = ?;", (book_id,))
    conn.commit()
    conn.close()

    return jsonify({"message": f"Book '{book['title']}' was deleted successfully."}), 200


# ==========================================
# Issue & Return Endpoints
# ==========================================

@app.route('/api/books/<int:book_id>/issue', methods=['POST'])
def issue_book(book_id):
    """
    Issue a book to a member.
    Payload: { member_id (or member_code), due_date (optional, defaults to +14 days) }
    Edge case validations:
    - Book must exist (404)
    - Book must be Available (400 if already Issued)
    - Member must exist (404/400)
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM books WHERE id = ?;", (book_id,))
    book = cursor.fetchone()
    if not book:
        conn.close()
        return jsonify({"error": f"Book with ID {book_id} not found."}), 404

    # Edge case: Cannot issue if already unavailable
    if book['status'] == 'Issued':
        cursor.execute("""
            SELECT m.name, m.member_code, l.due_date
            FROM loans l
            JOIN members m ON l.member_id = m.id
            WHERE l.book_id = ? AND l.status = 'Active';
        """, (book_id,))
        active_loan = cursor.fetchone()
        conn.close()
        borrower = active_loan['name'] if active_loan else "another member"
        return jsonify({
            "error": f"Cannot issue '{book['title']}': Book is already issued to {borrower}."
        }), 400

    data = request.get_json(silent=True) or {}
    member_id = data.get('member_id')
    member_code = data.get('member_code')

    # Look up member by either ID or member_code
    member = None
    if member_id:
        cursor.execute("SELECT * FROM members WHERE id = ?;", (member_id,))
        member = cursor.fetchone()
    elif member_code:
        cursor.execute("SELECT * FROM members WHERE member_code = ?;", (member_code.strip(),))
        member = cursor.fetchone()

    if not member:
        conn.close()
        return jsonify({"error": "Valid Member ID or Member Code is required to issue a book."}), 400

    due_date = data.get('due_date')
    if not due_date:
        due_date = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")

    # Perform transaction: update book status and create loan
    cursor.execute("UPDATE books SET status = 'Issued' WHERE id = ?;", (book_id,))
    cursor.execute("""
        INSERT INTO loans (book_id, member_id, due_date, status)
        VALUES (?, ?, ?, 'Active');
    """, (book_id, member['id'], due_date))
    loan_id = cursor.lastrowid
    conn.commit()

    cursor.execute("""
        SELECT l.*, b.title, m.name AS member_name, m.member_code
        FROM loans l
        JOIN books b ON l.book_id = b.id
        JOIN members m ON l.member_id = m.id
        WHERE l.id = ?;
    """, (loan_id,))
    loan_record = cursor.fetchone()
    conn.close()

    return jsonify({
        "message": f"Book '{book['title']}' successfully issued to {member['name']} (Due: {due_date}).",
        "loan": dict(loan_record)
    }), 200


@app.route('/api/books/<int:book_id>/return', methods=['POST'])
def return_book(book_id):
    """
    Return an issued book.
    Edge case validations:
    - Book must exist (404)
    - Book must actually be Issued (400 if already Available)
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM books WHERE id = ?;", (book_id,))
    book = cursor.fetchone()
    if not book:
        conn.close()
        return jsonify({"error": f"Book with ID {book_id} not found."}), 404

    # Edge case: Returning a book not issued
    if book['status'] != 'Issued':
        conn.close()
        return jsonify({
            "error": f"Cannot return '{book['title']}': Book is already marked as 'Available' and is not currently issued."
        }), 400

    # Update active loan record
    cursor.execute("""
        UPDATE loans
        SET status = 'Returned', return_date = CURRENT_TIMESTAMP
        WHERE book_id = ? AND status = 'Active';
    """, (book_id,))

    # Update book status to Available
    cursor.execute("UPDATE books SET status = 'Available' WHERE id = ?;", (book_id,))
    conn.commit()
    conn.close()

    return jsonify({
        "message": f"Book '{book['title']}' has been successfully returned and is now Available."
    }), 200


# ==========================================
# Members Endpoints
# ==========================================

@app.route('/api/members', methods=['GET'])
def list_members():
    """List all registered library members with their active issued book count."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT m.id, m.member_code, m.name, m.email, m.phone, m.created_at,
               COUNT(CASE WHEN l.status = 'Active' THEN 1 END) AS active_loans_count
        FROM members m
        LEFT JOIN loans l ON m.id = l.member_id
        GROUP BY m.id
        ORDER BY m.name ASC;
    """)
    members = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(members), 200


@app.route('/api/members', methods=['POST'])
def add_member():
    """
    Register a new library member.
    Payload: { name, email, phone, member_code (optional, auto-generated if omitted) }
    """
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    email = (data.get('email') or '').strip()
    phone = (data.get('phone') or '').strip()
    member_code = (data.get('member_code') or '').strip()

    if not name or not email:
        return jsonify({"error": "Member Name and Email are required."}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    # Generate member_code if not supplied
    if not member_code:
        cursor.execute("SELECT COUNT(*) FROM members;")
        count = cursor.fetchone()[0] + 1
        member_code = f"MEM-{count:03d}"

    # Check uniqueness
    cursor.execute("SELECT id FROM members WHERE email = ? OR member_code = ?;", (email, member_code))
    if cursor.fetchone():
        conn.close()
        return jsonify({"error": f"Member with email '{email}' or Code '{member_code}' already exists."}), 400

    cursor.execute("""
        INSERT INTO members (member_code, name, email, phone)
        VALUES (?, ?, ?, ?);
    """, (member_code, name, email, phone))
    conn.commit()
    new_id = cursor.lastrowid
    cursor.execute("SELECT * FROM members WHERE id = ?;", (new_id,))
    member = cursor.fetchone()
    conn.close()

    return jsonify({
        "message": "Member registered successfully.",
        "member": dict(member)
    }), 201


# ==========================================
# Loan Transactions History Endpoint
# ==========================================

@app.route('/api/loans', methods=['GET'])
def list_loans():
    """List loan history with book and member information."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT l.id, l.book_id, l.member_id, l.issue_date, l.due_date, l.return_date, l.status,
               b.title AS book_title, b.isbn AS book_isbn,
               m.name AS member_name, m.member_code AS member_code
        FROM loans l
        JOIN books b ON l.book_id = b.id
        JOIN members m ON l.member_id = m.id
        ORDER BY l.id DESC
        LIMIT 50;
    """)
    loans = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(loans), 200


# ==========================================
# Error Handlers
# ==========================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Resource not found."}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error occurred."}), 500


if __name__ == '__main__':
    print("=" * 60)
    print(" Library Management System - Server Starting")
    print(" URL: http://127.0.0.1:5000")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=True)
