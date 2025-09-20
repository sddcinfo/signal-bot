// Common JavaScript functions for Signal Bot Web Interface
// NO template literals - only string concatenation for safety

// Global configuration object - populated from data attributes
window.SignalBotConfig = {
    timezone: 'UTC',
    selectedGroup: null,
    selectedDate: null,
    selectedSender: null,
    hours: 24,
    attachmentsOnly: false
};

// Initialize configuration from page data attributes
function initializeConfig() {
    const configElement = document.getElementById('page-config');
    if (configElement) {
        SignalBotConfig.timezone = configElement.getAttribute('data-timezone') || 'UTC';
        SignalBotConfig.selectedGroup = configElement.getAttribute('data-group-id');
        SignalBotConfig.selectedDate = configElement.getAttribute('data-date');
        SignalBotConfig.selectedSender = configElement.getAttribute('data-sender-id');
        SignalBotConfig.hours = configElement.getAttribute('data-hours') || '24';
    }
}

// Common notification function
function showNotification(message, type) {
    type = type || 'info';
    const alertClass = type === 'success' ? 'alert-success' :
                      type === 'warning' ? 'alert-warning' :
                      type === 'error' ? 'alert-danger' : 'alert-info';

    const notificationHtml = '<div class="alert ' + alertClass + ' alert-dismissible fade show" role="alert" style="position: fixed; top: 20px; right: 20px; z-index: 9999; min-width: 300px;">' +
        message +
        '<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>' +
        '</div>';

    const notificationDiv = document.createElement('div');
    notificationDiv.innerHTML = notificationHtml;
    document.body.appendChild(notificationDiv.firstChild);

    // Auto-hide after 5 seconds
    setTimeout(function() {
        const alert = notificationDiv.querySelector('.alert');
        if (alert) {
            alert.remove();
        }
    }, 5000);
}

// Get global filters - use unified FilterManager if available
function getGlobalFilters() {
    // Use FilterManager if it's available
    if (typeof FilterManager !== 'undefined' && FilterManager.getFilters) {
        return FilterManager.getFilters();
    }

    // Fallback to direct DOM access
    const groupSelect = document.getElementById('global-group-filter');
    const senderSelect = document.getElementById('global-sender-filter');
    const dateInput = document.getElementById('global-date');
    const hoursSelect = document.getElementById('global-hours-filter');
    const attachmentsCheckbox = document.getElementById('global-attachments-only');
    const dateMode = document.querySelector('input[name="date-mode"]:checked');

    return {
        groupId: groupSelect ? groupSelect.value : '',
        senderId: senderSelect ? senderSelect.value : '',
        date: dateInput ? dateInput.value : '',
        hours: hoursSelect ? hoursSelect.value : '24',
        attachmentsOnly: attachmentsCheckbox ? attachmentsCheckbox.checked : false,
        dateMode: dateMode ? dateMode.value : 'all'
    };
}

// Build URL with parameters (safe string concatenation)
function buildUrl(baseUrl, params) {
    // Use FilterManager if available for consistent filter handling
    if (typeof FilterManager !== 'undefined' && FilterManager.buildUrl) {
        return FilterManager.buildUrl(baseUrl, params);
    }

    // Fallback to manual URL building
    let url = baseUrl;
    let first = true;

    for (let key in params) {
        if (params[key] !== null && params[key] !== undefined && params[key] !== '') {
            url += (first ? '?' : '&');
            url += key + '=' + encodeURIComponent(params[key]);
            first = false;
        }
    }

    return url;
}

// Format datetime for display
function formatDateTime(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleString();
}

// Format relative time
function formatRelativeTime(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return diffMins + ' minute' + (diffMins === 1 ? '' : 's') + ' ago';

    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return diffHours + ' hour' + (diffHours === 1 ? '' : 's') + ' ago';

    const diffDays = Math.floor(diffHours / 24);
    return diffDays + ' day' + (diffDays === 1 ? '' : 's') + ' ago';
}

// Escape HTML for safe display
function escapeHtml(unsafe) {
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// Convert markdown to HTML (basic version)
function markdownToHtml(text) {
    if (!text) return '';
    return text
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        .replace(/\n/g, '<br>');
}

// Poll for async job status
function pollJobStatus(jobId, endpoint, onSuccess, onError, onProgress) {
    const startTime = Date.now();
    const maxDuration = 180000; // 3 minutes timeout

    function checkStatus() {
        const url = endpoint + '?job_id=' + jobId;

        fetch(url)
            .then(response => response.json())
            .then(data => {
                if (data.status === 'completed' && data.result) {
                    if (onSuccess) onSuccess(data.result);
                } else if (data.status === 'processing') {
                    if (onProgress) onProgress(data.current_step || 'Processing');
                    setTimeout(checkStatus, 2000);
                } else if (data.status === 'error') {
                    if (onError) onError(data.error || 'Unknown error');
                } else {
                    const elapsed = Date.now() - startTime;
                    if (elapsed < maxDuration) {
                        setTimeout(checkStatus, 2000);
                    } else {
                        if (onError) onError('Operation timed out');
                    }
                }
            })
            .catch(error => {
                const elapsed = Date.now() - startTime;
                // Retry on fetch errors if we haven't exceeded the timeout
                if (elapsed < maxDuration) {
                    console.log('Retrying after fetch error:', error);
                    setTimeout(checkStatus, 3000); // Retry after 3 seconds
                } else {
                    if (onError) onError('Failed to check status: ' + error);
                }
            });
    }

    setTimeout(checkStatus, 1000);
}

// Create loading spinner
function createLoadingSpinner(message) {
    message = message || 'Loading...';
    return '<div class="text-center">' +
           '<div class="spinner-border text-primary" role="status">' +
           '<span class="visually-hidden">Loading...</span>' +
           '</div>' +
           '<p class="mt-2">' + message + '</p>' +
           '</div>';
}

// Create empty state message
function createEmptyState(message, icon) {
    icon = icon || '📭';
    return '<div class="text-center text-muted" style="padding: 40px;">' +
           '<div style="font-size: 48px;">' + icon + '</div>' +
           '<p class="mt-3">' + message + '</p>' +
           '</div>';
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initializeConfig();
});

// Export for use in other scripts
window.SignalBotUtils = {
    showNotification: showNotification,
    getGlobalFilters: getGlobalFilters,
    buildUrl: buildUrl,
    formatDateTime: formatDateTime,
    formatRelativeTime: formatRelativeTime,
    escapeHtml: escapeHtml,
    markdownToHtml: markdownToHtml,
    pollJobStatus: pollJobStatus,
    createLoadingSpinner: createLoadingSpinner,
    createEmptyState: createEmptyState
};