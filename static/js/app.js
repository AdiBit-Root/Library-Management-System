/**
 * Library Management System - Client Application Logic
 * Implements dynamic, reload-free CRUD operations via Fetch API.
 */

// Application State
const state = {
    searchQuery: '',
    categoryFilter: 'all',
    statusFilter: 'all',
    membersCache: [],
    books: []
};

// DOM Elements
const DOM = {
    booksTableBody: document.getElementById('books-table-body'),
    emptyState: document.getElementById('empty-state'),
    emptyStateTitle: document.getElementById('empty-state-title'),
    emptyStateDesc: document.getElementById('empty-state-desc'),
    resultsCountText: document.getElementById('results-count-text'),
    searchInput: document.getElementById('search-input'),
    btnClearSearch: document.getElementById('btn-clear-search'),
    filterCategory: document.getElementById('filter-category'),
    filterStatus: document.getElementById('filter-status'),
    btnRefresh: document.getElementById('btn-refresh'),
    btnResetFilters: document.getElementById('btn-reset-filters'),
    toastContainer: document.getElementById('toast-container'),

    // Dashboard metrics
    statTotalBooks: document.getElementById('stat-total-books'),
    statAvailableBooks: document.getElementById('stat-available-books'),
    statIssuedBooks: document.getElementById('stat-issued-books'),
    statTotalMembers: document.getElementById('stat-total-members'),

    // Modals
    modalAddBook: document.getElementById('modal-add-book'),
    modalEditBook: document.getElementById('modal-edit-book'),
    modalIssueBook: document.getElementById('modal-issue-book'),
    modalMembers: document.getElementById('modal-members'),
    modalLoans: document.getElementById('modal-loans'),

    // Forms
    formAddBook: document.getElementById('form-add-book'),
    formEditBook: document.getElementById('form-edit-book'),
    formIssueBook: document.getElementById('form-issue-book'),
    formAddMember: document.getElementById('form-add-member'),

    // Top action triggers
    btnOpenAddBook: document.getElementById('btn-open-add-book'),
    btnViewMembers: document.getElementById('btn-view-members'),
    btnViewLoans: document.getElementById('btn-view-loans'),

    // Issue book modal inputs
    issueBookId: document.getElementById('issue-book-id'),
    issueBookTitle: document.getElementById('issue-book-title'),
    issueBookMeta: document.getElementById('issue-book-meta'),
    issueMemberSelect: document.getElementById('issue-member-select'),
    issueDueDate: document.getElementById('issue-due-date'),

    // Members modal table
    membersTableBody: document.getElementById('members-table-body'),
    membersListCount: document.getElementById('members-list-count'),

    // Loans modal table
    loansTableBody: document.getElementById('loans-table-body')
};

// ============================================================================
// Initialization & Event Binding
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    initApp();
    bindEvents();
});

function initApp() {
    fetchStats();
    fetchCategories();
    fetchBooks();
    preloadMembers();
}

function bindEvents() {
    // Live Search with Debounce
    let searchTimeout = null;
    DOM.searchInput.addEventListener('input', (e) => {
        state.searchQuery = e.target.value.trim();
        DOM.btnClearSearch.style.display = state.searchQuery ? 'block' : 'none';

        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            fetchBooks();
        }, 220);
    });

    DOM.btnClearSearch.addEventListener('click', () => {
        DOM.searchInput.value = '';
        state.searchQuery = '';
        DOM.btnClearSearch.style.display = 'none';
        fetchBooks();
        DOM.searchInput.focus();
    });

    // Category and Status Filters
    DOM.filterCategory.addEventListener('change', (e) => {
        state.categoryFilter = e.target.value;
        fetchBooks();
    });

    DOM.filterStatus.addEventListener('change', (e) => {
        state.statusFilter = e.target.value;
        fetchBooks();
    });

    // Refresh & Reset buttons
    DOM.btnRefresh.addEventListener('click', () => {
        fetchStats();
        fetchCategories();
        fetchBooks();
        showToast('Refreshed', 'Book inventory and metrics updated.', 'info');
    });

    DOM.btnResetFilters.addEventListener('click', resetFilters);

    // Modal Triggers
    DOM.btnOpenAddBook.addEventListener('click', () => {
        DOM.formAddBook.reset();
        openModal(DOM.modalAddBook);
    });

    DOM.btnViewMembers.addEventListener('click', () => {
        loadMembersModal();
        openModal(DOM.modalMembers);
    });

    DOM.btnViewLoans.addEventListener('click', () => {
        loadLoansModal();
        openModal(DOM.modalLoans);
    });

    // Modal Close Buttons
    document.querySelectorAll('[data-close]').forEach(button => {
        button.addEventListener('click', () => {
            const modalId = button.getAttribute('data-close');
            const targetModal = document.getElementById(modalId);
            if (targetModal) closeModal(targetModal);
        });
    });

    // Close on backdrop click
    document.querySelectorAll('.modal-backdrop').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) closeModal(modal);
        });
    });

    // Form Submissions
    DOM.formAddBook.addEventListener('submit', handleAddBookSubmit);
    DOM.formEditBook.addEventListener('submit', handleEditBookSubmit);
    DOM.formIssueBook.addEventListener('submit', handleIssueBookSubmit);
    DOM.formAddMember.addEventListener('submit', handleAddMemberSubmit);
}

