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
        transition: box-shadow 0.3s cubic-bezier(0.4, 0, 0.2, 1), border-color 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }

    .gr-box:hover, .gr-group:hover {
        /* Removed transform to prevent stacking context issues with dropdowns */
        box-shadow: 0 10px 30px rgba(102, 126, 234, 0.2) !important;
        border-color: var(--border-glow) !important;
    }

    /* Button animations - only for Gradio buttons, not dropdown arrows */
    button.gr-button {
        position: relative;
        overflow: hidden;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }

    button.gr-button.primary, button.gr-button[variant="primary"] {
        background: var(--primary-gradient) !important;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3) !important;
    }

    button.gr-button:hover {
        transform: translateY(-2px) scale(1.02);
    }

    button.gr-button::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
        transition: left 0.5s;
        pointer-events: none;  /* Ensure it doesn't block interactions */
        z-index: 1;  /* Keep it above background but below text */
    }

    button.gr-button:hover::before {
        left: 100%;
    }

    /* Fix for Create Prompt button to show Gradio spinner */
    #create_prompt_btn {
        overflow: visible !important;  /* Allow spinner to show */
    }

    /* Remove the shine animation for this button to avoid conflicts */
    #create_prompt_btn::before {
        display: none !important;
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

    /* Ensure prompts table container has proper overflow handling */
    .prompts-table-container {
        max-height: 450px !important;
        overflow-y: auto !important;
        overflow-x: auto !important;
        margin-bottom: 16px !important;
        border: 1px solid rgba(102, 126, 234, 0.2) !important;
        border-radius: 8px !important;
        padding: 8px !important;
        display: block !important;
        position: relative !important;
    }

    /* Force the table to stay within container */
    .prompts-table {
        max-height: 430px !important;
        overflow-y: auto !important;
        display: block !important;
    }

    /* Ensure the dataframe wrapper respects container */
    .prompts-table-container .gr-dataframe {
        max-height: 430px !important;
        overflow-y: auto !important;
        overflow-x: auto !important;
    }

    /* Make sure the dataframe table itself scrolls */
    .prompts-table-container table {
        width: 100% !important;
    }

    /* Fix for the dataframe overflow */
    .prompts-table-container > div {
        max-height: 430px !important;
        overflow: auto !important;
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
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.05), rgba(118, 75, 162, 0.05)) !important;
        border: 1px solid rgba(102, 126, 234, 0.2) !important;
        border-radius: 8px !important;
        padding: 12px !important;
        margin-top: 8px !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }

    .batch-operation:hover {
        border-color: rgba(102, 126, 234, 0.3) !important;
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.08), rgba(118, 75, 162, 0.08)) !important;
    }

    /* Ensure batch operations always have proper styling regardless of parent state */
    .gr-row.batch-operation,
    .batch-operation.gr-row,
    div.batch-operation,
    .batch-operation {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.05), rgba(118, 75, 162, 0.05)) !important;
        border: 1px solid rgba(102, 126, 234, 0.2) !important;
        border-radius: 8px !important;
        padding: 12px !important;
        margin-top: 8px !important;
        position: relative !important;
        z-index: 10 !important;
        display: flex !important;
        align-items: center !important;
        gap: 8px !important;
        min-height: 50px !important;
    }

    /* Selection counter styling */
    .selection-counter {
        display: inline-flex;
        align-items: center;
        margin-left: auto;
        padding: 4px 12px;
        background: rgba(102, 126, 234, 0.1);
        border-radius: 16px;
        font-size: 0.9em;
        color: #667eea;
    }

    .selection-counter strong {
        color: #764ba2;
        font-weight: 600;
        margin: 0 4px;
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

    /* Filter section styling */
    .filter-section {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.03), rgba(118, 75, 162, 0.03));
        border: 1px solid rgba(102, 126, 234, 0.15);
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 16px;
    }

    .filter-section:hover {
        border-color: rgba(102, 126, 234, 0.3);
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.05), rgba(118, 75, 162, 0.05));
    }

    /* Results counter styling */
    .results-counter {
        display: inline-flex;
        align-items: center;
        padding: 4px 12px;
        background: rgba(102, 126, 234, 0.1);
        border-radius: 16px;
        font-size: 0.9em;
        color: #667eea;
        border: 1px solid rgba(102, 126, 234, 0.2);
    }

    .results-counter strong {
        color: #764ba2;
        font-weight: 600;
        margin: 0 4px;
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

    /* Unified Input Details Card Styling */
    .unified-input-card {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.05) 0%, rgba(118, 75, 162, 0.05) 100%) !important;
        border: 2px solid rgba(102, 126, 234, 0.3) !important;
        border-radius: 16px !important;
        padding: 20px !important;
        animation: fadeInUp 0.5s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }

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

    /* Video Preview Grid */
    .video-preview-grid {
        display: grid !important;
        grid-template-columns: repeat(3, 1fr) !important;
        gap: 12px !important;
        margin-top: 16px !important;
    }

    .video-preview-card {
        position: relative;
        border-radius: 12px !important;
        overflow: hidden !important;
        background: rgba(0, 0, 0, 0.3) !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        cursor: pointer;
    }

    .video-preview-card:hover {
        transform: scale(1.05);
        box-shadow: 0 8px 24px rgba(102, 126, 234, 0.4) !important;
        z-index: 10;
    }

    .video-preview-label {
        position: absolute;
        top: 8px;
        left: 8px;
        background: rgba(0, 0, 0, 0.8);
        color: white;
        padding: 4px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
        z-index: 1;
    }

    /* Video preview container fix - remove scrollbar */
    .video-preview-container {
        overflow: hidden !important;
    }

    .video-preview-container video {
        width: 100% !important;
        height: 100% !important;
        object-fit: cover !important;
    }

    /* Remove scroll indicators from video components - but not dropdowns */
    div[class*="video"]:not([class*="dropdown"]) {
        overflow: hidden !important;
    }

    /* Fix dropdown z-index and overflow issues */
    .gr-dropdown {
        position: relative !important;
        z-index: 999 !important;
    }

    .gr-dropdown-menu,
    [class*="dropdown"][class*="menu"],
    [class*="dropdown"][class*="list"] {
        position: absolute !important;
        z-index: 9999 !important;
        overflow: visible !important;
    }

    /* Ensure parent containers don't clip dropdowns */
    .gr-box:has(.gr-dropdown),
    .gr-group:has(.gr-dropdown),
    .gr-column:has(.gr-dropdown),
    .gr-row:has(.gr-dropdown) {
        overflow: visible !important;
    }

    /* Consistent textbox styling matching prompts tab */
    .detail-card input[type="text"],
    .detail-card textarea {
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        color: white !important;
    }

    .detail-card input[type="text"]:focus,
    .detail-card textarea:focus {
        border-color: var(--border-glow) !important;
        background: rgba(255, 255, 255, 0.08) !important;
    }

    /* Input details typography hierarchy */
    .input-title {
        font-size: 1.5rem !important;
        font-weight: 700 !important;
        background: var(--primary-gradient);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 12px !important;
    }

    .input-subtitle {
        font-size: 0.9rem !important;
        color: rgba(255, 255, 255, 0.6) !important;
        margin-bottom: 16px !important;
    }

    /* Video preview gallery with 16:9 aspect ratio */
    #video_preview_gallery .thumbnail-item {
        aspect-ratio: 16 / 9 !important;
        object-fit: cover !important;
        min-height: 120px !important;
        border-radius: 8px !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        border: 2px solid transparent !important;
    }

    #video_preview_gallery video {
        aspect-ratio: 16 / 9 !important;
        object-fit: cover !important;
        width: 100% !important;
        height: auto !important;
        border-radius: 8px !important;
    }

    #video_preview_gallery .grid-container {
        gap: 12px !important;
        padding: 8px !important;
    }

    #video_preview_gallery .thumbnail-item:hover {
        transform: scale(1.03);
        border-color: var(--border-glow) !important;
        box-shadow: 0 6px 16px rgba(102, 126, 234, 0.3) !important;
    }

    /* Runs gallery specific styling for proper aspect ratio */
    #runs_gallery .thumbnail-item {
        aspect-ratio: 16 / 9 !important;
        object-fit: cover !important;
        border-radius: 8px !important;
        overflow: hidden !important;
    }

    #runs_gallery img {
        width: 100% !important;
        height: 100% !important;
        object-fit: cover !important;
    }

    #runs_gallery .grid-container {
        gap: 12px !important;
        padding: 0 !important;
    }

    #runs_gallery .thumbnail-item:hover {
        transform: scale(1.02);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.25) !important;
    }
    """
