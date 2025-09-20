// Senders Tab JavaScript - NO template literals, only string concatenation

// Senders tab functions
function loadSenders() {
    const filters = SignalBotUtils.getGlobalFilters();
    const contentDiv = document.getElementById('senders-content');

    if (!filters.groupId) {
        contentDiv.innerHTML = SignalBotUtils.createEmptyState('Please select a group first', '👥');
        return;
    }

    contentDiv.innerHTML = SignalBotUtils.createLoadingSpinner('Loading senders...');

    const params = {
        timezone: SignalBotConfig.timezone,
        group_id: filters.groupId
    };

    const url = SignalBotUtils.buildUrl('/api/senders', params);

    fetch(url)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                renderSenders(data.senders);
            } else {
                SignalBotUtils.showNotification(data.error || 'Failed to load senders', 'error');
                contentDiv.innerHTML = SignalBotUtils.createEmptyState('Failed to load senders', '❌');
            }
        })
        .catch(error => {
            console.error('Error loading senders:', error);
            SignalBotUtils.showNotification('Error loading senders', 'error');
            contentDiv.innerHTML = SignalBotUtils.createEmptyState('Failed to load senders', '❌');
        });
}

function renderSenders(senders) {
    const contentDiv = document.getElementById('senders-content');

    if (!senders || senders.length === 0) {
        contentDiv.innerHTML = SignalBotUtils.createEmptyState('No senders found in this group', '📭');
        return;
    }

    let html = '<div class="senders-list">';
    html += '<table class="table table-hover">';
    html += '<thead><tr>';
    html += '<th>Name</th>';
    html += '<th>Messages</th>';
    html += '<th>Last Activity</th>';
    html += '<th>Actions</th>';
    html += '</tr></thead>';
    html += '<tbody>';

    senders.forEach(function(sender) {
        html += '<tr>';
        html += '<td>' + SignalBotUtils.escapeHtml(sender.name) + '</td>';
        html += '<td>' + sender.message_count + '</td>';
        html += '<td>' + SignalBotUtils.formatRelativeTime(sender.last_activity) + '</td>';
        html += '<td>';
        html += '<button class="btn btn-sm btn-primary" onclick="selectSender(\'' + sender.id + '\', \'' + SignalBotUtils.escapeHtml(sender.name).replace(/'/g, "\\'") + '\')">View Messages</button>';
        html += '</td>';
        html += '</tr>';
    });

    html += '</tbody>';
    html += '</table>';
    html += '</div>';

    contentDiv.innerHTML = html;
}

function selectSender(senderId, senderName) {
    // Update the global filter
    const senderSelect = document.getElementById('global-sender-filter');
    if (senderSelect) {
        // Check if option exists, if not add it
        let optionExists = false;
        for (let i = 0; i < senderSelect.options.length; i++) {
            if (senderSelect.options[i].value === senderId) {
                optionExists = true;
                break;
            }
        }

        if (!optionExists) {
            const option = document.createElement('option');
            option.value = senderId;
            option.textContent = senderName;
            senderSelect.appendChild(option);
        }

        senderSelect.value = senderId;
        // Trigger change event to update other filters
        const event = new Event('change', { bubbles: true });
        senderSelect.dispatchEvent(event);
    }

    // Store in config
    SignalBotConfig.selectedSender = senderId;

    // Show notification
    SignalBotUtils.showNotification('Viewing messages from: ' + senderName, 'success');

    // Switch to messages tab
    const messagesTab = document.querySelector('[data-bs-target="#all"]');
    if (messagesTab) {
        messagesTab.click();
    }
}

// Auto-load on page load if this is the active tab
document.addEventListener('DOMContentLoaded', function() {
    const activeTab = document.querySelector('.nav-link.active');
    if (activeTab && activeTab.getAttribute('data-bs-target') === '#senders') {
        loadSenders();
    }

    // Also reload when group filter changes
    const groupFilter = document.getElementById('global-group-filter');
    if (groupFilter) {
        groupFilter.addEventListener('change', function() {
            const activeTab = document.querySelector('.nav-link.active');
            if (activeTab && activeTab.getAttribute('data-bs-target') === '#senders') {
                loadSenders();
            }
        });
    }
});