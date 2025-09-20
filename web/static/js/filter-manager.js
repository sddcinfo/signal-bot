// Unified Filter Manager for Signal Bot Web Interface
// This ensures consistency across all tabs and components

(function() {
    'use strict';

    // Create namespace if it doesn't exist
    window.FilterManager = window.FilterManager || {};

    // Store current filter state
    let currentFilters = {
        groupId: '',
        senderId: '',
        date: '',
        hours: '24',
        attachmentsOnly: false,
        dateMode: 'all'
    };

    // Get filter values from the DOM
    FilterManager.getFilters = function() {
        // Try to get from GlobalFilters first (if it exists from filters.py)
        if (typeof GlobalFilters !== 'undefined' && GlobalFilters.getValues) {
            return GlobalFilters.getValues();
        }

        // Otherwise get directly from DOM elements
        const groupSelect = document.getElementById('global-group-filter');
        const senderSelect = document.getElementById('global-sender-filter');
        const dateInput = document.getElementById('global-date');
        const hoursSelect = document.getElementById('global-hours-filter');
        const attachmentsCheckbox = document.getElementById('global-attachments-only');
        const dateMode = document.querySelector('input[name="date-mode"]:checked');

        currentFilters = {
            groupId: groupSelect ? groupSelect.value : currentFilters.groupId,
            senderId: senderSelect ? senderSelect.value : currentFilters.senderId,
            date: dateInput ? dateInput.value : currentFilters.date,
            hours: hoursSelect ? hoursSelect.value : currentFilters.hours,
            attachmentsOnly: attachmentsCheckbox ? attachmentsCheckbox.checked : currentFilters.attachmentsOnly,
            dateMode: dateMode ? dateMode.value : currentFilters.dateMode
        };

        return currentFilters;
    };

    // Apply filters (trigger refresh)
    FilterManager.apply = function() {
        // Get current filters
        const filters = FilterManager.getFilters();

        // Store in session for persistence
        if (typeof sessionStorage !== 'undefined') {
            sessionStorage.setItem('signalbot_filters', JSON.stringify(filters));
        }

        // Trigger GlobalFilters.apply if it exists
        if (typeof GlobalFilters !== 'undefined' && GlobalFilters.apply) {
            GlobalFilters.apply();
        } else {
            // Manual refresh with filters in URL
            FilterManager.refreshWithFilters();
        }

        // Trigger custom event for tabs to listen to
        const event = new CustomEvent('filtersChanged', { detail: filters });
        document.dispatchEvent(event);
    };

    // Refresh page with current filters in URL
    FilterManager.refreshWithFilters = function() {
        const filters = FilterManager.getFilters();
        const url = new URL(window.location.href);

        // Update URL parameters
        if (filters.groupId) url.searchParams.set('group_id', filters.groupId);
        else url.searchParams.delete('group_id');

        if (filters.senderId) url.searchParams.set('sender_id', filters.senderId);
        else url.searchParams.delete('sender_id');

        if (filters.date) url.searchParams.set('date', filters.date);
        else url.searchParams.delete('date');

        if (filters.hours && filters.hours !== '24') url.searchParams.set('hours', filters.hours);
        else url.searchParams.delete('hours');

        if (filters.attachmentsOnly) url.searchParams.set('attachments_only', 'true');
        else url.searchParams.delete('attachments_only');

        if (filters.dateMode && filters.dateMode !== 'all') url.searchParams.set('date_mode', filters.dateMode);
        else url.searchParams.delete('date_mode');

        // Navigate to new URL
        window.location.href = url.toString();
    };

    // Build URL with filter parameters
    FilterManager.buildUrl = function(baseUrl, additionalParams) {
        const filters = FilterManager.getFilters();
        const params = Object.assign({}, additionalParams || {});

        // Add filter parameters
        if (filters.groupId) params.group_id = filters.groupId;
        if (filters.senderId) params.sender_id = filters.senderId;
        if (filters.date) params.date = filters.date;
        if (filters.hours) params.hours = filters.hours;
        if (filters.attachmentsOnly) params.attachments_only = 'true';

        // Build URL
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
    };

    // Initialize filters from URL/storage on page load
    FilterManager.initialize = function() {
        // Parse URL parameters first
        const urlParams = new URLSearchParams(window.location.search);

        // Check if we have any filter-related URL parameters
        const hasFilterParams = urlParams.has('group_id') ||
                              urlParams.has('sender_id') ||
                              urlParams.has('date') ||
                              urlParams.has('hours') ||
                              urlParams.has('attachments_only') ||
                              urlParams.has('date_mode');

        // Only restore from session storage if we have filter params in URL
        // This ensures clean slate when navigating to main messages page
        if (hasFilterParams && typeof sessionStorage !== 'undefined') {
            const stored = sessionStorage.getItem('signalbot_filters');
            if (stored) {
                try {
                    const storedFilters = JSON.parse(stored);
                    currentFilters = Object.assign(currentFilters, storedFilters);
                } catch (e) {
                    console.error('Failed to parse stored filters:', e);
                }
            }
        }

        // Override with URL parameters if they exist
        if (urlParams.has('group_id')) currentFilters.groupId = urlParams.get('group_id');
        if (urlParams.has('sender_id')) currentFilters.senderId = urlParams.get('sender_id');
        if (urlParams.has('date')) currentFilters.date = urlParams.get('date');
        if (urlParams.has('hours')) currentFilters.hours = urlParams.get('hours');
        if (urlParams.has('attachments_only')) currentFilters.attachmentsOnly = urlParams.get('attachments_only') === 'true';
        if (urlParams.has('date_mode')) currentFilters.dateMode = urlParams.get('date_mode');

        // If no filter params in URL, clear sessionStorage to ensure fresh start
        if (!hasFilterParams && typeof sessionStorage !== 'undefined') {
            sessionStorage.removeItem('signalbot_filters');
        }

        // Set initial values in DOM if elements exist
        setTimeout(function() {
            const groupSelect = document.getElementById('global-group-filter');
            if (groupSelect && currentFilters.groupId) groupSelect.value = currentFilters.groupId;

            const senderSelect = document.getElementById('global-sender-filter');
            if (senderSelect && currentFilters.senderId) senderSelect.value = currentFilters.senderId;

            const dateInput = document.getElementById('global-date');
            if (dateInput && currentFilters.date) dateInput.value = currentFilters.date;

            const hoursSelect = document.getElementById('global-hours-filter');
            if (hoursSelect && currentFilters.hours) hoursSelect.value = currentFilters.hours;

            const attachmentsCheckbox = document.getElementById('global-attachments-only');
            if (attachmentsCheckbox) attachmentsCheckbox.checked = currentFilters.attachmentsOnly;

            // Set date mode radio
            if (currentFilters.dateMode) {
                const radio = document.getElementById('global-date-mode-' + currentFilters.dateMode);
                if (radio) radio.checked = true;
            }
        }, 100);
    };

    // Reset all filters
    FilterManager.reset = function() {
        // Clear session storage
        if (typeof sessionStorage !== 'undefined') {
            sessionStorage.removeItem('signalbot_filters');
        }

        // If GlobalFilters exists, use its reset function
        if (typeof GlobalFilters !== 'undefined' && GlobalFilters.reset) {
            GlobalFilters.reset();
        } else {
            // Manual reset - navigate to clean URL
            const currentUrl = new URL(window.location.pathname, window.location.origin);
            const tab = new URLSearchParams(window.location.search).get('tab');
            if (tab) {
                currentUrl.searchParams.set('tab', tab);
            }
            window.location.href = currentUrl.toString();
        }
    };

    // Listen for filter changes
    FilterManager.attachListeners = function() {
        // Group filter
        const groupSelect = document.getElementById('global-group-filter');
        if (groupSelect) {
            groupSelect.addEventListener('change', FilterManager.apply);
        }

        // Sender filter
        const senderSelect = document.getElementById('global-sender-filter');
        if (senderSelect) {
            senderSelect.addEventListener('change', FilterManager.apply);
        }

        // Date input
        const dateInput = document.getElementById('global-date');
        if (dateInput) {
            dateInput.addEventListener('change', FilterManager.apply);
        }

        // Hours filter
        const hoursSelect = document.getElementById('global-hours-filter');
        if (hoursSelect) {
            hoursSelect.addEventListener('change', FilterManager.apply);
        }

        // Attachments checkbox
        const attachmentsCheckbox = document.getElementById('global-attachments-only');
        if (attachmentsCheckbox) {
            attachmentsCheckbox.addEventListener('change', FilterManager.apply);
        }

        // Date mode radios
        const dateRadios = document.querySelectorAll('input[name="date-mode"]');
        dateRadios.forEach(function(radio) {
            radio.addEventListener('change', FilterManager.apply);
        });
    };

    // Auto-initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            FilterManager.initialize();
            FilterManager.attachListeners();
        });
    } else {
        FilterManager.initialize();
        FilterManager.attachListeners();
    }
})();