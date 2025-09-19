"""
Shared template system for Signal Bot web interface.

Provides consistent HTML structure and CSS across all pages - exactly matching original.
"""

from typing import Optional


def get_standard_css() -> str:
    """Get the exact original CSS used across all pages."""
    return """
                * { box-sizing: border-box; margin: 0; padding: 0; }
                body {
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: #333;
                    min-height: 100vh;
                    padding: 20px;
                }
                .container { max-width: 1200px; margin: 0 auto; }
                .card {
                    background: white;
                    border-radius: 15px;
                    padding: 30px;
                    margin-bottom: 30px;
                    box-shadow: 0 8px 25px rgba(0,0,0,0.1);
                }
                /* Compact header card styling */
                .header-card {
                    background: linear-gradient(135deg, white 0%, #f8f9fa 100%);
                    padding: 20px 25px;
                }
                .header-card h1 {
                    font-size: 1.8em;
                    margin-bottom: 5px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    font-weight: 700;
                    letter-spacing: -0.5px;
                }
                .header-card p {
                    font-size: 1em;
                    color: #6c757d;
                    margin-bottom: 15px;
                }
                .nav {
                    display: flex;
                    gap: 12px;
                    justify-content: center;
                    margin-top: 15px;
                    padding: 10px;
                    margin-top: 25px;
                    margin-bottom: 0;
                    flex-wrap: wrap;
                    padding: 15px;
                    background: #f8f9fa;
                    border-radius: 12px;
                }
                .nav-item {
                    padding: 12px 24px;
                    background: white;
                    border-radius: 25px;
                    text-decoration: none;
                    color: #495057;
                    font-weight: 600;
                    font-size: 0.95em;
                    transition: all 0.3s ease;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
                    position: relative;
                    overflow: hidden;
                }
                .nav-item:before {
                    content: "";
                    position: absolute;
                    top: 0;
                    left: -100%;
                    width: 100%;
                    height: 100%;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    transition: left 0.3s ease;
                    z-index: -1;
                }
                .nav-item:hover {
                    transform: translateY(-3px);
                    box-shadow: 0 6px 20px rgba(0,0,0,0.12);
                    color: #667eea;
                }
                .nav-item.active {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
                }
                .nav-item.active:hover {
                    transform: translateY(-3px);
                    box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
                    color: white;
                }
                table { width: 100%; border-collapse: collapse; margin-top: 20px; }
                th, td { padding: 12px; text-align: left; border-bottom: 1px solid #dee2e6; }
                th { background: #f8f9fa; font-weight: 600; }
                .btn {
                    padding: 8px 16px;
                    border: none;
                    border-radius: 5px;
                    background: #007bff;
                    color: white;
                    cursor: pointer;
                    transition: background 0.3s;
                    margin-right: 5px;
                    text-decoration: none;
                    display: inline-block;
                    font-size: 14px;
                    font-weight: normal;
                    line-height: 1.5;
                }
                .btn:hover { background: #0056b3; }
                .btn-danger { background: #dc3545; }
                .btn-danger:hover { background: #c82333; }
                .btn-success { background: #28a745; }
                .btn-success:hover { background: #218838; }
                .btn-warning { background: #ffc107; color: #212529; }
                .btn-warning:hover { background: #e0a800; }
                .btn-secondary { background: #6c757d; }
                .btn-secondary:hover { background: #5a6268; }
                .text-muted { color: #6c757d; }
                /* Form elements */
                .form-group { margin-bottom: 20px; }
                .form-group label { display: block; margin-bottom: 5px; font-weight: 500; }
                .form-group input, .form-group select, .form-group textarea {
                    width: 100%;
                    padding: 12px;
                    border: 1px solid #dee2e6;
                    border-radius: 5px;
                    font-size: 14px;
                }
                .form-group input:focus, .form-group select:focus, .form-group textarea:focus {
                    outline: none;
                    border-color: #007bff;
                    box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.25);
                }
                /* Status and alerts */
                .alert {
                    padding: 12px 20px;
                    border-radius: 5px;
                    margin-bottom: 20px;
                }
                .alert-success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
                .alert-error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
                .alert-warning { background: #fff3cd; color: #856404; border: 1px solid #ffeaa7; }
                .alert-info { background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }
                /* Loading states */
                .loading {
                    text-align: center;
                    padding: 40px;
                    color: #6c757d;
                }
                /* Message displays */
                .messages-container { margin-top: 20px; }
                .message-item {
                    border: 1px solid #dee2e6;
                    border-radius: 8px;
                    margin-bottom: 12px;
                    padding: 12px;
                    background: white;
                }
                .message-header {
                    margin-bottom: 10px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    flex-wrap: wrap;
                }
                .message-time, .timestamp {
                    color: #6c757d;
                    font-size: 0.85em;
                }
                .message-content {
                    line-height: 1.4;
                    white-space: pre-wrap;
                    word-wrap: break-word;
                }
                .no-messages {
                    text-align: center;
                    color: #6c757d;
                    font-style: italic;
                    padding: 40px 20px;
                    background: white;
                    border-radius: 8px;
                    border: 2px dashed #dee2e6;
                }
                /* Enhanced message styling */
                .messages-container {
                    background: #f8f9fa;
                    border-radius: 8px;
                    padding: 12px;
                }
                .message-item {
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                    padding: 12px;
                    margin-bottom: 12px;
                }
                .message-header {
                    border-bottom: 1px solid #f0f0f0;
                    padding-bottom: 8px;
                }
                .message-sender {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    flex-wrap: wrap;
                }
                .group-indicator {
                    color: #6c757d;
                    font-style: italic;
                    font-size: 0.9em;
                }
                .group-name {
                    color: #007bff;
                }
                .message-text {
                    margin-top: 8px;
                }
                .attachments {
                    margin-top: 12px;
                    padding: 8px;
                    background: #f8f9fa;
                    border-radius: 6px;
                    border-left: 3px solid #007bff;
                }
                .attachment-image {
                    max-width: 200px;
                    max-height: 200px;
                    border-radius: 6px;
                    margin: 5px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
                    cursor: pointer;
                    transition: transform 0.2s;
                }
                .attachment-image:hover {
                    transform: scale(1.05);
                }
                .attachment-video {
                    max-width: 200px;
                    max-height: 200px;
                    border-radius: 6px;
                    margin: 5px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
                    cursor: pointer;
                    transition: transform 0.2s;
                }
                .attachment-video:hover {
                    transform: scale(1.05);
                }
                .mention {
                    background: #e3f2fd;
                    color: #1976d2;
                    padding: 2px 6px;
                    border-radius: 12px;
                    font-weight: 500;
                    font-size: 0.9em;
                    border: 1px solid #bbdefb;
                }
                .attachment-file {
                    padding: 8px 12px;
                    background: #e9ecef;
                    border-radius: 4px;
                    margin: 4px 0;
                    color: #495057;
                    border-left: 3px solid #6c757d;
                }
                /* Pagination */
                .pagination {
                    display: flex;
                    justify-content: center;
                    gap: 10px;
                    margin-top: 20px;
                    flex-wrap: wrap;
                }
                .pagination > * {
                    flex: 0 0 auto;
                }
                .user-tabs, .tabs {
                    display: flex;
                    gap: 5px;
                    margin-bottom: 20px;
                    border-bottom: 2px solid #f0f0f0;
                    padding-bottom: 10px;
                    flex-wrap: wrap;
                }
                .tab-btn {
                    padding: 10px 20px;
                    border: none;
                    background: #f8f9fa;
                    color: #495057;
                    cursor: pointer;
                    border-radius: 20px 20px 0 0;
                    transition: all 0.3s;
                    text-decoration: none;
                    display: inline-block;
                }
                .tab-btn:hover { background: #e9ecef; }
                .tab-btn.active {
                    background: #007bff;
                    color: white;
                }
                .tab-content {
                    display: none;
                }
                .tab-content.active {
                    display: block;
                }
                /* Ensure consistent opaque backgrounds for tab content cards */
                .tab-content .card {
                    background: white;
                    padding: 20px;
                }
                /* Tab content styling */
                .reactions-container {
                    background: #f8f9fa;
                    border-radius: 8px;
                    padding: 15px;
                    margin-bottom: 20px;
                }
                .emoji-selector {
                    display: flex;
                    gap: 10px;
                    flex-wrap: wrap;
                    margin-bottom: 15px;
                }
                .emoji-btn {
                    font-size: 1.5em;
                    padding: 5px 10px;
                    border: 2px solid #dee2e6;
                    border-radius: 25px;
                    background: white;
                    cursor: pointer;
                    transition: all 0.3s;
                }
                .emoji-btn:hover, .emoji-btn.selected {
                    border-color: #007bff;
                    background: #e7f1ff;
                }
                .emoji-display {
                    font-size: 1.2em;
                    margin-right: 5px;
                }
                .user-item {
                    border: 1px solid #dee2e6;
                    border-radius: 8px;
                    padding: 15px;
                    margin-bottom: 10px;
                    background: white;
                    transition: box-shadow 0.3s;
                }
                .user-item:hover {
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                }
                .user-name {
                    font-weight: bold;
                    margin-bottom: 5px;
                }
                .user-details {
                    color: #6c757d;
                    font-size: 0.9em;
                    margin-bottom: 10px;
                }
                .user-actions {
                    display: flex;
                    gap: 10px;
                    flex-wrap: wrap;
                }
                .emoji-badge {
                    display: inline-block;
                    padding: 5px 10px;
                    margin: 4px;
                    background: #e9ecef;
                    border-radius: 15px;
                    cursor: pointer;
                    font-size: 1.2em;
                    border: 1px solid #dee2e6;
                    transition: all 0.2s;
                }
                .emoji-badge:hover {
                    background: #dc3545;
                    color: white;
                    transform: scale(1.1);
                }
                .groups-list {
                    font-size: 0.9em;
                    color: #6c757d;
                    line-height: 1.4;
                }

                /* Modal CSS for emoji picker */
                .modal {
                    display: none;
                    position: fixed;
                    z-index: 1000;
                    left: 0;
                    top: 0;
                    width: 100%;
                    height: 100%;
                    background-color: rgba(0, 0, 0, 0.5);
                }
                .modal-content {
                    background-color: #ffffff;
                    margin: 5% auto;
                    padding: 25px;
                    border-radius: 10px;
                    width: 90%;
                    max-width: 600px;
                    max-height: 80vh;
                    overflow-y: auto;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                    position: relative;
                }
                .close {
                    color: #aaa;
                    float: right;
                    font-size: 28px;
                    font-weight: bold;
                    cursor: pointer;
                }
                .close:hover { color: black; }
                .emoji-grid {
                    display: grid;
                    grid-template-columns: repeat(8, 1fr);
                    gap: 5px;
                    margin: 20px 0;
                }
                .emoji-item {
                    padding: 10px;
                    text-align: center;
                    cursor: pointer;
                    border-radius: 5px;
                    font-size: 1.5em;
                }
                .emoji-item:hover { background: #f0f0f0; }
                .emoji-item.selected { background: #007bff; color: white; }
                .selected-emojis {
                    border: 2px solid #dee2e6;
                    border-radius: 8px;
                    padding: 15px;
                    margin: 15px 0;
                    min-height: 60px;
                    background: #f8f9fa;
                    display: flex;
                    flex-wrap: wrap;
                    gap: 5px;
                    align-items: center;
                }
                .selected-emojis:empty::after {
                    content: "Click emojis below to add them here";
                    color: #6c757d;
                    font-style: italic;
                }

                /* Stats and metrics */
                .stats {
                    display: flex;
                    justify-content: space-between;
                    margin-bottom: 20px;
                    flex-wrap: wrap;
                    gap: 10px;
                }
                .stats > div {
                    flex: 1;
                    min-width: 200px;
                }
                .stat-card {
                    background: white;
                    border-radius: 10px;
                    padding: 20px;
                    text-align: center;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }
                .stat-number { font-size: 2em; font-weight: bold; color: #007bff; }
                .stat-label { margin-top: 5px; color: #666; }

                /* Setup page styles */
                .setup-steps { margin: 30px 0; }
                .setup-step { padding: 20px; margin-bottom: 15px; border-radius: 8px; border-left: 4px solid #ddd; }
                .setup-step.step-complete { background: #d4edda; border-color: #c3e6cb; }
                .setup-step.step-pending { background: #fff3cd; border-color: #ffeaa7; }
                .status-indicator {
                    display: inline-block;
                    width: 12px;
                    height: 12px;
                    border-radius: 50%;
                    margin-right: 8px;
                }
                .status-good { background: #28a745; }
                .status-warning { background: #ffc107; }
                .status-error { background: #dc3545; }
                .setup-actions { margin: 30px 0; }
                .setup-status { margin: 30px 0; }
                .setup-status ul { list-style: none; padding: 0; }
                .setup-status li { padding: 5px 0; }
                .setup-output, #setup-output {
                    background: #f8f9fa;
                    border: 1px solid #dee2e6;
                    border-radius: 5px;
                    padding: 15px;
                    min-height: 100px;
                    font-family: monospace;
                    white-space: pre-wrap;
                    margin-top: 20px;
                }
                .qr-container { text-align: center; margin: 15px 0; }
                .qr-container img { max-width: 300px; border: 1px solid #ddd; padding: 10px; }

                /* Members list */
                .members-list {
                    max-width: 300px;
                    font-size: 0.85em;
                    color: #555;
                    line-height: 1.4;
                    word-wrap: break-word;
                }

                /* Messages page styles */
                .back-btn {
                    background: #6c757d;
                    color: white;
                }
                .back-btn:hover { background: #5a6268; }
                .page-btn {
                    padding: 8px 12px;
                    text-decoration: none;
                    background: #f8f9fa;
                    color: #495057;
                    border-radius: 5px;
                    transition: background 0.3s;
                }
                .page-btn:hover { background: #e9ecef; }
                .page-btn.current {
                    background: #007bff;
                    color: white;
                }

                /* Attachments */
                .attachment {
                    margin-top: 10px;
                    padding: 10px;
                    background: #f8f9fa;
                    border-radius: 5px;
                    border-left: 3px solid #007bff;
                }
                /* Hide all tabs initially except first */
                .tabs-content > div { display: none; }
                .tabs-content > div:first-child { display: block; }
                .tabs-content > div.active { display: block; }

                /* Responsive design adjustments */
                @media (max-width: 768px) {
                    .nav { gap: 5px; }
                    .nav-item { padding: 8px 12px; font-size: 0.8em; }
                    .container { padding: 10px; }
                    .card { padding: 20px; }
                    .stats { flex-direction: column; }
                    .message-header { flex-direction: column; align-items: flex-start; gap: 5px; }
                    table, thead, tbody, th, td, tr { display: block; }
                    thead tr { position: absolute; top: -9999px; left: -9999px; }
                    tr { border: 1px solid #ccc; margin-bottom: 10px; }
                    td { border: none; position: relative; padding-left: 50%; }
                    td:before {
                        content: attr(data-label) ": ";
                        position: absolute;
                        left: 6px;
                        width: 45%;
                        padding-right: 10px;
                        white-space: nowrap;
                        font-weight: bold;
                    }
                }

                /* Additional styles for AI and analysis pages */
                .provider-card {
                    background: #f8f9fa;
                    border: 1px solid #e9ecef;
                    border-radius: 8px;
                    padding: 20px;
                    margin-bottom: 20px;
                }
                .provider-available { border-left: 4px solid #28a745; }
                .provider-unavailable { border-left: 4px solid #dc3545; }
                .status-badge {
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 12px;
                    font-weight: bold;
                    text-transform: uppercase;
                }
                .status-available { background: #d4edda; color: #155724; }
                .status-unavailable { background: #f8d7da; color: #721c24; }
                .provider-details { margin-top: 15px; }
                .provider-details dt { font-weight: bold; margin-top: 10px; }
                .provider-details dd { margin-left: 20px; color: #666; }
                .refresh-btn {
                    background: #007cba;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 4px;
                    cursor: pointer;
                }
                .refresh-btn:hover { background: #005a87; }

                /* Analysis result styling */
                .analysis-result, .summary-result {
                    background: #f8f9fa;
                    border: 1px solid #e9ecef;
                    border-radius: 8px;
                    padding: 20px;
                    margin-top: 20px;
                    line-height: 1.6;
                }
                .analysis-result h1, .analysis-result h2, .analysis-result h3,
                .summary-result h1, .summary-result h2, .summary-result h3 {
                    color: #495057;
                    margin-top: 20px;
                    margin-bottom: 10px;
                }
                .analysis-result h1, .summary-result h1 { font-size: 1.5em; }
                .analysis-result h2, .summary-result h2 { font-size: 1.3em; }
                .analysis-result h3, .summary-result h3 { font-size: 1.1em; }

                /* Filters styling */
                .filters {
                    background: #f8f9fa;
                    padding: 15px;
                    border-radius: 8px;
                    margin-bottom: 20px;
                    border: 1px solid #e9ecef;
                }
                .filters label {
                    margin-right: 15px;
                    font-weight: 500;
                }
                .filters select, .filters input {
                    margin-left: 5px;
                    padding: 5px 10px;
                    border: 1px solid #dee2e6;
                    border-radius: 4px;
                }

                /* Status indicators */
                .status {
                    padding: 4px 8px;
                    border-radius: 12px;
                    font-size: 0.9em;
                    font-weight: 500;
                }
                .status.active {
                    background: #d4edda;
                    color: #155724;
                }
                .status.inactive {
                    background: #f8d7da;
                    color: #721c24;
                }

                /* Activity Chart Styles */
                .activity-filters {
                    background: white;
                    padding: 20px;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    margin-bottom: 20px;
                }
                .filter-row {
                    display: flex;
                    gap: 20px;
                    align-items: end;
                    flex-wrap: wrap;
                }
                .filter-group {
                    display: flex;
                    flex-direction: column;
                    gap: 5px;
                }
                .filter-group label {
                    font-weight: 500;
                    color: #333;
                }
                .filter-group select,
                .filter-group input {
                    padding: 8px 12px;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    font-size: 14px;
                }
                .chart-container {
                    margin: 30px 0;
                    padding: 20px;
                    background: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }
                .chart-title {
                    text-align: center;
                    margin-bottom: 20px;
                    color: #333;
                    font-size: 18px;
                    font-weight: bold;
                }
                .bar-chart {
                    display: flex;
                    align-items: flex-end;
                    height: 220px;
                    padding: 10px;
                    gap: 2px;
                }
                .bar-container {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: flex-end;
                    flex: 1;
                    height: 100%;
                    cursor: pointer;
                }
                .bar {
                    width: 100%;
                    min-height: 2px;
                    border-radius: 2px 2px 0 0;
                    transition: all 0.3s ease;
                    margin-bottom: 5px;
                }
                .bar:hover {
                    opacity: 0.7;
                    transform: scaleY(1.1);
                }
                .bar-label {
                    font-size: 0.8em;
                    color: #666;
                    margin-top: 5px;
                }
                #activity-charts-container {
                    margin-top: 20px;
                }
                #filtered-messages-container {
                    margin-top: 30px;
                    padding: 20px;
                    background: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }
                .clickable-bar {
                    cursor: pointer;
                }
                .clickable-bar:hover {
                    opacity: 0.8;
                }
                /* Notification System */
                .notification-container {
                    position: fixed; top: 20px; right: 20px; z-index: 1000; max-width: 400px;
                }
                .notification {
                    background: white; border-radius: 8px; padding: 15px; margin-bottom: 10px;
                    box-shadow: 0 4px 15px rgba(0,0,0,0.1); border-left: 4px solid #007bff;
                    animation: slideIn 0.3s ease-out; font-size: 14px;
                }
                .notification.error { border-left-color: #dc3545; }
                .notification.warning { border-left-color: #ffc107; }
                .notification.success { border-left-color: #28a745; }
                .notification.info { border-left-color: #17a2b8; }
                .notification-close {
                    float: right; background: none; border: none; font-size: 18px; cursor: pointer;
                    color: #999; margin-left: 10px;
                }
                .notification-close:hover { color: #333; }
                @keyframes slideIn {
                    from { transform: translateX(100%); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
                @keyframes slideOut {
                    from { transform: translateX(0); opacity: 1; }
                    to { transform: translateX(100%); opacity: 0; }
                }

                /* Utility Classes for Consistent Styling */
                .content-card {
                    background: white;
                    border-radius: 12px;
                    padding: 20px;
                    margin-bottom: 20px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
                }
                .tab-container {
                    background: white;
                    border-radius: 12px;
                    overflow: hidden;
                }
                .data-table {
                    width: 100%;
                    border-collapse: collapse;
                }
                .data-table th {
                    background: #f8f9fa;
                    font-weight: 600;
                    text-align: left;
                    padding: 12px;
                    border-bottom: 2px solid #dee2e6;
                }
                .data-table td {
                    padding: 12px;
                    border-bottom: 1px solid #dee2e6;
                }
                .action-group {
                    display: flex;
                    gap: 10px;
                    flex-wrap: wrap;
                    align-items: center;
                }
                .status-badge {
                    display: inline-block;
                    padding: 4px 12px;
                    border-radius: 20px;
                    font-size: 0.85em;
                    font-weight: 500;
                }
                .status-badge.active {
                    background: #d4edda;
                    color: #155724;
                }
                .status-badge.inactive {
                    background: #f8d7da;
                    color: #721c24;
                }
                .status-badge.pending {
                    background: #fff3cd;
                    color: #856404;
                }

                /* Spacing Utilities */
                .mt-1 { margin-top: 5px; }
                .mt-2 { margin-top: 10px; }
                .mt-3 { margin-top: 15px; }
                .mt-4 { margin-top: 20px; }
                .mb-1 { margin-bottom: 5px; }
                .mb-2 { margin-bottom: 10px; }
                .mb-3 { margin-bottom: 15px; }
                .mb-4 { margin-bottom: 20px; }
                .p-1 { padding: 5px; }
                .p-2 { padding: 10px; }
                .p-3 { padding: 15px; }
                .p-4 { padding: 20px; }

                /* Flexbox Utilities */
                .flex-row {
                    display: flex;
                    flex-direction: row;
                }
                .flex-col {
                    display: flex;
                    flex-direction: column;
                }
                .gap-1 { gap: 5px; }
                .gap-2 { gap: 10px; }
                .gap-3 { gap: 15px; }
                .flex-wrap { flex-wrap: wrap; }
                .items-center { align-items: center; }
                .justify-between { justify-content: space-between; }
                .justify-center { justify-content: center; }

                /* Width Utilities */
                .w-full { width: 100%; }
                .max-w-sm { max-width: 300px; }
                .max-w-md { max-width: 500px; }
                .max-w-lg { max-width: 800px; }

                /* Text Utilities */
                .text-center { text-align: center; }
                .text-right { text-align: right; }
                .text-sm { font-size: 0.875rem; }
                .text-lg { font-size: 1.125rem; }
                .font-bold { font-weight: 600; }
                .text-muted { color: #6c757d; }
    """


