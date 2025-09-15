"""Simplified styling for the Cosmos Workflow Manager UI - Focus on functionality."""


def get_custom_css():
    """Return simplified CSS that doesn't interfere with dropdowns."""
    return """
    /* Basic color scheme */
    :root {
        --primary-color: #667eea;
        --secondary-color: #764ba2;
        --border-color: rgba(255, 255, 255, 0.1);
        --hover-color: rgba(102, 126, 234, 0.1);
    }

    /* Simple header */
    h1 {
        color: var(--primary-color);
        font-size: 2.5rem !important;
        font-weight: 800 !important;
    }

    /* Basic card styling - no transforms or complex effects */
    .gr-box, .gr-group {
        border: 1px solid var(--border-color) !important;
        border-radius: 8px !important;
    }

    /* Simple button styling - only for actual buttons, not dropdown arrows */
    button.gr-button {
        border-radius: 8px !important;
        font-weight: 600 !important;
        transition: background-color 0.2s ease !important;
    }

    button.gr-button:hover {
        opacity: 0.9;
    }

    /* Gallery styling */
    #input_gallery .thumbnail-item {
        aspect-ratio: 16 / 9 !important;
        object-fit: cover !important;
        min-height: 200px !important;
        border-radius: 8px !important;
    }

    #input_gallery .thumbnail-item:hover {
        border: 2px solid var(--primary-color) !important;
    }

    /* Tabs */
    .tab-nav button {
        font-weight: 600 !important;
        padding: 12px 24px !important;
        border-radius: 8px 8px 0 0 !important;
    }

    .tab-nav button.selected {
        background: var(--primary-color) !important;
        color: white !important;
    }

    /* Tables */
    .gr-dataframe {
        border-radius: 8px !important;
    }

    .gr-dataframe thead {
        background: rgba(102, 126, 234, 0.1) !important;
    }

    .gr-dataframe tbody tr:hover {
        background: var(--hover-color) !important;
    }

    /* Status badges */
    .status-badge {
        padding: 4px 12px;
        border-radius: 16px;
        font-size: 0.875rem;
        font-weight: 600;
        display: inline-block;
    }

    .status-running {
        background: rgba(59, 130, 246, 0.2);
        color: #3b82f6;
    }

    .status-completed {
        background: rgba(34, 197, 94, 0.2);
        color: #22c55e;
    }

    .status-failed {
        background: rgba(239, 68, 68, 0.2);
        color: #ef4444;
    }

    .status-pending {
        background: rgba(251, 191, 36, 0.2);
        color: #fbbf24;
    }

    /* Info sections */
    .info-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 12px;
        padding: 16px;
        background: rgba(0, 0, 0, 0.02);
        border-radius: 8px;
    }

    .info-item label {
        font-weight: 600;
        color: #9ca3af;
        font-size: 0.875rem;
    }

    .info-item .value {
        color: #f3f4f6;
        margin-top: 4px;
    }

    /* Split view layout */
    .split-view {
        display: flex;
        gap: 16px;
        height: calc(100vh - 200px);
    }

    .split-left {
        flex: 1.5;
    }

    .split-right {
        flex: 1;
        border-left: 1px solid var(--border-color);
        padding-left: 16px;
    }

    /* CRITICAL: Ensure dropdowns work properly */
    .gr-dropdown {
        position: relative !important;
    }

    /* Don't apply any transforms, overflow hidden, or z-index to containers with dropdowns */

    /* Log viewer */
    .log-viewer {
        font-family: 'Monaco', 'Consolas', monospace !important;
        background: #1e1e1e !important;
        color: #d4d4d4 !important;
        padding: 16px !important;
        border-radius: 8px !important;
        font-size: 13px !important;
        line-height: 1.6 !important;
    }

    /* Selection counter */
    .selection-counter {
        background: rgba(102, 126, 234, 0.1);
        padding: 8px 16px;
        border-radius: 8px;
        font-weight: 600;
    }

    /* Results counter */
    .results-counter {
        color: var(--primary-color);
        font-weight: 600;
    }

    /* Video components */
    .video-preview-container video {
        width: 100% !important;
        height: 100% !important;
        object-fit: cover !important;
    }

    /* Textbox styling */
    .detail-card input[type="text"],
    .detail-card textarea {
        font-family: 'SF Mono', 'Monaco', 'Inconsolata', monospace !important;
        background: rgba(0, 0, 0, 0.2) !important;
        border: 1px solid rgba(102, 126, 234, 0.3) !important;
    }

    .detail-card input[type="text"]:focus,
    .detail-card textarea:focus {
        border-color: var(--primary-color) !important;
        outline: none !important;
    }

    /* Loading skeleton - simple */
    .loading-skeleton {
        background: linear-gradient(90deg, #333 25%, #444 50%, #333 75%);
        background-size: 200% 100%;
    }

    /* Batch operation styling */
    .batch-operation {
        padding: 12px;
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.05), rgba(118, 75, 162, 0.05));
        border: 1px solid rgba(102, 126, 234, 0.2);
        border-radius: 8px;
        margin: 12px 0;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    /* Detail cards */
    .detail-card {
        padding: 16px;
        border-radius: 8px;
        background: rgba(0, 0, 0, 0.02);
    }

    /* Run details styling */
    .run-detail-header {
        padding: 16px;
        background: rgba(102, 126, 234, 0.1);
        border-radius: 8px;
        margin-bottom: 16px;
    }

    .params-json {
        font-family: monospace;
        white-space: pre-wrap;
        background: rgba(0, 0, 0, 0.1);
        padding: 12px;
        border-radius: 8px;
    }

    /* Remove any global overflow hidden that might affect dropdowns */
    * {
        overflow: initial;
    }

    /* Only apply overflow where specifically needed */
    .log-viewer,
    .params-json,
    pre,
    code {
        overflow: auto !important;
    }
    """