function resetFilters() {
    DOM.searchInput.value = '';
    state.searchQuery = '';
    DOM.btnClearSearch.style.display = 'none';
    DOM.filterCategory.value = 'all';
    state.categoryFilter = 'all';
    DOM.filterStatus.value = 'all';
    state.statusFilter = 'all';
    fetchBooks();
}

// ============================================================================
// API Calls & Data Fetching (Fetch API)
// ============================================================================

/**
 * Fetch and render books dynamically without page reload.
 */
async function fetchBooks() {
    const params = new URLSearchParams();
    if (state.searchQuery) params.append('q', state.searchQuery);
    if (state.categoryFilter && state.categoryFilter !== 'all') params.append('category', state.categoryFilter);
    if (state.statusFilter && state.statusFilter !== 'all') params.append('status', state.statusFilter);

    try {
        const response = await fetch(`/api/books?${params.toString()}`);
        if (!response.ok) throw new Error(`HTTP error: ${response.status}`);
        const books = await response.json();
        state.books = books;
        renderBooks(books);
    } catch (error) {
        console.error('Error fetching books:', error);
        showToast('Error', 'Failed to load books from server.', 'error');
    }
}

/**
 * Fetch and update dashboard metrics counters.
 */
async function fetchStats() {
    try {
        const res = await fetch('/api/stats');
        if (!res.ok) return;
        const data = await res.json();
        DOM.statTotalBooks.textContent = data.total_books ?? 0;
        DOM.statAvailableBooks.textContent = data.available_books ?? 0;
        DOM.statIssuedBooks.textContent = data.issued_books ?? 0;
        DOM.statTotalMembers.textContent = data.total_members ?? 0;
    } catch (err) {
        console.error('Error loading stats:', err);
    }
}

/**
 * Fetch distinct book categories and populate filter dropdown.
 */
async function fetchCategories() {
    try {
        const res = await fetch('/api/categories');
        if (!res.ok) return;
        const categories = await res.json();
        const currentVal = DOM.filterCategory.value;

        let optionsHtml = '<option value="all">All Categories</option>';
        categories.forEach(cat => {
            optionsHtml += `<option value="${escapeHtml(cat)}">${escapeHtml(cat)}</option>`;
        });
        DOM.filterCategory.innerHTML = optionsHtml;

        if (categories.includes(currentVal)) {
            DOM.filterCategory.value = currentVal;
        }
    } catch (err) {
        console.error('Error loading categories:', err);
    }
}

/**
 * Preload registered members for issue dropdown.
 */
async function preloadMembers() {
    try {
        const res = await fetch('/api/members');
        if (res.ok) {
            state.membersCache = await res.json();
        }
    } catch (err) {
        console.error('Error loading members cache:', err);
    }
}

// ============================================================================
// Render Logic
// ============================================================================

