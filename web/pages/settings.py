"""
Settings page - consolidated settings with tabbed interface.
"""

from typing import Dict, Any
from ..shared.base_page import BasePage
from services.ai_provider import get_ai_status, save_ai_configuration


class SettingsPage(BasePage):
    """Consolidated settings page with tabs for Setup and AI Config."""

    @property
    def title(self) -> str:
        return "⚙️ Settings"

    @property
    def nav_key(self) -> str:
        return "settings"

    @property
    def subtitle(self) -> str:
        return "Configure bot settings"

    def get_custom_css(self) -> str:
        """Additional CSS for provider cards."""
        return """
            .provider-card {
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 15px;
                margin-bottom: 15px;
                background: white;
            }
            .provider-available { border-left: 4px solid #28a745; }
            .provider-unavailable { border-left: 4px solid #dc3545; }
            .status-badge {
                padding: 3px 8px;
                border-radius: 12px;
                font-size: 0.85em;
                font-weight: 500;
            }
            .status-available {
                background: #d4edda;
                color: #155724;
            }
            .status-unavailable {
                background: #f8d7da;
                color: #721c24;
            }
            .provider-details {
                margin-top: 15px;
                display: grid;
                grid-template-columns: auto 1fr;
                gap: 8px;
                font-size: 0.9em;
            }
            .provider-details dt {
                font-weight: 600;
                color: #495057;
                text-align: right;
                padding-right: 10px;
            }
            .provider-details dd {
                margin: 0;
                color: #212529;
            }
            .alert {
                padding: 12px;
                margin: 10px 0;
                border-radius: 4px;
            }
            .alert-success {
                background-color: #d4edda;
                border: 1px solid #c3e6cb;
                color: #155724;
            }
            .alert-error {
                background-color: #f8d7da;
                border: 1px solid #f5c6cb;
                color: #721c24;
            }
        """

    def get_custom_js(self) -> str:
        """Combined JavaScript for both Setup and AI Config."""
        return """
            // Tab switching using URL navigation
            function switchTab(tab) {
                window.location.href = '/settings?tab=' + tab;
            }

            // Setup functions
            async function runSetup() {
                const btn = document.getElementById('run-setup');
                const output = document.getElementById('setup-output');

                btn.disabled = true;
                btn.textContent = 'Running Setup...';
                output.textContent = 'Starting setup...\\n';

                try {
                    const response = await fetch('/api/setup/run');
                    const result = await response.json();

                    output.textContent += `Setup completed:\\n`;
                    output.textContent += `Success: ${result.success}\\n`;
                    output.textContent += `Steps: ${result.steps_completed.join(', ')}\\n`;

                    if (result.errors.length > 0) {
                        output.textContent += `Errors: ${result.errors.join(', ')}\\n`;
                    }

                    // Display QR code if available
                    if (result.linking_qr) {
                        output.innerHTML += `<br><strong>Device Linking Required:</strong><br>`;
                        output.innerHTML += `<p>Scan this QR code with your Signal app:</p>`;

                        if (result.linking_qr.qr_code) {
                            output.innerHTML += `<div style="text-align: center; margin: 20px 0;">`;
                            output.innerHTML += `<img src="${result.linking_qr.qr_code}" alt="QR Code" style="max-width: 300px; border: 1px solid #ccc;">`;
                            output.innerHTML += `</div>`;
                        }

                        output.innerHTML += `<p><em>After scanning, setup will complete automatically.</em></p>`;
                    } else if (result.success) {
                        output.textContent += '\\nSetup completed successfully! Refreshing...';
                        setTimeout(() => location.reload(), 2000);
                    }
                } catch (error) {
                    output.textContent += `Error: ${error.message}\\n`;
                } finally {
                    btn.disabled = false;
                    btn.textContent = 'Run Setup';
                }
            }

            async function syncGroups() {
                const btn = document.getElementById('sync-groups');
                const output = document.getElementById('setup-output');

                btn.disabled = true;
                btn.textContent = 'Syncing...';
                output.textContent = 'Syncing groups...\\n';

                try {
                    const response = await fetch('/api/setup/sync', { method: 'POST' });
                    const result = await response.json();

                    output.textContent += `Groups synced: ${result.synced_count}\\n`;
                    output.textContent += 'Sync completed! Refreshing...';
                    setTimeout(() => location.reload(), 2000);
                } catch (error) {
                    output.textContent += `Error: ${error.message}\\n`;
                } finally {
                    btn.disabled = false;
                    btn.textContent = 'Sync Groups';
                }
            }

            async function syncUsers() {
                const btn = document.getElementById('sync-users');
                const output = document.getElementById('setup-output');

                btn.disabled = true;
                btn.textContent = 'Syncing...';
                output.textContent = 'Syncing users...\\n';

                try {
                    const response = await fetch('/api/setup/sync-users', { method: 'POST' });
                    const result = await response.json();

                    if (result.success) {
                        output.textContent += `Users synced successfully!\\n`;
                        output.textContent += `Total users: ${result.total_users || 0}\\n`;
                        output.textContent += `Configured users: ${result.configured_users || 0}\\n`;
                        output.textContent += 'Refreshing...';
                        setTimeout(() => location.reload(), 2000);
                    } else {
                        output.textContent += `Sync failed: ${result.error || 'Unknown error'}\\n`;
                    }
                } catch (error) {
                    output.textContent += `Error: ${error.message}\\n`;
                } finally {
                    btn.disabled = false;
                    btn.textContent = 'Sync Users';
                }
            }

            async function cleanImport() {
                const btn = document.getElementById('clean-import');
                const output = document.getElementById('setup-output');

                if (!confirm('This will clear all users and group memberships, then reimport clean data. Continue?')) {
                    return;
                }

                btn.disabled = true;
                btn.textContent = 'Importing...';
                output.textContent = 'Starting clean import...\\n';

                try {
                    const response = await fetch('/api/setup/clean-import', { method: 'POST' });
                    const result = await response.json();

                    if (result.success) {
                        output.textContent += `Import completed!\\n`;
                        output.textContent += `Contacts: ${result.contacts_imported}\\n`;
                        output.textContent += `Groups: ${result.groups_synced}\\n`;
                        output.textContent += 'Refreshing...';
                        setTimeout(() => location.reload(), 2000);
                    } else {
                        output.textContent += `Import failed: ${result.error || 'Unknown error'}\\n`;
                    }
                } catch (error) {
                    output.textContent += `Error: ${error.message}\\n`;
                } finally {
                    btn.disabled = false;
                    btn.textContent = 'Clean Import';
                }
            }

            // AI Config functions
            let currentConfig = {};

            async function refreshAIStatus() {
                const container = document.getElementById('providers-container');
                container.innerHTML = '<div class="loading" style="text-align: center; padding: 40px; color: #666;">Loading AI provider status...</div>';

                try {
                    const response = await fetch('/api/ai-status');
                    const data = await response.json();
                    displayProviders(data);
                    loadConfiguration(data.configuration);
                } catch (error) {
                    container.innerHTML = `<div class="error">Error loading AI status: ${error.message}</div>`;
                }
            }

            function loadConfiguration(config) {
                if (!config) return;
                currentConfig = config;

                // Load Ollama configuration
                if (config.ollama) {
                    document.getElementById('ollama-host').value = config.ollama.host || '';
                    document.getElementById('ollama-enabled').checked = config.ollama.enabled === 'true';

                    // Load models if host is configured
                    if (config.ollama.host) {
                        loadOllamaModels(config.ollama.host, config.ollama.model);
                    }
                }

                // Load Gemini configuration
                if (config.gemini) {
                    document.getElementById('gemini-path').value = config.gemini.path || 'gemini';
                    document.getElementById('gemini-enabled').checked = config.gemini.enabled === 'true';
                }
            }

            async function loadOllamaModels(host, selectedModel) {
                const select = document.getElementById('ollama-model');

                try {
                    // Use our proxy endpoint to avoid CORS issues
                    const response = await fetch(`/api/ollama-models?host=${encodeURIComponent(host)}`);
                    if (response.ok) {
                        const data = await response.json();
                        const models = data.models || [];

                        select.innerHTML = models.length > 0
                            ? '<option value="">Select a model...</option>'
                            : '<option value="">No models available</option>';

                        models.forEach(model => {
                            const option = document.createElement('option');
                            option.value = model;
                            option.textContent = model;
                            if (model === selectedModel) {
                                option.selected = true;
                            }
                            select.appendChild(option);
                        });
                    } else {
                        select.innerHTML = '<option value="">Failed to load models</option>';
                    }
                } catch (error) {
                    select.innerHTML = '<option value="">Error loading models</option>';
                }
            }

            async function testOllama() {
                const host = document.getElementById('ollama-host').value;
                if (!host) {
                    alert('Please enter Ollama host URL');
                    return;
                }

                try {
                    // Use our proxy endpoint to test connection
                    const response = await fetch(`/api/ollama-models?host=${encodeURIComponent(host)}`);
                    if (response.ok) {
                        const data = await response.json();
                        if (data.status === 'success') {
                            loadOllamaModels(host);
                            alert(`✅ Connected successfully! Found ${data.models?.length || 0} models.`);
                        } else {
                            alert(`❌ Failed to connect: ${data.error}`);
                        }
                    } else {
                        alert(`❌ Failed to connect: HTTP ${response.status}`);
                    }
                } catch (error) {
                    alert(`❌ Connection failed: ${error.message}`);
                }
            }

            async function saveAIConfiguration() {
                const config = {
                    ollama: {
                        host: document.getElementById('ollama-host').value,
                        model: document.getElementById('ollama-model').value,
                        enabled: document.getElementById('ollama-enabled').checked
                    },
                    gemini: {
                        path: document.getElementById('gemini-path').value,
                        enabled: document.getElementById('gemini-enabled').checked
                    }
                };

                const messageDiv = document.getElementById('config-message');
                messageDiv.innerHTML = '<div class="alert alert-info">Saving configuration...</div>';

                try {
                    const response = await fetch('/api/ai-config', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(config)
                    });

                    const data = await response.json();

                    if (data.status === 'success') {
                        messageDiv.innerHTML = '<div class="alert alert-success">✅ Configuration saved successfully!</div>';
                        setTimeout(() => refreshAIStatus(), 1000);
                    } else {
                        messageDiv.innerHTML = `<div class="alert alert-error">❌ Error: ${data.error}</div>`;
                    }
                } catch (error) {
                    messageDiv.innerHTML = `<div class="alert alert-error">❌ Error: ${error.message}</div>`;
                }
            }

            // AI Analysis Types functions
            async function loadAnalysisTypes() {
                const container = document.getElementById('analysis-types-list');
                container.innerHTML = '<div class="loading">Loading analysis types...</div>';

                try {
                    const response = await fetch('/api/ai-analysis/types');
                    const data = await response.json();

                    if (data.status === 'success' && data.types) {
                        displayAnalysisTypes(data.types);
                    } else {
                        container.innerHTML = '<div class="error">Error loading analysis types</div>';
                    }
                } catch (error) {
                    container.innerHTML = '<div class="error">Error: ' + error.message + '</div>';
                }
            }

            function displayAnalysisTypes(types) {
                const container = document.getElementById('analysis-types-list');

                if (types.length === 0) {
                    container.innerHTML = '<div class="empty-state">No analysis types configured</div>';
                    return;
                }

                let html = '<div class="analysis-types">';
                types.forEach(type => {
                    const isBuiltin = type.is_builtin === 1;
                    const isActive = type.is_active === 1;

                    html += `
                        <div class="analysis-type-card" style="border: 1px solid #dee2e6; padding: 15px; margin-bottom: 15px; border-radius: 8px;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <h4 style="margin: 0;">
                                    <span style="font-size: 1.5em; margin-right: 10px;">${type.icon || '🤖'}</span>
                                    ${type.display_name}
                                    ${isBuiltin ? '<span style="background: #e7f3ff; color: #004085; padding: 2px 6px; border-radius: 3px; font-size: 0.7em; margin-left: 10px;">Built-in</span>' : ''}
                                </h4>
                                <div>
                                    <button class="btn btn-sm ${isActive ? 'btn-success' : 'btn-secondary'}"
                                            onclick="toggleAnalysisType(${type.id})"
                                            style="padding: 5px 10px; margin-right: 5px;">
                                        ${isActive ? 'Active' : 'Inactive'}
                                    </button>
                                    ${!isBuiltin ? `
                                        <button class="btn btn-sm btn-primary" onclick="editAnalysisType(${type.id})" style="padding: 5px 10px; margin-right: 5px;">Edit</button>
                                        <button class="btn btn-sm btn-danger" onclick="deleteAnalysisType(${type.id})" style="padding: 5px 10px;">Delete</button>
                                    ` : ''}
                                </div>
                            </div>
                            <p style="color: #666; margin: 10px 0 5px 0;">${type.description || 'No description'}</p>
                            <div style="font-size: 0.85em; color: #999;">
                                <span style="margin-right: 15px;">Min messages: ${type.min_messages}</span>
                                <span style="margin-right: 15px;">Max hours: ${type.max_hours}</span>
                                ${type.requires_group ? '<span style="margin-right: 15px;">Requires group</span>' : ''}
                                ${type.requires_sender ? '<span>Requires sender filter</span>' : ''}
                            </div>
                        </div>
                    `;
                });
                html += '</div>';

                container.innerHTML = html;
            }

            async function toggleAnalysisType(id) {
                try {
                    const response = await fetch(`/api/ai-analysis/type/${id}/toggle`, { method: 'POST' });
                    const data = await response.json();

                    if (data.status === 'success') {
                        loadAnalysisTypes();
                    } else {
                        alert('Error toggling analysis type: ' + data.error);
                    }
                } catch (error) {
                    alert('Error: ' + error.message);
                }
            }

            async function deleteAnalysisType(id) {
                if (!confirm('Are you sure you want to delete this analysis type?')) return;

                try {
                    const response = await fetch(`/api/ai-analysis/type/${id}`, { method: 'DELETE' });
                    const data = await response.json();

                    if (data.status === 'success') {
                        loadAnalysisTypes();
                    } else {
                        alert('Error deleting analysis type: ' + data.error);
                    }
                } catch (error) {
                    alert('Error: ' + error.message);
                }
            }

            function editAnalysisType(id) {
                // TODO: Implement edit functionality
                alert('Edit functionality coming soon!');
            }

            function showAddAnalysisType() {
                const form = document.getElementById('add-analysis-form');
                form.style.display = form.style.display === 'none' ? 'block' : 'none';
            }

            async function saveNewAnalysisType() {
                const config = {
                    name: document.getElementById('new-type-name').value,
                    display_name: document.getElementById('new-type-display').value,
                    description: document.getElementById('new-type-description').value,
                    icon: document.getElementById('new-type-icon').value || '🤖',
                    prompt_template: document.getElementById('new-type-prompt').value,
                    requires_group: document.getElementById('new-type-requires-group').checked,
                    requires_sender: document.getElementById('new-type-requires-sender').checked,
                    min_messages: parseInt(document.getElementById('new-type-min-messages').value) || 5,
                    max_hours: parseInt(document.getElementById('new-type-max-hours').value) || 168
                };

                if (!config.name || !config.display_name || !config.prompt_template) {
                    alert('Please fill in all required fields');
                    return;
                }

                try {
                    const response = await fetch('/api/ai-analysis/type', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(config)
                    });
                    const data = await response.json();

                    if (data.status === 'success') {
                        // Clear form
                        document.getElementById('add-analysis-form').style.display = 'none';
                        document.getElementById('new-analysis-form').reset();
                        loadAnalysisTypes();
                    } else {
                        alert('Error saving analysis type: ' + data.error);
                    }
                } catch (error) {
                    alert('Error: ' + error.message);
                }
            }

            function displayProviders(data) {
                const container = document.getElementById('providers-container');

                if (!data.providers || data.providers.length === 0) {
                    container.innerHTML = '<div class="error">No AI providers configured</div>';
                    return;
                }

                let html = '';

                if (data.active_provider) {
                    html += `<div class="alert alert-success">
                        <strong>✅ Active Provider:</strong> ${data.active_provider}
                    </div>`;
                } else {
                    html += `<div class="alert alert-error">
                        <strong>❌ No AI providers available</strong><br>
                        Please install and configure Ollama or Gemini CLI below.
                    </div>`;
                }

                data.providers.forEach(provider => {
                    const isAvailable = provider.available;
                    const statusClass = isAvailable ? 'provider-available' : 'provider-unavailable';
                    const badgeClass = isAvailable ? 'status-available' : 'status-unavailable';
                    const statusText = isAvailable ? 'Available' : 'Unavailable';

                    html += `
                        <div class="provider-card ${statusClass}">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <h3 style="margin: 0;">${provider.name}</h3>
                                <span class="status-badge ${badgeClass}">${statusText}</span>
                            </div>
                            <dl class="provider-details">
                                <dt>Type:</dt>
                                <dd>${provider.type === 'local' ? '🏠 Local' : '🌐 External'}</dd>
                                ${provider.host ? `<dt>Host:</dt><dd>${provider.host}</dd>` : ''}
                                ${provider.model ? `<dt>Current Model:</dt><dd>${provider.model} ${provider.current_model_loaded ? '✅' : '⏸️'}</dd>` : ''}
                                ${provider.command ? `<dt>Command:</dt><dd>${provider.command}</dd>` : ''}

                                ${provider.type === 'local' && provider.available ? `
                                    <dt>Memory Usage:</dt>
                                    <dd>📊 ${provider.total_vram_usage_gb || 0} GB VRAM (${provider.loaded_models_count || 0} models loaded)</dd>

                                    ${provider.loaded_models && provider.loaded_models.length > 0 ? `
                                        <dt>Loaded Models:</dt>
                                        <dd>
                                            ${provider.loaded_models.map(model => `
                                                <div style="background: #f8f9fa; padding: 8px; margin: 4px 0; border-radius: 3px; border-left: 3px solid ${model.is_current_model ? '#28a745' : '#6c757d'};">
                                                    <strong>${model.name}</strong> ${model.is_current_model ? '🎯' : ''}
                                                    <br><small>📏 ${model.parameter_size} | 💾 ${model.size_vram_gb}GB VRAM | 🔧 ${model.quantization || 'N/A'} | 📝 ${(model.context_length / 1000).toFixed(0)}K context</small>
                                                </div>
                                            `).join('')}
                                        </dd>
                                    ` : ''}

                                    <dt>Available Models:</dt>
                                    <dd>📦 ${provider.total_available_models || 0} models (${provider.total_models_size_gb || 0} GB total)</dd>
                                ` : ''}

                                ${provider.available_models && provider.type !== 'local' ? `<dt>Available Models:</dt><dd>${provider.available_models.join(', ') || 'None'}</dd>` : ''}
                            </dl>
                        </div>
                    `;
                });

                container.innerHTML = html;
            }

            async function preloadModel() {
                const host = document.getElementById('ollama-host').value;
                const model = document.getElementById('ollama-model').value;
                if (!host || !model) {
                    document.getElementById('config-message').innerHTML = '<div class="alert alert-error">Please configure Ollama host and select a model first</div>';
                    return;
                }

                const messageDiv = document.getElementById('config-message');
                messageDiv.innerHTML = '<div class="alert alert-info">🚀 Loading model... This may take several minutes for large models.</div>';

                try {
                    const response = await fetch(`/api/ollama-preload?host=${encodeURIComponent(host)}&model=${encodeURIComponent(model)}`);
                    const data = await response.json();

                    if (data.status === 'success') {
                        messageDiv.innerHTML = `<div class="alert alert-success">✅ Model ${model} loaded successfully!</div>`;
                    } else {
                        messageDiv.innerHTML = `<div class="alert alert-error">❌ Failed to load model: ${data.error}</div>`;
                    }
                } catch (error) {
                    messageDiv.innerHTML = `<div class="alert alert-error">❌ Error loading model: ${error.message}</div>`;
                }
            }
        """

    def render_content(self, query: Dict[str, Any]) -> str:
        """Render settings with tabbed interface."""
        # Get the active tab from query params
        tab = query.get('tab', ['setup'])[0]

        status = self.setup_service.get_setup_status()
        ai_status = get_ai_status()

        # Load AI status on page load if AI tab is active
        ai_init_script = """
            <script>
                window.addEventListener('DOMContentLoaded', function() {
                    refreshAIStatus();
                });
            </script>
        """ if tab == 'ai-config' else ""

        return f"""
            <!-- Tab Navigation -->
            <div class="tabs">
                <button class="tab-btn {'active' if tab == 'setup' else ''}" onclick="switchTab('setup')">Setup</button>
                <button class="tab-btn {'active' if tab == 'ai-config' else ''}" onclick="switchTab('ai-config')">AI Configuration</button>
                <button class="tab-btn {'active' if tab == 'analysis-types' else ''}" onclick="switchTab('analysis-types')">AI Analysis Types</button>
            </div>

            <!-- Setup Tab -->
            <div id="setup-tab" class="tab-content {'active' if tab == 'setup' else ''}">
                <!-- Status Card -->
                <div class="card">
                    <h3>System Status</h3>
                    <div class="user-item">
                        <div class="user-name">
                            <span class="status-indicator {'status-good' if status['signal_cli_available'] else 'status-error'}"></span>
                            Signal CLI
                        </div>
                        <div class="user-details">
                            Path: {status['signal_cli_path']}<br>
                            Status: {'Available' if status['signal_cli_available'] else 'Not Available'}
                        </div>
                    </div>

                    <div class="user-item">
                        <div class="user-name">
                            <span class="status-indicator {'status-good' if status['bot_configured'] else 'status-warning'}"></span>
                            Bot Configuration
                        </div>
                        <div class="user-details">
                            Phone: {status.get('bot_phone_number', 'Not configured')}<br>
                            UUID: {status.get('bot_uuid', 'Not configured')[:8] + '...' if status.get('bot_uuid') else 'Not configured'}<br>
                            {'Registered' if status['device_registered'] else 'Not registered'}
                        </div>
                    </div>

                    <div class="user-item">
                        <div class="user-name">
                            <span class="status-indicator {'status-good' if status['groups_synced'] else 'status-warning'}"></span>
                            Groups
                        </div>
                        <div class="user-details">
                            Total: {status['total_groups']}<br>
                            Monitored: {status['monitored_groups']}
                        </div>
                    </div>

                    <div class="user-item">
                        <div class="user-name">
                            <span class="status-indicator {'status-good' if status['total_users'] > 0 else 'status-warning'}"></span>
                            Users
                        </div>
                        <div class="user-details">
                            Total: {status['total_users']}<br>
                            Configured: {status['configured_users']}<br>
                            Discovered: {status['discovered_users']}
                        </div>
                    </div>
                </div>

                <!-- Actions Card -->
                <div class="card">
                    <h3>Actions</h3>
                    <div style="display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 15px;">
                        <button id="run-setup" class="btn btn-primary" onclick="runSetup()">Run Setup</button>
                        <button id="sync-groups" class="btn btn-secondary" onclick="syncGroups()">Sync Groups</button>
                        <button id="sync-users" class="btn btn-secondary" onclick="syncUsers()">Sync Users</button>
                        <button id="clean-import" class="btn btn-warning" onclick="cleanImport()">Clean Import</button>
                    </div>
                    <pre id="setup-output" style="background: #f8f9fa; padding: 10px; border-radius: 5px; min-height: 100px;"></pre>
                </div>
            </div>

            <!-- AI Config Tab -->
            <div id="ai-config-tab" class="tab-content {'active' if tab == 'ai-config' else ''}">
                <!-- Ollama Card -->
                <div class="card">
                    <h3>🏠 Ollama (Local AI - Recommended)</h3>
                    <p style="color: #666; margin-bottom: 15px;">Run AI models locally for privacy and faster responses. No internet required.</p>

                    <div class="form-group">
                        <label for="ollama-host">Server URL:</label>
                        <input type="text" id="ollama-host" class="form-control" placeholder="http://192.168.10.160:11434" style="width: 350px;">
                        <button onclick="testOllama()" class="btn btn-secondary" style="margin-left: 10px;">Test Connection</button>
                    </div>

                    <div class="form-group">
                        <label for="ollama-model">AI Model:</label>
                        <select id="ollama-model" class="form-control" style="width: 250px;">
                            <option value="">Select a model...</option>
                        </select>
                        <small style="display: block; color: #666; margin-top: 5px;">Available models will load after entering a valid server URL</small>
                    </div>

                    <div class="form-group">
                        <label>
                            <input type="checkbox" id="ollama-enabled" style="margin-right: 8px;">
                            Enable Ollama Provider
                        </label>
                    </div>
                </div>

                <!-- Gemini Card -->
                <div class="card">
                    <h3>🌐 Gemini (External AI)</h3>
                    <p style="color: #666; margin-bottom: 15px;">Use Google's Gemini AI service. Requires internet connection and API key setup.</p>

                    <div class="form-group">
                        <label for="gemini-path">CLI Command Path:</label>
                        <input type="text" id="gemini-path" class="form-control" value="gemini" style="width: 250px;">
                        <small style="display: block; color: #666; margin-top: 5px;">Path to the gemini CLI command (usually just "gemini")</small>
                    </div>

                    <div class="form-group">
                        <label>
                            <input type="checkbox" id="gemini-enabled" style="margin-right: 8px;">
                            Enable Gemini Provider
                        </label>
                    </div>
                </div>

                <!-- Actions -->
                <div class="card">
                    <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                        <button class="btn btn-primary" onclick="saveAIConfiguration()">💾 Save Configuration</button>
                        <button class="btn btn-secondary" onclick="preloadModel()">🚀 Preload Selected Model</button>
                        <button class="btn btn-secondary" onclick="refreshAIStatus()">🔄 Refresh Status</button>
                    </div>
                    <div id="config-message" style="margin-top: 15px;"></div>
                </div>

                <!-- Provider Status -->
                <div class="card">
                    <h3>Provider Status</h3>
                    <div id="providers-container">
                        <div class="loading" style="text-align: center; padding: 40px; color: #666;">
                            Loading AI provider status...
                        </div>
                    </div>
                </div>
            </div>

            <!-- AI Analysis Types Tab -->
            <div id="analysis-types-tab" class="tab-content {'active' if tab == 'analysis-types' else ''}">
                <!-- Add New Type -->
                <div class="card">
                    <h3>AI Analysis Types</h3>
                    <p style="color: #666; margin-bottom: 15px;">Configure custom AI analysis types for processing your messages.</p>

                    <button class="btn btn-primary" onclick="showAddAnalysisType()" style="margin-bottom: 15px;">
                        Add New Analysis Type
                    </button>

                    <!-- Add Form (Hidden by default) -->
                    <div id="add-analysis-form" style="display: none; border: 1px solid #dee2e6; padding: 20px; border-radius: 8px; background: #f8f9fa; margin-bottom: 20px;">
                        <h4>New Analysis Type</h4>
                        <form id="new-analysis-form">
                            <div class="form-group">
                                <label for="new-type-name">Internal Name*:</label>
                                <input type="text" id="new-type-name" class="form-control" placeholder="e.g., weekly_report" required style="width: 300px;">
                                <small style="color: #666;">Unique identifier, no spaces</small>
                            </div>

                            <div class="form-group">
                                <label for="new-type-display">Display Name*:</label>
                                <input type="text" id="new-type-display" class="form-control" placeholder="e.g., Weekly Report" required style="width: 300px;">
                            </div>

                            <div class="form-group">
                                <label for="new-type-icon">Icon:</label>
                                <input type="text" id="new-type-icon" class="form-control" placeholder="e.g., 📊" value="🤖" style="width: 100px;">
                            </div>

                            <div class="form-group">
                                <label for="new-type-description">Description:</label>
                                <textarea id="new-type-description" class="form-control" rows="2" placeholder="Brief description of what this analysis does" style="width: 100%;"></textarea>
                            </div>

                            <div class="form-group">
                                <label for="new-type-prompt">Prompt Template*:</label>
                                <textarea id="new-type-prompt" class="form-control" rows="8" required style="width: 100%; font-family: monospace; font-size: 0.9em;"
                                          placeholder="Analyze the following messages from {{group_name}}:&#10;&#10;Time Period: Last {{hours}} hours&#10;Message Count: {{message_count}}&#10;&#10;Messages:&#10;{{messages}}&#10;&#10;Please provide..."></textarea>
                                <small style="color: #666;">Available placeholders: {{group_name}}, {{hours}}, {{message_count}}, {{messages}}</small>
                            </div>

                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                                <div class="form-group">
                                    <label for="new-type-min-messages">Minimum Messages:</label>
                                    <input type="number" id="new-type-min-messages" class="form-control" value="5" min="1" style="width: 100px;">
                                </div>

                                <div class="form-group">
                                    <label for="new-type-max-hours">Max Hours Back:</label>
                                    <input type="number" id="new-type-max-hours" class="form-control" value="168" min="1" style="width: 100px;">
                                </div>
                            </div>

                            <div class="form-group">
                                <label>
                                    <input type="checkbox" id="new-type-requires-group" checked>
                                    Requires group selection
                                </label>
                            </div>

                            <div class="form-group">
                                <label>
                                    <input type="checkbox" id="new-type-requires-sender">
                                    Requires sender filter
                                </label>
                            </div>

                            <div style="display: flex; gap: 10px;">
                                <button type="button" class="btn btn-primary" onclick="saveNewAnalysisType()">Save</button>
                                <button type="button" class="btn btn-secondary" onclick="document.getElementById('add-analysis-form').style.display='none';">Cancel</button>
                            </div>
                        </form>
                    </div>
                </div>

                <!-- Existing Types List -->
                <div class="card">
                    <h3>Configured Analysis Types</h3>
                    <div id="analysis-types-list">
                        <div class="loading">Loading analysis types...</div>
                    </div>
                </div>
            </div>

            <!-- Initialize scripts based on active tab -->
            {ai_init_script}
            {'<script>window.addEventListener("DOMContentLoaded", function() {{ loadAnalysisTypes(); }});</script>' if tab == 'analysis-types' else ''}
        """