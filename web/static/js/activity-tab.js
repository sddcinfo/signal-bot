// Activity Tab JavaScript - NO template literals, only string concatenation

// Activity tab functions
function loadActivityData() {
    const filters = SignalBotUtils.getGlobalFilters();

    // Handle date based on date mode
    let date = '';
    if (filters.dateMode === 'today') {
        const today = new Date();
        date = today.getFullYear() + '-' +
            String(today.getMonth() + 1).padStart(2, '0') + '-' +
            String(today.getDate()).padStart(2, '0');
    } else if (filters.dateMode === 'specific' && filters.date) {
        date = filters.date;
    }

    // Build URL with all filters
    const params = {
        date: date,
        timezone: SignalBotConfig.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone,
        group_id: filters.groupId,
        sender_id: filters.senderId,
        hours: filters.hours,
        attachments_only: filters.attachmentsOnly,
        date_mode: filters.dateMode
    };

    const url = SignalBotUtils.buildUrl('/api/activity/hourly', params);

    // Clear and show loading state
    const container = document.getElementById('activity-charts-container');
    if (container) {
        container.innerHTML = SignalBotUtils.createLoadingSpinner('Loading activity data...');
    }

    fetch(url)
        .then(response => response.json())
        .then(data => {
            renderActivityCharts(data);
        })
        .catch(error => {
            console.error('Error loading activity data:', error);
            if (container) {
                container.innerHTML = SignalBotUtils.createEmptyState('Error loading activity data', '❌');
            }
        });
}

function renderActivityCharts(data) {
    const container = document.getElementById('activity-charts-container');
    if (!container) return;

    container.innerHTML = '';

    if (!data.hourly_data || Object.keys(data.hourly_data).length === 0) {
        container.innerHTML = SignalBotUtils.createEmptyState('No activity data for selected filters', '📊');
        return;
    }

    // Colors for different groups
    const colors = ['#007bff', '#28a745', '#dc3545', '#ffc107', '#17a2b8', '#6f42c1', '#fd7e14'];
    let colorIndex = 0;

    for (let groupId in data.hourly_data) {
        const groupData = data.hourly_data[groupId];
        const color = colors[colorIndex % colors.length];
        colorIndex++;

        const chartDiv = document.createElement('div');
        chartDiv.className = 'mb-4';
        chartDiv.style.backgroundColor = '#f8f9fa';
        chartDiv.style.padding = '15px';
        chartDiv.style.borderRadius = '8px';

        let chartHtml = '<h5>' + SignalBotUtils.escapeHtml(groupData.name || groupId) + '</h5>';
        chartHtml += '<div class="activity-bars" style="display: flex; align-items: flex-end; height: 150px; gap: 2px;">';

        // Calculate max for scaling
        let maxCount = 0;
        for (let hour = 0; hour < 24; hour++) {
            const count = groupData.counts[hour] || 0;
            if (count > maxCount) maxCount = count;
        }

        // Generate bars for each hour
        for (let hour = 0; hour < 24; hour++) {
            const count = groupData.counts[hour] || 0;
            const height = maxCount > 0 ? (count / maxCount) * 100 : 0;

            chartHtml += '<div style="flex: 1; background: ' + color + '; height: ' + height + '%; min-height: 2px;" ';
            chartHtml += 'title="' + hour + ':00 - ' + count + ' messages"></div>';
        }

        chartHtml += '</div>';
        chartHtml += '<div style="display: flex; justify-content: space-between; margin-top: 5px; font-size: 0.8em; color: #666;">';
        chartHtml += '<span>00:00</span><span>06:00</span><span>12:00</span><span>18:00</span><span>23:00</span>';
        chartHtml += '</div>';

        // Add total count
        let totalCount = 0;
        for (let h = 0; h < 24; h++) {
            totalCount += groupData.counts[h] || 0;
        }
        chartHtml += '<div style="margin-top: 10px; text-align: center; color: #666;">';
        chartHtml += 'Total: ' + totalCount + ' messages';
        chartHtml += '</div>';

        chartDiv.innerHTML = chartHtml;
        container.appendChild(chartDiv);
    }
}

// Auto-refresh when filters change
document.addEventListener('filtersChanged', function(event) {
    // Only reload if activity tab is active
    const activeTab = document.querySelector('.nav-link.active');
    if (activeTab && activeTab.getAttribute('data-bs-target') === '#activity') {
        loadActivityData();
    }
});

// Auto-load data when activity tab is shown
document.addEventListener('DOMContentLoaded', function() {
    // Check if activity tab is active on page load
    const activeTab = document.querySelector('.nav-link.active');
    if (activeTab && activeTab.getAttribute('data-bs-target') === '#activity') {
        setTimeout(loadActivityData, 500);
    }

    // Listen for tab changes
    const activityTabButton = document.querySelector('[data-bs-target="#activity"]');
    if (activityTabButton) {
        activityTabButton.addEventListener('click', function() {
            setTimeout(loadActivityData, 100);
        });
    }
});