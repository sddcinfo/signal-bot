// AI Analysis JavaScript - Unified interface for all AI analyses

// Update analysis description when type is selected
document.addEventListener('DOMContentLoaded', function() {
    const typeSelect = document.getElementById('analysis-type-select');
    if (typeSelect) {
        typeSelect.addEventListener('change', function() {
            updateAnalysisDescription();
        });
    }
});

function updateAnalysisDescription() {
    const typeSelect = document.getElementById('analysis-type-select');
    const descEl = document.getElementById('analysis-description');

    if (!typeSelect || !descEl) return;

    const selectedId = typeSelect.value;
    if (selectedId && analysisTypes[selectedId]) {
        descEl.textContent = analysisTypes[selectedId].description || '';
        descEl.style.display = 'block';
    } else {
        descEl.style.display = 'none';
    }
}

// Show preview of message count
function showAnalysisPreview() {
    const filters = SignalBotUtils.getGlobalFilters();
    const typeSelect = document.getElementById('analysis-type-select');

    if (!typeSelect.value) {
        SignalBotUtils.showNotification('Please select an analysis type', 'warning');
        return;
    }

    const analysisType = analysisTypes[typeSelect.value];

    // Check requirements
    if (analysisType.requires_group && !filters.groupId) {
        SignalBotUtils.showNotification('This analysis requires selecting a group', 'warning');
        return;
    }

    if (analysisType.requires_sender && !filters.senderId) {
        SignalBotUtils.showNotification('This analysis requires selecting a sender', 'warning');
        return;
    }

    const previewDiv = document.getElementById('analysis-preview');
    const previewContent = document.getElementById('analysis-preview-content');

    previewContent.innerHTML = SignalBotUtils.createLoadingSpinner('Getting preview...');
    previewDiv.style.display = 'block';

    // Build URL for preview (NO caching, real-time count)
    const params = {
        timezone: SignalBotConfig.timezone,
        analysis_type: typeSelect.value,
        group_id: filters.groupId,
        sender_id: filters.senderId,
        date: filters.date,
        hours: filters.hours,
        date_mode: filters.dateMode,
        attachments_only: filters.attachmentsOnly
    };

    const url = SignalBotUtils.buildUrl('/api/ai-analysis/preview', params);

    fetch(url)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                // Simple preview like sentiment - NO caching info, NO AI status
                let html = '<div class="preview-info" style="padding: 10px;">';
                html += '<p><strong>' + analysisType.icon + ' ' + analysisType.display_name + '</strong></p>';
                if (data.group_name) {
                    html += '<p><strong>Group:</strong> ' + data.group_name + '</p>';
                }
                html += '<p><strong>Messages:</strong> ' + data.message_count + ' messages';

                if (data.message_count < analysisType.min_messages) {
                    html += ' <span style="color: #dc3545;">(Minimum ' + analysisType.min_messages + ' required)</span>';
                }
                html += '</p>';

                if (data.hours) {
                    html += '<p><strong>Time Period:</strong> Last ' + data.hours + ' hours</p>';
                }

                html += '</div>';
                previewContent.innerHTML = html;
            } else {
                previewContent.innerHTML = '<div class="alert alert-danger">Error: ' + (data.error || 'Unknown error') + '</div>';
            }
        })
        .catch(error => {
            previewContent.innerHTML = '<div class="alert alert-danger">Error getting preview: ' + error + '</div>';
        });
}

