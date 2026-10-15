// Configuration
const API_URL = '/api'; // Update this with your API Gateway URL when deployed
const API_KEY = ''; // Update this with your API key when deployed

// Chart objects
let categoryChart = null;
let dailyChart = null;

// Initialize the dashboard
document.addEventListener('DOMContentLoaded', function() {
    // Load initial data
    loadDashboardData();
    
    // Set up event listeners
    document.getElementById('subscriber-form').addEventListener('submit', addSubscriber);
    document.getElementById('update-btn').addEventListener('click', updateSubscriber);
    document.getElementById('remove-btn').addEventListener('click', removeSubscriber);
    document.getElementById('message-form').addEventListener('submit', sendMessage);
    document.getElementById('refresh-btn').addEventListener('click', loadDashboardData);
});

// Load dashboard data
function loadDashboardData() {
    // Load subscribers
    fetchWithAuth(`${API_URL}/subscribers`)
        .then(response => response.json())
        .then(data => {
            updateSubscribersList(data.subscribers);
            document.getElementById('total-subscribers').textContent = data.count;
        })
        .catch(error => console.error('Error loading subscribers:', error));
    
    // Load analytics
    fetchWithAuth(`${API_URL}/analytics`)
        .then(response => response.json())
        .then(data => {
            updateAnalytics(data);
        })
        .catch(error => console.error('Error loading analytics:', error));
}

// Update subscribers list
function updateSubscribersList(subscribers) {
    const tableBody = document.getElementById('subscribers-table');
    tableBody.innerHTML = '';
    
    subscribers.forEach(sub => {
        const row = document.createElement('tr');
        
        // Phone number
        const phoneCell = document.createElement('td');
        phoneCell.textContent = sub.phone_number;
        row.appendChild(phoneCell);
        
        // Category
        const categoryCell = document.createElement('td');
        categoryCell.textContent = sub.preferred_category || 'Default';
        row.appendChild(categoryCell);
        
        // Status
        const statusCell = document.createElement('td');
        const statusBadge = document.createElement('span');
        statusBadge.className = `badge ${sub.active ? 'bg-success' : 'bg-danger'}`;
        statusBadge.textContent = sub.active ? 'Active' : 'Inactive';
        statusCell.appendChild(statusBadge);
        row.appendChild(statusCell);
        
        // Created date
        const createdCell = document.createElement('td');
        createdCell.textContent = sub.created_at ? new Date(sub.created_at).toLocaleDateString() : 'N/A';
        row.appendChild(createdCell);
        
        // Actions
        const actionsCell = document.createElement('td');
        
        // Edit button
        const editBtn = document.createElement('button');
        editBtn.className = 'btn btn-sm btn-outline-primary me-1';
        editBtn.textContent = 'Edit';
        editBtn.addEventListener('click', () => {
            document.getElementById('phone').value = sub.phone_number;
            document.getElementById('category').value = sub.preferred_category || 'motivation';
        });
        actionsCell.appendChild(editBtn);
        
        // Send button
        const sendBtn = document.createElement('button');
        sendBtn.className = 'btn btn-sm btn-outline-success';
        sendBtn.textContent = 'Send';
        sendBtn.addEventListener('click', () => {
            document.getElementById('message-phone').value = sub.phone_number;
        });
        actionsCell.appendChild(sendBtn);
        
        row.appendChild(actionsCell);
        
        tableBody.appendChild(row);
    });
}

// Update analytics charts
function updateAnalytics(data) {
    document.getElementById('total-messages').textContent = data.total_messages || 0;
    document.getElementById('total-categories').textContent = Object.keys(data.category_counts || {}).length;
    
    // Update category chart
    updateCategoryChart(data.category_counts || {});
    
    // Update daily chart
    updateDailyChart(data.daily_counts || {});
}

// Update category chart
function updateCategoryChart(categoryData) {
    const ctx = document.getElementById('category-chart').getContext('2d');
    
    const labels = Object.keys(categoryData);
    const data = Object.values(categoryData);
    
    if (categoryChart) {
        categoryChart.destroy();
    }
    
    categoryChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: [
                    'rgba(255, 99, 132, 0.7)',
                    'rgba(54, 162, 235, 0.7)',
                    'rgba(255, 206, 86, 0.7)',
                    'rgba(75, 192, 192, 0.7)'
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false
        }
    });
}

// Update daily chart
function updateDailyChart(dailyData) {
    const ctx = document.getElementById('daily-chart').getContext('2d');
    
    // Sort dates
    const sortedDates = Object.keys(dailyData).sort();
    const data = sortedDates.map(date => dailyData[date]);
    
    if (dailyChart) {
        dailyChart.destroy();
    }
    
    dailyChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: sortedDates,
            datasets: [{
                label: 'Messages Sent',
                data: data,
                borderColor: 'rgba(75, 192, 192, 1)',
                backgroundColor: 'rgba(75, 192, 192, 0.2)',
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0
                    }
                }
            }
        }
    });
}

// Add subscriber
function addSubscriber(event) {
    event.preventDefault();
    
    const phone = document.getElementById('phone').value;
    const category = document.getElementById('category').value;
    
    fetchWithAuth(`${API_URL}/subscribers`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            action: 'add',
            phone: phone,
            category: category
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Subscriber added successfully!');
            loadDashboardData();
        } else {
            alert(`Error: ${data.message}`);
        }
    })
    .catch(error => {
        console.error('Error adding subscriber:', error);
        alert('An error occurred. Please try again.');
    });
}

// Update subscriber
function updateSubscriber() {
    const phone = document.getElementById('phone').value;
    const category = document.getElementById('category').value;
    
    if (!phone) {
        alert('Please enter a phone number');
        return;
    }
    
    fetchWithAuth(`${API_URL}/subscribers`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            action: 'update',
            phone: phone,
            category: category
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Subscriber updated successfully!');
            loadDashboardData();
        } else {
            alert(`Error: ${data.message}`);
        }
    })
    .catch(error => {
        console.error('Error updating subscriber:', error);
        alert('An error occurred. Please try again.');
    });
}

// Remove subscriber
function removeSubscriber() {
    const phone = document.getElementById('phone').value;
    
    if (!phone) {
        alert('Please enter a phone number');
        return;
    }
    
    if (!confirm(`Are you sure you want to remove ${phone}?`)) {
        return;
    }
    
    fetchWithAuth(`${API_URL}/subscribers`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            action: 'remove',
            phone: phone
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Subscriber removed successfully!');
            loadDashboardData();
        } else {
            alert(`Error: ${data.message}`);
        }
    })
    .catch(error => {
        console.error('Error removing subscriber:', error);
        alert('An error occurred. Please try again.');
    });
}

// Send message
function sendMessage(event) {
    event.preventDefault();
    
    const phone = document.getElementById('message-phone').value;
    const message = document.getElementById('message-text').value;
    const category = document.getElementById('message-category').value;
    
    fetchWithAuth(`${API_URL}/send`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            phone: phone,
            message: message,
            category: category
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Message sent successfully!');
            document.getElementById('message-text').value = '';
        } else {
            alert(`Error: ${data.message}`);
        }
    })
    .catch(error => {
        console.error('Error sending message:', error);
        alert('An error occurred. Please try again.');
    });
}

// Helper function for authenticated API calls
function fetchWithAuth(url, options = {}) {
    // Add API key to headers if available
    if (API_KEY) {
        options.headers = options.headers || {};
        options.headers['x-api-key'] = API_KEY;
    }
    
    return fetch(url, options);
}