function renderBooks(books) {
    DOM.booksTableBody.innerHTML = '';

    if (!books || books.length === 0) {
        document.getElementById('books-table').style.display = 'none';
        DOM.emptyState.style.display = 'flex';
        DOM.resultsCountText.textContent = '0 books found';

        if (state.searchQuery) {
            DOM.emptyStateTitle.textContent = `No books matching "${state.searchQuery}"`;
            DOM.emptyStateDesc.textContent = 'Check your search spelling or try searching by title, author, or ISBN.';
        } else if (state.categoryFilter !== 'all' || state.statusFilter !== 'all') {
            DOM.emptyStateTitle.textContent = 'No books match active filters';
            DOM.emptyStateDesc.textContent = 'Try choosing a different category or status filter.';
        } else {
            DOM.emptyStateTitle.textContent = 'Library catalog is empty';
            DOM.emptyStateDesc.textContent = 'Click "Add New Book" to start cataloging books.';
        }
        return;
    }

    document.getElementById('books-table').style.display = 'table';
    DOM.emptyState.style.display = 'none';
    DOM.resultsCountText.textContent = `Showing ${books.length} ${books.length === 1 ? 'book' : 'books'}`;

    const rowsHtml = books.map(book => {
        const isAvailable = book.status === 'Available';
        const statusBadge = isAvailable
            ? `<span class="status-badge status-available"><i class="fa-solid fa-check"></i> Available</span>`
            : `<span class="status-badge status-issued"><i class="fa-solid fa-hand-holding"></i> Issued</span>`;

        let borrowerHtml = '<span class="text-muted-dash">&mdash;</span>';
        if (!isAvailable && book.borrower_name) {
            borrowerHtml = `
                <div class="borrower-info">
                    <div class="borrower-name"><i class="fa-solid fa-user-tag"></i> ${escapeHtml(book.borrower_name)}</div>
                    <div class="borrower-due"><i class="fa-regular fa-clock"></i> Due: ${escapeHtml(book.due_date || 'N/A')}</div>
                </div>
            `;
        }

        const actionButtons = `
            <div class="action-buttons">
                ${isAvailable ? `
                    <button class="btn-action btn-action-issue" onclick="openIssueModal(${book.id})" title="Issue to member">
                        <i class="fa-solid fa-arrow-up-right-from-square"></i> Issue
                    </button>
                ` : `
                    <button class="btn-action btn-action-return" onclick="handleReturnBook(${book.id})" title="Return book">
                        <i class="fa-solid fa-arrow-rotate-left"></i> Return
                    </button>
                `}
                <button class="btn-action btn-action-edit" onclick="openEditModal(${book.id})" title="Edit details">
                    <i class="fa-solid fa-pen"></i>
                </button>
                <button class="btn-action btn-action-delete" onclick="handleDeleteBook(${book.id}, '${escapeHtml(book.title.replace(/'/g, "\\'"))}', '${book.status}')" title="Delete book">
                    <i class="fa-solid fa-trash"></i>
                </button>
            </div>
        `;

        return `
            <tr data-book-id="${book.id}">
                <td>
                    <div class="book-title-cell">
                        <span class="book-title">${escapeHtml(book.title)}</span>
                        <span class="book-author"><i class="fa-solid fa-pen-nib"></i> ${escapeHtml(book.author)}</span>
                    </div>
                </td>
                <td>
                    <span class="isbn-code">${escapeHtml(book.isbn)}</span>
                </td>
                <td>
                    <span class="category-tag">${escapeHtml(book.category)}</span>
                </td>
                <td>${statusBadge}</td>
                <td>${borrowerHtml}</td>
                <td>${actionButtons}</td>
            </tr>
        `;
    }).join('');

    DOM.booksTableBody.innerHTML = rowsHtml;
}

// ============================================================================
// CRUD Handlers: Add, Edit, Delete, Issue, Return
// ============================================================================

/**
 * Handle Add New Book Form Submission
 */
async function handleAddBookSubmit(e) {
    e.preventDefault();
    const title = document.getElementById('add-title').value.trim();
    const author = document.getElementById('add-author').value.trim();
    const isbn = document.getElementById('add-isbn').value.trim();
    const category = document.getElementById('add-category').value.trim();

    if (!title || !author || !isbn || !category) {
        showToast('Validation Error', 'Please complete all required fields.', 'error');
        return;
    }

    try {
        const response = await fetch('/api/books', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title, author, isbn, category })
        });

        const data = await response.json();
        if (!response.ok) {
            showToast('Unable to Add Book', data.error || 'Server error', 'error');
            return;
        }

        closeModal(DOM.modalAddBook);
        DOM.formAddBook.reset();
        showToast('Book Added', `"${title}" was added to catalog.`, 'success');
        fetchBooks();
        fetchStats();
        fetchCategories();
    } catch (err) {
        console.error('Error adding book:', err);
        showToast('Request Failed', 'Network or connection error.', 'error');
    }
}

/**
 * Open Edit Modal
 */
window.openEditModal = async function(bookId) {
    try {
        const res = await fetch(`/api/books/${bookId}`);
        if (!res.ok) {
            showToast('Error', 'Unable to retrieve book details.', 'error');
            return;
        }
        const book = await res.json();
        document.getElementById('edit-id').value = book.id;
        document.getElementById('edit-title').value = book.title;
        document.getElementById('edit-author').value = book.author;
        document.getElementById('edit-isbn').value = book.isbn;
        document.getElementById('edit-category').value = book.category;

        openModal(DOM.modalEditBook);
    } catch (err) {
        console.error('Error fetching book details:', err);
    }
};

