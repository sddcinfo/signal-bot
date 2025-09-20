// All Messages Tab JavaScript - NO template literals, only string concatenation

// All tab functions
function loadAllMessages(page) {
    page = page || 1;
    const filters = SignalBotUtils.getGlobalFilters();

    const contentDiv = document.getElementById('all-messages-content');
    contentDiv.innerHTML = SignalBotUtils.createLoadingSpinner('Loading messages...');

    // Build URL using safe string concatenation
    const params = {
        timezone: SignalBotConfig.timezone,
        page: page,
        per_page: 50,
        group_id: filters.groupId,
        sender_id: filters.senderId,
        date: filters.date,
        hours: filters.hours,
        attachments_only: filters.attachmentsOnly,
        date_mode: filters.dateMode
    };

    const url = SignalBotUtils.buildUrl('/api/messages', params);

    fetch(url)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                renderAllMessages(data.messages, data.pagination);
            } else {
                SignalBotUtils.showNotification(data.error || 'Failed to load messages', 'error');
                contentDiv.innerHTML = SignalBotUtils.createEmptyState('Failed to load messages', '❌');
            }
        })
        .catch(error => {
            console.error('Error loading messages:', error);
            SignalBotUtils.showNotification('Error loading messages', 'error');
            contentDiv.innerHTML = SignalBotUtils.createEmptyState('Failed to load messages', '❌');
        });
}

function renderAllMessages(messages, pagination) {
    const contentDiv = document.getElementById('all-messages-content');

    if (!messages || messages.length === 0) {
        contentDiv.innerHTML = SignalBotUtils.createEmptyState('No messages found', '📭');
        return;
    }

    let html = '<div class="messages-list">';

    messages.forEach(function(message) {
        html += '<div class="message-item">';
        html += '<div class="message-header">';
        html += '<span class="message-sender">' + SignalBotUtils.escapeHtml(message.sender_name || 'Unknown') + '</span>';
        html += '<span class="message-time">' + SignalBotUtils.formatDateTime(message.timestamp) + '</span>';
        html += '</div>';
        html += '<div class="message-text">' + SignalBotUtils.escapeHtml(message.body || '[No content]') + '</div>';

        if (message.attachments && message.attachments.length > 0) {
            html += '<div class="message-attachments">';
            message.attachments.forEach(function(attachment) {
                html += '<span class="attachment-badge">📎 ' + SignalBotUtils.escapeHtml(attachment.filename || 'Attachment') + '</span>';
            });
            html += '</div>';
        }

        html += '</div>';
    });

    html += '</div>';

    // Add pagination controls if needed
    if (pagination && (pagination.has_prev || pagination.has_next)) {
        html += '<div class="pagination-controls">';

        if (pagination.has_prev) {
            html += '<button class="btn btn-secondary" onclick="loadAllMessages(' + (pagination.current_page - 1) + ')">Previous</button>';
        }

        html += '<span class="page-info">Page ' + pagination.current_page + ' of ' + pagination.total_pages + '</span>';

        if (pagination.has_next) {
            html += '<button class="btn btn-secondary" onclick="loadAllMessages(' + (pagination.current_page + 1) + ')">Next</button>';
        }

        html += '</div>';
    }

    contentDiv.innerHTML = html;
}

// Auto-load on page load if this is the active tab
document.addEventListener('DOMContentLoaded', function() {
    const activeTab = document.querySelector('.nav-link.active');
    if (activeTab && activeTab.getAttribute('data-bs-target') === '#all') {
        loadAllMessages(1);
    }
});