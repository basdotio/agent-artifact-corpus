// ============================================================
// Auth helpers
// ============================================================
function saveToken(token, role) {
    localStorage.setItem('token', token);
    localStorage.setItem('role', role || 'user');
}
function getToken() { return localStorage.getItem('token'); }
function logout() { localStorage.clear(); window.location.href = '/'; }
function authHeaders() {
    return { 'Authorization': 'Bearer ' + getToken(), 'Content-Type': 'application/json' };
}


// ============================================================
// Login page
// ============================================================
function showTab(tab, event) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    if (event && event.target) event.target.classList.add('active');
    document.getElementById('login-form').style.display = tab === 'login' ? 'flex' : 'none';
    document.getElementById('register-form').style.display = tab === 'register' ? 'flex' : 'none';
}

async function loadDepartments() {
    const res = await fetch('/departments');
    const data = await res.json();
    const select = document.getElementById('reg-department');
    if (!select) return;
    select.innerHTML = data.departments.map(d =>
        `<option value="${d.id}">${d.name}${d.description ? ' — ' + d.description : ''}</option>`
    ).join('');
}

async function handleLogin(e) {
    e.preventDefault();
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;
    const res = await fetch('/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
    });
    if (res.ok) {
        const data = await res.json();
        saveToken(data.access_token, data.role);
        window.location.href = '/chat';
    } else {
        document.getElementById('auth-error').textContent = 'Invalid credentials';
    }
}

async function handleRegister(e) {
    e.preventDefault();
    const email = document.getElementById('reg-email').value;
    const password = document.getElementById('reg-password').value;
    const department_id = parseInt(document.getElementById('reg-department').value);
    const res = await fetch('/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, department_id })
    });
    if (res.ok) {
        const data = await res.json();
        saveToken(data.access_token, 'user');
        window.location.href = '/chat';
    } else {
        document.getElementById('auth-error').textContent = 'Registration failed';
    }
}

if (document.getElementById('reg-department')) {
    loadDepartments();
}


// ============================================================
// Chat page
// ============================================================
let currentSession = null;

async function initChat() {
    if (!getToken()) { window.location.href = '/'; return; }
    const res = await fetch('/auth/me', { headers: authHeaders() });
    if (!res.ok) { logout(); return; }
    const user = await res.json();
    document.getElementById('user-email').textContent = user.email;
    if (user.department_name) {
        document.getElementById('user-dept').textContent = '🏢 ' + user.department_name;
    }
    if (user.role === 'admin') {
        document.getElementById('admin-link').style.display = 'inline';
    }
}

async function sendMessage() {
    const input = document.getElementById('question');
    const question = input.value.trim();
    if (!question) return;
    input.value = '';

    const welcome = document.querySelector('.welcome');
    if (welcome) welcome.remove();

    addMessage(question, 'user');
    const loading = addMessage('Thinking...', 'assistant');

    try {
        const res = await fetch('/chat', {
            method: 'POST',
            headers: authHeaders(),
            body: JSON.stringify({ question, session_id: currentSession })
        });

        loading.remove();

        if (!res.ok) {
            addMessage('Error: could not get a response.', 'assistant');
            return;
        }

        const data = await res.json();
        currentSession = data.session_id;

        let text = data.answer;
        if (data.sources && data.sources.length) {
            text += '\n\n📎 Sources: ' + data.sources.map(s => s.source).join(', ');
        }
        addMessage(text, 'assistant');
    } catch (err) {
        loading.remove();
        addMessage('Error: ' + err.message, 'assistant');
    }
}

function addMessage(text, role) {
    const div = document.createElement('div');
    div.className = 'message ' + role;
    div.textContent = text;
    document.getElementById('messages').appendChild(div);
    div.scrollIntoView({ behavior: 'smooth' });
    return div;
}