/**
 * Handle Edit Book Form Submission
 */
async function handleEditBookSubmit(e) {
    e.preventDefault();
    const id = document.getElementById('edit-id').value;
    const title = document.getElementById('edit-title').value.trim();
    const author = document.getElementById('edit-author').value.trim();
    const isbn = document.getElementById('edit-isbn').value.trim();
    const category = document.getElementById('edit-category').value.trim();

    try {
        const response = await fetch(`/api/books/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title, author, isbn, category })
        });
        const data = await response.json();
        if (!response.ok) {
            showToast('Update Failed', data.error || 'Unable to update book.', 'error');
            return;
        }

        closeModal(DOM.modalEditBook);
        showToast('Book Updated', `"${title}" was updated.`, 'success');
        fetchBooks();
        fetchCategories();
    } catch (err) {
        console.error('Error updating book:', err);
        showToast('Request Failed', 'Network error occurred.', 'error');
    }
}

/**
 * Handle Delete Book Record
 */
window.handleDeleteBook = async function(bookId, bookTitle, currentStatus) {
    // Edge case check on client side as an immediate feedback
    if (currentStatus === 'Issued') {
        showToast('Action Blocked', `Cannot delete "${bookTitle}" while it is issued. Please return it first.`, 'error');
        return;
    }

    const confirmed = confirm(`Are you sure you want to delete "${bookTitle}" from the library? This cannot be undone.`);
    if (!confirmed) return;

    try {
        const response = await fetch(`/api/books/${bookId}`, {
            method: 'DELETE'
        });
        const data = await response.json();
        if (!response.ok) {
            showToast('Delete Failed', data.error || 'Could not delete book.', 'error');
            return;
        }

        showToast('Book Deleted', data.message || `Book deleted successfully.`, 'success');
        fetchBooks();
        fetchStats();
    } catch (err) {
        console.error('Error deleting book:', err);
        showToast('Request Failed', 'Network error occurred.', 'error');
    }
};

/**
 * Open Issue Modal
 */
window.openIssueModal = async function(bookId) {
    const book = state.books.find(b => b.id === bookId);
    if (!book) return;

    // Edge Case: Validate book is available
    if (book.status !== 'Available') {
        showToast('Not Available', `"${book.title}" is already issued.`, 'error');
        return;
    }

    DOM.issueBookId.value = book.id;
    DOM.issueBookTitle.textContent = book.title;
    DOM.issueBookMeta.textContent = `Author: ${book.author} | ISBN: ${book.isbn}`;

    // Calculate default due date = today + 14 days
    const d = new Date();
    d.setDate(d.getDate() + 14);
    DOM.issueDueDate.value = d.toISOString().split('T')[0];

    // Populate Member Options
    await preloadMembers();
    let membersHtml = '<option value="">-- Choose Member --</option>';
    state.membersCache.forEach(m => {
        membersHtml += `<option value="${m.id}">${escapeHtml(m.name)} (${escapeHtml(m.member_code)})</option>`;
    });
    DOM.issueMemberSelect.innerHTML = membersHtml;

    openModal(DOM.modalIssueBook);
};

/**
 * Handle Issue Book Submission
 */
async function handleIssueBookSubmit(e) {
    e.preventDefault();
    const bookId = DOM.issueBookId.value;
    const memberId = DOM.issueMemberSelect.value;
    const dueDate = DOM.issueDueDate.value;

    if (!memberId) {
        showToast('Select Member', 'Please select a registered member.', 'error');
        return;
    }

    try {
        const response = await fetch(`/api/books/${bookId}/issue`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ member_id: parseInt(memberId), due_date: dueDate })
        });
        const data = await response.json();

        if (!response.ok) {
            // Edge case error feedback
            showToast('Issue Failed', data.error || 'Could not issue book.', 'error');
            return;
        }

        closeModal(DOM.modalIssueBook);
        showToast('Book Issued', data.message, 'success');
        fetchBooks();
        fetchStats();
    } catch (err) {
        console.error('Error issuing book:', err);
        showToast('Request Failed', 'Network error occurred.', 'error');
    }
}

/**
 * Handle Return Book
 */
window.handleReturnBook = async function(bookId) {
    const book = state.books.find(b => b.id === bookId);
    const title = book ? book.title : 'this book';

    const confirmed = confirm(`Confirm return of "${title}" back to available library inventory?`);
    if (!confirmed) return;

    try {
        const response = await fetch(`/api/books/${bookId}/return`, {
            method: 'POST'
        });
        const data = await response.json();

        if (!response.ok) {
            // Edge case feedback
            showToast('Return Failed', data.error || 'Could not return book.', 'error');
            return;
        }

        showToast('Book Returned', data.message, 'success');
        fetchBooks();
        fetchStats();
    } catch (err) {
        console.error('Error returning book:', err);
        showToast('Request Failed', 'Network error occurred.', 'error');
    }
};

// ============================================================================
// Member Management
// ============================================================================

async function loadMembersModal() {
    try {
        const res = await fetch('/api/members');
        if (!res.ok) return;
        const members = await res.json();
        state.membersCache = members;
        DOM.membersListCount.textContent = members.length;

        if (members.length === 0) {
            DOM.membersTableBody.innerHTML = `<tr><td colspan="4" style="text-align:center; color:#94a3b8;">No members registered yet.</td></tr>`;
            return;
        }

        DOM.membersTableBody.innerHTML = members.map(m => `
            <tr>
                <td><span class="isbn-code">${escapeHtml(m.member_code)}</span></td>
                <td><strong>${escapeHtml(m.name)}</strong></td>
                <td>${escapeHtml(m.email)}</td>
                <td>
                    <span class="category-tag" style="background:${m.active_loans_count > 0 ? '#fffbeb' : '#f1f5f9'}; color:${m.active_loans_count > 0 ? '#b45309' : '#64748b'};">
                        ${m.active_loans_count} active
                    </span>
                </td>
            </tr>
        `).join('');
    } catch (err) {
        console.error('Error fetching members:', err);
    }
}

async function handleAddMemberSubmit(e) {
    e.preventDefault();
    const name = document.getElementById('member-name').value.trim();
    const email = document.getElementById('member-email').value.trim();
    const phone = document.getElementById('member-phone').value.trim();

    try {
        const res = await fetch('/api/members', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, email, phone })
        });
        const data = await res.json();
        if (!res.ok) {
            showToast('Registration Error', data.error || 'Could not register member.', 'error');
            return;
        }

        DOM.formAddMember.reset();
        showToast('Member Registered', `${data.member.name} registered as ${data.member.member_code}.`, 'success');
        loadMembersModal();
        fetchStats();
    } catch (err) {
        console.error('Error registering member:', err);
        showToast('Request Failed', 'Network error occurred.', 'error');
    }
}

// ============================================================================
// Loan Audit History
// ============================================================================

async function loadLoansModal() {
    try {
        const res = await fetch('/api/loans');
        if (!res.ok) return;
        const loans = await res.json();

        if (loans.length === 0) {
            DOM.loansTableBody.innerHTML = `<tr><td colspan="5" style="text-align:center; color:#94a3b8;">No loan transactions recorded.</td></tr>`;
            return;
        }

        DOM.loansTableBody.innerHTML = loans.map(l => {
            const isActive = l.status === 'Active';
            const badge = isActive
                ? `<span class="status-badge status-issued">Active</span>`
                : `<span class="status-badge status-available">Returned</span>`;

            return `
                <tr>
                    <td><strong>${escapeHtml(l.book_title)}</strong></td>
                    <td>${escapeHtml(l.member_name)} <span class="isbn-code">${escapeHtml(l.member_code)}</span></td>
                    <td>${escapeHtml((l.issue_date || '').substring(0, 10))}</td>
                    <td>${escapeHtml(l.due_date || '')}</td>
                    <td>${badge}</td>
                </tr>
            `;
        }).join('');
    } catch (err) {
        console.error('Error fetching loans:', err);
    }
}

// ============================================================================
// Modal Utilities
// ============================================================================

function openModal(modal) {
    if (!modal) return;
    modal.classList.add('is-open');
}

function closeModal(modal) {
    if (!modal) return;
    modal.classList.remove('is-open');
}

// ============================================================================
// Toast Notification Utility
// ============================================================================

function showToast(title, message, type = 'info', duration = 3800) {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    let iconClass = 'fa-circle-info';
    if (type === 'success') iconClass = 'fa-circle-check';
    if (type === 'error') iconClass = 'fa-triangle-exclamation';

    toast.innerHTML = `
        <div class="toast-icon"><i class="fa-solid ${iconClass}"></i></div>
        <div class="toast-content">
            <div class="toast-title">${escapeHtml(title)}</div>
            <div class="toast-message">${escapeHtml(message)}</div>
        </div>
    `;

    DOM.toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(15px)';
        toast.style.transition = 'all 0.25s ease';
        setTimeout(() => toast.remove(), 250);
    }, duration);
}

// ============================================================================
// Security / XSS Sanitization Helper
// ============================================================================

function escapeHtml(str) {
    if (typeof str !== 'string') return str ?? '';
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}