// Run the selected analysis
function runAnalysis() {
    const filters = SignalBotUtils.getGlobalFilters();
    const typeSelect = document.getElementById('analysis-type-select');

    if (!typeSelect.value) {
        SignalBotUtils.showNotification('Please select an analysis type', 'warning');
        return;
    }

    const analysisType = analysisTypes[typeSelect.value];

    // Check requirements
    if (analysisType.requires_group && !filters.groupId) {
        SignalBotUtils.showNotification('This analysis requires selecting a group', 'warning');
        return;
    }

    if (analysisType.requires_sender && !filters.senderId) {
        SignalBotUtils.showNotification('This analysis requires selecting a sender', 'warning');
        return;
    }

    const contentDiv = document.getElementById('analysis-content');
    const resultsDiv = document.getElementById('analysis-results');
    const titleEl = document.getElementById('analysis-title');

    // Show loading state
    contentDiv.innerHTML = SignalBotUtils.createLoadingSpinner('Running ' + analysisType.display_name + '...');
    titleEl.innerHTML = analysisType.icon + ' ' + analysisType.display_name;
    resultsDiv.style.display = 'block';

    // Build URL for analysis
    const params = {
        timezone: SignalBotConfig.timezone,
        analysis_type: typeSelect.value,
        group_id: filters.groupId,
        sender_id: filters.senderId,
        date: filters.date,
        hours: filters.hours,
        date_mode: filters.dateMode,
        attachments_only: filters.attachmentsOnly,
        async: 'true'  // Use async mode for better UX
    };

    const url = SignalBotUtils.buildUrl('/api/ai-analysis/run', params);

    fetch(url)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'started' && data.job_id) {
                // Poll for job completion
                SignalBotUtils.pollJobStatus(
                    data.job_id,
                    '/api/ai-analysis/status',
                    renderAnalysisResults,
                    function(error) {
                        SignalBotUtils.showNotification('Error: ' + error, 'error');
                        contentDiv.innerHTML = SignalBotUtils.createEmptyState('Analysis failed', '❌');
                    },
                    function(step) {
                        contentDiv.innerHTML = SignalBotUtils.createLoadingSpinner('Running ' + analysisType.display_name + '... (' + step + ')');
                    }
                );
            } else if (data.status === 'success') {
                // Direct result (non-async)
                renderAnalysisResults(data);
            } else {
                SignalBotUtils.showNotification('Error: ' + (data.error || 'Unknown error'), 'error');
                contentDiv.innerHTML = SignalBotUtils.createEmptyState('Analysis failed', '❌');
            }
        })
        .catch(error => {
            SignalBotUtils.showNotification('Error running analysis: ' + error, 'error');
            contentDiv.innerHTML = SignalBotUtils.createEmptyState('Analysis failed', '❌');
        });
}

// Render analysis results
function renderAnalysisResults(data) {
    const contentDiv = document.getElementById('analysis-content');
    const titleEl = document.getElementById('analysis-title');

    if (data.status === 'success') {
        // Update title with metadata
        let title = data.display_name || 'Analysis Results';
        if (data.group_name) {
            title += ' - ' + data.group_name;
        }
        if (data.message_count) {
            title += ' (' + data.message_count + ' messages)';
        }
        titleEl.innerHTML = title;

        // Render the analysis result with markdown support
        let html = '<div class="analysis-result" style="padding: 20px; background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">';

        // Add metadata
        html += '<div class="metadata" style="margin-bottom: 20px; padding-bottom: 15px; border-bottom: 1px solid #dee2e6; font-size: 0.9em; color: #6c757d;">';
        html += '<span>Analyzed at: ' + new Date(data.analyzed_at).toLocaleString() + '</span>';
        if (data.ai_provider) {
            html += ' | <span>AI: ' + data.ai_provider;
            if (data.is_local) {
                html += ' (Local)';
            } else {
                html += ' (External)';
            }
            html += '</span>';
        }
        html += '</div>';

        // Render the actual result with markdown
        html += '<div class="result-content">';
        html += SignalBotUtils.markdownToHtml(data.result || 'No result available');
        html += '</div>';

        html += '</div>';

        contentDiv.innerHTML = html;

        SignalBotUtils.showNotification('Analysis completed successfully', 'success');
    } else {
        contentDiv.innerHTML = SignalBotUtils.createEmptyState('Analysis failed: ' + (data.error || 'Unknown error'), '❌');
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Auto-select first analysis type if available
    const typeSelect = document.getElementById('analysis-type-select');
    if (typeSelect && typeSelect.options.length > 1) {
        // Don't auto-select, let user choose
        updateAnalysisDescription();
    }

    // Add keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        if (e.ctrlKey || e.metaKey) {
            if (e.key === 'Enter') {
                e.preventDefault();
                runAnalysis();
            } else if (e.key === 'p') {
                e.preventDefault();
                showAnalysisPreview();
            }
        }
    });
});