// ============================================================
// Admin page
// ============================================================
async function initAdmin() {
    if (!getToken()) { window.location.href = '/'; return; }
    await loadStats();
    await loadDepartmentsForAdmin();
    await loadDocuments();
    await loadUsers();
}

async function loadStats() {
    const res = await fetch('/admin/stats', { headers: authHeaders() });
    if (!res.ok) { window.location.href = '/chat'; return; }
    const stats = await res.json();
    document.getElementById('stats').innerHTML = `
        <div class="row"><span>Total Documents</span><strong>${stats.document_count}</strong></div>
        <div class="row"><span>Total Embeddings</span><strong>${stats.embedding_count}</strong></div>
    `;
}

async function loadDepartmentsForAdmin() {
    const res = await fetch('/admin/departments', { headers: authHeaders() });
    const data = await res.json();

    document.getElementById('departments').innerHTML = data.departments.map(d =>
        `<div class="row"><span><strong>${d.name}</strong> — ${d.description || ''}</span></div>`
    ).join('');

    const select = document.getElementById('upload-department');
    if (select) {
        select.innerHTML = '<option value="">— Select department —</option>' +
            data.departments.map(d =>
                `<option value="${d.id}">${d.name}</option>`
            ).join('');
    }
}

async function createDepartment() {
    const name = document.getElementById('new-dept-name').value.trim();
    const description = document.getElementById('new-dept-desc').value.trim();
    if (!name) return alert('Name required');

    const res = await fetch('/admin/departments', {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({ name, description })
    });
    if (res.ok) {
        document.getElementById('new-dept-name').value = '';
        document.getElementById('new-dept-desc').value = '';
        await loadDepartmentsForAdmin();
    } else {
        alert('Failed to create department (may already exist)');
    }
}

async function loadDocuments() {
    const res = await fetch('/documents', { headers: authHeaders() });
    const data = await res.json();
    document.getElementById('documents').innerHTML = data.documents.length ? data.documents.map(d =>
        `<div class="row">
            <span><strong>[${d.department || 'None'}]</strong> ${d.source} — ${d.content.slice(0, 60)}...</span>
            <button onclick="deleteDoc(${d.id})">Delete</button>
         </div>`
    ).join('') : '<p style="color:#888">No documents yet.</p>';
}

async function loadUsers() {
    const res = await fetch('/admin/users', { headers: authHeaders() });
    if (!res.ok) return;
    const data = await res.json();
    document.getElementById('users').innerHTML = data.users.map(u =>
        `<div class="row">
            <span>${u.email} <strong>(${u.role}${u.department ? ' / ' + u.department : ''})</strong></span>
            <button onclick="deleteUser(${u.id})">Delete</button>
         </div>`
    ).join('');
}

async function uploadDoc() {
    const content = document.getElementById('doc-content').value;
    const source = document.getElementById('doc-source').value || 'manual';
    const department_id = document.getElementById('upload-department').value;

    if (!content) return alert('Content required');
    if (!department_id) return alert('Select a department');

    const form = new FormData();
    form.append('content', content);
    form.append('source', source);
    form.append('department_id', department_id);

    const res = await fetch('/documents/upload', {
        method: 'POST',
        headers: { 'Authorization': 'Bearer ' + getToken() },
        body: form
    });
    if (res.ok) {
        const data = await res.json();
        alert(`Imported ${data.imported} chunks`);
        document.getElementById('doc-content').value = '';
        document.getElementById('doc-source').value = '';
        await loadStats();
        await loadDocuments();
    } else {
        alert('Upload failed');
    }
}

async function deleteDoc(id) {
    if (!confirm('Delete this document?')) return;
    await fetch(`/documents/${id}`, { method: 'DELETE', headers: authHeaders() });
    await loadDocuments();
}

async function deleteUser(id) {
    if (!confirm('Delete this user?')) return;
    await fetch(`/admin/users/${id}`, { method: 'DELETE', headers: authHeaders() });
    await loadUsers();
}