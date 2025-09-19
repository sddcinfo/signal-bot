"""
Setup page for Signal Bot web interface.
"""

from typing import Dict, Any
from ..shared.base_page import BasePage


class SetupPage(BasePage):
    @property
    def title(self) -> str:
        return "⚙️ Signal Bot Setup"

    @property
    def nav_key(self) -> str:
        return "setup"

    @property
    def subtitle(self) -> str:
        return "Configure and initialize your Signal bot"

    def get_custom_js(self) -> str:
        return """
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
                            output.innerHTML += `<p>Scan this QR code with your Signal app to link this device:</p>`;

                            if (result.linking_qr.qr_code) {
                                output.innerHTML += `<div style="text-align: center; margin: 20px 0;"><img src="${result.linking_qr.qr_code}" alt="QR Code" style="max-width: 300px; border: 1px solid #ccc; display: block; margin: 0 auto;"></div>`;
                            } else {
                                output.innerHTML += `<p><strong>Error:</strong> QR code not generated</p>`;
                            }

                            if (result.linking_qr.linking_uri) {
                                output.innerHTML += `<p><strong>Link URI:</strong> <code style="word-break: break-all;">${result.linking_qr.linking_uri}</code></p>`;
                            }

                            output.innerHTML += `<p><em>After scanning with your Signal app, the setup will automatically complete. This page will refresh when done.</em></p>`;
                        } else if (result.success) {
                            output.textContent += '\\nSetup completed successfully! Refreshing page...';
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
                        output.textContent += 'Sync completed! Refreshing page...';
                        setTimeout(() => location.reload(), 2000);
                    } catch (error) {
                        output.textContent += `Error: ${error.message}\\n`;
                    } finally {
                        btn.disabled = false;
                        btn.textContent = 'Sync Groups';
                    }
                }

                async function cleanImport() {
                    const btn = document.getElementById('clean-import');
                    const output = document.getElementById('setup-output');

                    if (!confirm('This will clear all users and group memberships, then reimport clean data from Signal CLI. User reactions and monitored group settings will be preserved. Continue?')) {
                        return;
                    }

                    btn.disabled = true;
                    btn.textContent = 'Importing...';
                    output.textContent = 'Starting clean import...\\n';

                    try {
                        const response = await fetch('/api/setup/clean-import', { method: 'POST' });
                        const result = await response.json();

                        if (result.success) {
                            output.textContent += `Import completed successfully!\\n`;
                            output.textContent += `Contacts imported: ${result.contacts_imported}\\n`;
                            output.textContent += `Groups synced: ${result.groups_synced}\\n`;
                            if (result.reactions_restored) {
                                output.textContent += `User reactions restored: ${result.reactions_restored}\\n`;
                            }
                            output.textContent += 'Refreshing page...';
                            setTimeout(() => location.reload(), 2000);
                        } else {
                            output.textContent += `Import failed: ${result.error || 'Unknown error'}\\n`;
                        }
                    } catch (error) {
                        output.textContent += `Error: ${error.message}\\n`;
                    } finally {
                        btn.disabled = false;
                        btn.textContent = 'Clean Import Contacts & Groups';
                    }
                }
        """

    def render_content(self, query: Dict[str, Any]) -> str:
        status = self.setup_service.get_setup_status()

        return f"""
            <div class="setup-step {'step-complete' if status['signal_cli_available'] else 'step-pending'}">
                <h3>
                    <span class="status-indicator {'status-good' if status['signal_cli_available'] else 'status-error'}"></span>
                    Signal CLI Detection
                </h3>
                <p>Path: {status['signal_cli_path']}</p>
                <p>Status: {'Available' if status['signal_cli_available'] else 'Not Available'}</p>
            </div>

            <div class="setup-step {'step-complete' if status['bot_configured'] else 'step-pending'}">
                <h3>
                    <span class="status-indicator {'status-good' if status['bot_configured'] else 'status-warning'}"></span>
                    Bot Configuration
                </h3>
                <p>Phone: {status.get('bot_phone_number', 'Not configured')}</p>
                <p>UUID: {status.get('bot_uuid', 'Not configured')}</p>
            </div>

            <div class="setup-step {'step-complete' if status['total_groups'] > 0 else 'step-pending'}">
                <h3>
                    <span class="status-indicator {'status-good' if status['total_groups'] > 0 else 'status-warning'}"></span>
                    Group Discovery
                </h3>
                <p>Total Groups: {status['total_groups']}</p>
                <p>Monitored: {status['monitored_groups']}</p>
            </div>

            <div class="setup-step {'step-complete' if status['total_users'] > 0 else 'step-pending'}">
                <h3>
                    <span class="status-indicator {'status-good' if status['total_users'] > 0 else 'status-warning'}"></span>
                    User Discovery
                </h3>
                <p>Total Users: {status['total_users']}</p>
                <p>Configured: {status['configured_users']}</p>
                <p>Discovered: {status['discovered_users']}</p>
            </div>

            <button id="run-setup" class="btn" onclick="runSetup()">
                {'Re-run Setup' if status['bot_configured'] else 'Run Initial Setup'}
            </button>

            <button id="sync-groups" class="btn" onclick="syncGroups()" style="margin-left: 10px;">
                Sync Groups
            </button>

            <button id="clean-import" class="btn" onclick="cleanImport()" style="margin-left: 10px;">
                Clean Import Contacts & Groups
            </button>

            <div id="setup-output"></div>
        """

    def get_custom_css(self) -> str:
        """Setup-specific CSS - all core styles are in shared templates."""
        return ""