"""Styling and theming for the Cosmos Workflow Manager UI."""

def get_custom_css():
    """Return the custom CSS for the Gradio interface."""
    return """
    /* Design System: Hierarchy, Contrast, Balance, Movement */
    :root {
        --primary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        --secondary-gradient: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        --success-gradient: linear-gradient(135deg, #00d2ff 0%, #3a7bd5 100%);
        --dark-bg: #1a1b26;
        --card-bg: rgba(255, 255, 255, 0.02);
        --border-glow: rgba(102, 126, 234, 0.5);
    }

    /* Animated header with gradient */
    h1 {
        background: var(--primary-gradient);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 2.5rem !important;
        font-weight: 800 !important;
        animation: gradientShift 6s ease infinite;
    }

    @keyframes gradientShift {
        0%, 100% { filter: hue-rotate(0deg); }
        50% { filter: hue-rotate(30deg); }
    }

    /* Card glassmorphism effects */
    .gr-box, .gr-group {
        background: var(--card-bg) !important;
        backdrop-filter: blur(10px) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }

    .gr-box:hover, .gr-group:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 30px rgba(102, 126, 234, 0.2) !important;
        border-color: var(--border-glow) !important;
    }

    /* Button animations */
    button {
        position: relative;
        overflow: hidden;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }

    button.primary, button[variant="primary"] {
        background: var(--primary-gradient) !important;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3) !important;
    }

    button:hover {
        transform: translateY(-2px) scale(1.02);
    }

    button::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
        transition: left 0.5s;
    }

    button:hover::before {
        left: 100%;
    }

    /* Gallery enhancements with hover effects */
    #input_gallery .thumbnail-item {
        aspect-ratio: 16 / 9 !important;
        object-fit: cover !important;
        min-height: 200px !important;
        border-radius: 8px !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        border: 2px solid transparent !important;
    }

    #input_gallery video {
        aspect-ratio: 16 / 9 !important;
        object-fit: cover !important;
        width: 100% !important;
        height: auto !important;
        min-height: 200px !important;
        border-radius: 8px !important;
    }

    #input_gallery .grid-container {
        gap: 20px !important;
        padding: 12px !important;
    }

    #output_gallery .thumbnail-item {
        aspect-ratio: 16 / 9 !important;
        object-fit: cover !important;
        min-height: 150px !important;
        border-radius: 8px !important;
        transition: all 0.3s !important;
    }

    #output_gallery video {
        aspect-ratio: 16 / 9 !important;
        object-fit: cover !important;
        width: 100% !important;
        height: auto !important;
        border-radius: 8px !important;
    }

    .thumbnail-item:hover {
        transform: scale(1.05);
        border-color: var(--border-glow) !important;
        box-shadow: 0 8px 20px rgba(102, 126, 234, 0.3) !important;
    }

    /* Tab styling */
    .tab-nav button.selected {
        background: var(--primary-gradient) !important;
        color: white !important;
        box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3) !important;
    }

    /* Table with hover effects */
    .dataframe tbody tr {
        transition: background 0.2s !important;
    }

    .dataframe tbody tr:hover {
        background: rgba(102, 126, 234, 0.1) !important;
    }

    /* Progress animation */
    @keyframes shimmer {
        0% { transform: translateX(-100%); }
        100% { transform: translateX(100%); }
    }

    /* Status pulse animation */
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }

    /* Interactive table rows */
    .prompts-table tr {
        cursor: pointer;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }

    .prompts-table tr:hover {
        background: linear-gradient(90deg, rgba(102, 126, 234, 0.1), rgba(118, 75, 162, 0.1)) !important;
        transform: translateX(4px);
    }

    .prompts-table tr.selected {
        background: rgba(102, 126, 234, 0.2) !important;
        border-left: 3px solid #667eea !important;
    }

    /* Checkbox animations */
    input[type="checkbox"] {
        transition: all 0.2s !important;
    }

    input[type="checkbox"]:checked {
        transform: scale(1.1);
        box-shadow: 0 0 10px rgba(102, 126, 234, 0.5) !important;
    }

    /* Staggered animations for batch operations */
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    .batch-operation {
        animation: fadeInUp 0.3s ease-out;
    }

    /* Loading skeleton */
    .loading-skeleton {
        background: linear-gradient(90deg, var(--card-bg) 25%, rgba(102, 126, 234, 0.1) 50%, var(--card-bg) 75%);
        background-size: 200% 100%;
        animation: loading 1.5s infinite;
    }

    @keyframes loading {
        0% { background-position: 200% 0; }
        100% { background-position: -200% 0; }
    }

    /* Professional detail cards */
    .detail-card {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.05), rgba(118, 75, 162, 0.05));
        border: 1px solid rgba(102, 126, 234, 0.2);
        border-radius: 12px;
        padding: 16px;
        margin: 8px 0;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }

    .detail-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 24px rgba(102, 126, 234, 0.2);
    }

    /* Split view layout */
    .split-view {
        display: flex;
        gap: 16px;
        height: calc(100vh - 200px);
    }

    .split-left {
        flex: 1.5;
        overflow-y: auto;
    }

    .split-right {
        flex: 1;
        overflow-y: auto;
        border-left: 1px solid rgba(102, 126, 234, 0.2);
        padding-left: 16px;
    }

    /* Status indicator animations */
    @keyframes statusPulse {
        0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
        70% { box-shadow: 0 0 0 10px rgba(16, 185, 129, 0); }
        100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
    }

    /* Slider enhancements */
    input[type="range"]::-webkit-slider-thumb:hover {
        transform: scale(1.2);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.5) !important;
    }

    /* Focus states for accessibility */
    *:focus {
        outline: 2px solid var(--border-glow) !important;
        outline-offset: 2px !important;
    }
    """