def get_page_header(title: str, subtitle: str, active_page: str = '') -> str:
    """Get standardized page header with navigation for all pages - exact original structure."""
    nav_items = [
        ('/', 'Overview'),
        ('/groups', 'Groups'),
        ('/users', 'Users'),
        ('/messages', 'Messages'),
        ('/settings', 'Settings')
    ]

    nav_html = ''
    for href, label in nav_items:
        # Check if this is the active page
        is_active = ''
        if active_page == label.lower().replace(' ', '-'):
            is_active = ' active'
        elif href == '/' and active_page == 'overview':
            is_active = ' active'
        nav_html += f'<a href="{href}" class="nav-item{is_active}">{label}</a>\n'

    return f"""
            <div class="container">
                <div class="card header-card">
                    <h1>{title}</h1>
                    <p>{subtitle}</p>
                    <div class="nav">
                        {nav_html.strip()}
                    </div>
                </div>
    """


def render_page(title: str, subtitle: str, content: str, active_page: str = '', extra_css: str = '', extra_js: str = '') -> str:
    """Generate a complete standardized page with consistent structure - exact original structure."""
    return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Signal Bot - {title}</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                {get_standard_css()}
                {extra_css}
            </style>
        </head>
        <body>
            <div class="notification-container" id="notification-container"></div>
            {get_page_header(title, subtitle, active_page)}
            <div class="card">
                {content}
            </div>
            </div>
            <script>
                // Global notification system
                function showNotification(message, type = 'info', duration = 5000) {{
                    const container = document.getElementById('notification-container');
                    const notification = document.createElement('div');
                    notification.className = `notification ${{type}}`;
                    notification.innerHTML = `
                        <button class="notification-close" onclick="closeNotification(this)">&times;</button>
                        ${{message}}
                    `;

                    container.appendChild(notification);

                    // Auto-remove after duration
                    setTimeout(() => {{
                        if (notification.parentNode) {{
                            closeNotification(notification.querySelector('.notification-close'));
                        }}
                    }}, duration);
                }}

                function closeNotification(closeBtn) {{
                    const notification = closeBtn.parentNode;
                    notification.style.animation = 'slideOut 0.3s ease-out';
                    setTimeout(() => {{
                        if (notification.parentNode) {{
                            notification.parentNode.removeChild(notification);
                        }}
                    }}, 300);
                }}

                // Replace alert function globally
                window.originalAlert = window.alert;
                window.alert = function(message) {{
                    showNotification(message, 'warning');
                }};
            </script>
            {f'<script>{extra_js}</script>' if extra_js else ''}
        </body>
        </html>
        """


def get_standard_date_selector(input_id: str = "date-input",
                              label_text: str = "Select Date:",
                              button_text: str = "Load Data",
                              onclick_function: str = "loadData()",
                              auto_load: bool = True,
                              default_today: bool = True,
                              include_button: bool = True,
                              onchange_function: Optional[str] = None) -> str:
    """Get a standardized date selector component."""

    # Auto-fill today's date if requested
    auto_fill_script = """
        document.addEventListener('DOMContentLoaded', function() {
            var today = new Date();
            var todayStr = today.getFullYear() + '-' +
                String(today.getMonth() + 1).padStart(2, '0') + '-' +
                String(today.getDate()).padStart(2, '0');
            document.getElementById('""" + input_id + """').value = todayStr;
            """ + (onclick_function + "();" if auto_load else "") + """
        });
    """ if default_today else ""

    onchange_attr = f'onchange="{onchange_function}"' if onchange_function else ""

    button_html = f'<button onclick="{onclick_function}" class="btn">{button_text}</button>' if include_button else ''

    return f"""
        <div class="form-group">
            <label for="{input_id}">{label_text}</label>
            <input type="date" id="{input_id}" value="" {onchange_attr} class="form-control">
            {button_html}
        </div>
        <script>{auto_fill_script}</script>
    """