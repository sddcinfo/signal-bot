// Groups Tab JavaScript - NO template literals, only string concatenation

// Groups tab functions
function loadGroups() {
    const contentDiv = document.getElementById('groups-content');
    contentDiv.innerHTML = SignalBotUtils.createLoadingSpinner('Loading groups...');

    const params = {
        timezone: SignalBotConfig.timezone
    };

    const url = SignalBotUtils.buildUrl('/api/groups', params);

    fetch(url)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                renderGroups(data.groups);
            } else {
                SignalBotUtils.showNotification(data.error || 'Failed to load groups', 'error');
                contentDiv.innerHTML = SignalBotUtils.createEmptyState('Failed to load groups', '❌');
            }
        })
        .catch(error => {
            console.error('Error loading groups:', error);
            SignalBotUtils.showNotification('Error loading groups', 'error');
            contentDiv.innerHTML = SignalBotUtils.createEmptyState('Failed to load groups', '❌');
        });
}

function renderGroups(groups) {
    const contentDiv = document.getElementById('groups-content');

    if (!groups || groups.length === 0) {
        contentDiv.innerHTML = SignalBotUtils.createEmptyState('No groups found', '📭');
        return;
    }

    let html = '<div class="groups-grid">';

    groups.forEach(function(group) {
        html += '<div class="group-card card">';
        html += '<h4>' + SignalBotUtils.escapeHtml(group.name) + '</h4>';
        html += '<p class="text-muted">' + group.message_count + ' messages</p>';
        html += '<p class="text-muted">Last activity: ' + SignalBotUtils.formatRelativeTime(group.last_activity) + '</p>';
        html += '<button class="btn btn-sm btn-primary" onclick="selectGroup(\'' + group.id + '\', \'' + SignalBotUtils.escapeHtml(group.name).replace(/'/g, "\\'") + '\')">Select Group</button>';
        html += '</div>';
    });

    html += '</div>';
    contentDiv.innerHTML = html;
}

function selectGroup(groupId, groupName) {
    // Update the global filter
    const groupSelect = document.getElementById('global-group-filter');
    if (groupSelect) {
        groupSelect.value = groupId;
        // Trigger change event to update other filters
        const event = new Event('change', { bubbles: true });
        groupSelect.dispatchEvent(event);
    }

    // Store in config
    SignalBotConfig.selectedGroup = groupId;

    // Show notification
    SignalBotUtils.showNotification('Selected group: ' + groupName, 'success');

    // Switch to messages tab
    const messagesTab = document.querySelector('[data-bs-target="#all"]');
    if (messagesTab) {
        messagesTab.click();
    }
}

// Auto-load on page load if this is the active tab
document.addEventListener('DOMContentLoaded', function() {
    const activeTab = document.querySelector('.nav-link.active');
    if (activeTab && activeTab.getAttribute('data-bs-target') === '#groups') {
        loadGroups();
    }
});