# Cosmos Workflow Manager - UI Guide

A comprehensive guide to using the Cosmos Workflow Manager's advanced Gradio web interface.

## Table of Contents

- [Getting Started](#getting-started)
- [Interface Overview](#interface-overview)
- [Tab-by-Tab Guide](#tab-by-tab-guide)
- [Advanced Features](#advanced-features)
- [Design System](#design-system)
- [Troubleshooting](#troubleshooting)

## Getting Started

### Launching the Interface

```bash
# Launch with default settings
cosmos ui

# Launch on custom port
cosmos ui --port 8080

# Create public share link
cosmos ui --share
```

The interface will open at `http://localhost:7860` by default and provides a complete workflow management system for AI video generation.

### System Requirements

- **Local System**: Python 3.10+, web browser with modern CSS support
- **Remote GPU**: NVIDIA H100 or compatible GPU with Docker support
- **Network**: Stable connection to remote GPU instance via SSH

## Interface Overview

The Cosmos Workflow Manager features a professional, multi-tab interface designed for comprehensive workflow management:

### Core Design Principles

- **Professional Aesthetics**: Gradient animations, glassmorphism effects, and smooth transitions
- **Comprehensive Functionality**: Complete workflow from input preparation to output management
- **Advanced Filtering**: Multi-criteria search and filtering across all data
- **Batch Operations**: Efficient management of multiple runs and prompts
- **Real-time Updates**: Live status monitoring and progress tracking

### Navigation Structure

The interface is organized into five main tabs, each serving specific workflow needs:

1. **📁 Inputs**: Video browser and prompt creation
2. **🚀 Prompts**: Prompt management and operations
3. **🎬 Outputs**: Generated video gallery
4. **📊 Run History**: Comprehensive run management
5. **📦 Active Jobs**: Real-time container monitoring

## Tab-by-Tab Guide

### 📁 Inputs Tab

**Purpose**: Browse input videos and create prompts directly from available content.

#### Input Video Browser
- **Gallery Display**: Large thumbnail grid (4 columns, 3 rows) showing input directories
- **Video Preview**: Multi-tab preview system for Color, Depth Map, and Segmentation
- **Metadata Display**: Resolution, duration, creation time, and file information
- **Auto-fill Integration**: Selected inputs automatically populate prompt creation

#### Navigation Features
- **View Prompts Button**: "→ View Prompts Using This Input" - navigates to Prompts tab with filter applied
- **View Runs Button**: "→ View Runs Using This Input" - navigates to Runs tab showing only runs from prompts that use the selected input directory
- **Cross-Tab Navigation**: Seamless workflow from input discovery to prompt creation to run results

#### Create Prompt Section
- **Video Directory**: Auto-filled when selecting inputs, supports manual entry
- **Prompt Text**: Main description for AI generation (supports multi-line)
- **Name**: Optional descriptive name (auto-generated if empty)
- **Negative Prompt**: Pre-filled with optimized defaults, fully customizable

**Workflow**:
1. Browse input gallery and select desired video directory
2. Preview multimodal inputs (color, depth, segmentation)
3. Enter prompt text and optional customizations
4. Create prompt - automatically generates unique ID

### 🚀 Prompts Tab

**Purpose**: Unified prompt management and AI operations with enhanced status tracking.

#### Features Removed for Simplification
- **Model Type Filters**: Removed to focus on core functionality
- **Model Type Dropdowns**: Simplified interface without model selection
- **Model Type Display**: Cleaner prompt details without model type clutter

#### Enhanced Prompt Details
- **Enhanced Status Indicator**: ✨ Enhanced checkbox shows AI-enhanced prompts
- **Run Status Filter**: New "Run Status" dropdown with options:
  - **All**: Shows all prompts regardless of usage
  - **No Runs**: Shows only unused prompts (helpful for identifying untested prompts)
  - **Has Runs**: Shows only prompts that have been used for inference
- **Comprehensive Information**: ID, name, text, negative prompt, creation time
- **Video Directory**: Shows source input directory for traceability
- **Enhanced Prompts**: Clear visual distinction for AI-improved prompts

#### Operation Controls
**Inference Tab**:
- **Control Weights**: Visual (0.0-1.0), Edge (0.0-1.0), Depth (0.0-1.0), Segmentation (0.0-1.0)
- **Advanced Parameters**: Steps, guidance scale, seed, FPS, sigma max
- **Blur & Edge Controls**: Configurable blur strength and Canny threshold
- **Batch Execution**: Select multiple prompts for efficient processing

**Prompt Enhance Tab**:
- **AI Model**: Uses Pixtral model for intelligent enhancement
- **Action Options**: Create new enhanced prompt or overwrite existing
- **Force Overwrite**: Option to delete existing runs when overwriting

#### Selection and Batch Operations
- **Interactive Table**: Checkbox selection with real-time count display
- **Clear Selection**: One-click deselection of all items
- **Batch Processing**: Run operations on multiple selected prompts
- **Workflow Management**: Use "Run Status" filter to identify prompts ready for inference or cleanup

#### Run Status Filter Usage
The "Run Status" filter helps manage prompt lifecycle:
- **"No Runs"**: Identify newly created prompts that haven't been tested yet
- **"Has Runs"**: Focus on prompts with existing results for analysis or re-runs
- **"All"**: Standard view showing all prompts

This filter works in combination with other filters (search, enhanced status, date range) for precise prompt management.

### 🎬 Outputs Tab

**Purpose**: Browse and manage generated video outputs with comprehensive metadata.

#### Gallery System
- **Video Thumbnails**: Generated videos displayed in organized gallery
- **Metadata Integration**: Run IDs, prompt names, status, and creation dates
- **Filter Options**: Status-based filtering (completed, all)
- **Model Type Filtering**: Filter by generation model type

#### Output Details
- **Comprehensive Information**: Run ID, status, creation time, prompt details
- **Input Traceability**: Links to original color, depth, and segmentation inputs
- **Video Preview**: Direct video playback with download capabilities
- **File Management**: Download and path display functionality
- **Auto-Download Controls**: Automatic download of NVIDIA-generated control files (depth, normal, canny) for streamlined workflow

### 📊 Run History Tab

**Purpose**: Advanced run management with comprehensive filtering, search, and batch operations.

#### Advanced Filtering System
**Status Filters**:
- All runs
- Completed runs
- Currently running
- Pending execution
- Failed runs
- Cancelled operations

**Date Range Filters**:
- All time
- Today only
- Yesterday only
- Last 7 days
- Last 30 days

**Text Search**:
- Search prompt text content
- Search by run ID
- Real-time results as you type
- Case-insensitive matching

**Result Configuration**:
- Configurable limits (10-500 runs)
- Performance optimization for large datasets

#### Statistics Panel
- **Total Run Count**: Complete execution history
- **Status Breakdown**: Detailed counts by execution status
- **Success Rate**: Percentage calculation of completed runs
- **Visual Indicators**: Color-coded status representation

#### Interactive Run Table
**Table Features**:
- **Checkbox Selection**: Individual and batch selection capabilities
- **Sortable Columns**: Run ID, Prompt, Status, Duration, Created, Rating, Output
- **Selection Controls**: Select All and Clear Selection buttons
- **Batch Operations**: Delete selected runs (with confirmation)

**Column Information**:
- **Run ID**: Unique identifier with hover details
- **Prompt**: Associated prompt name with truncation for long names
- **Status**: Color-coded execution status
- **Duration**: Calculated execution time for completed runs
- **Created**: Timestamp of run creation
- **Rating**: User rating (1-5 stars) for completed runs with quality assessment
- **Output**: Indicates if output files exist

#### Multi-Tab Run Details

**Navigation Controls**:
- **Previous/Next Buttons**: "◀ Previous" and "Next ▶" buttons in the Run Details header
- **Gallery Navigation**: Navigate through gallery items without clicking individual thumbnails
- **Index Tracking**: Uses State component to track current gallery position
- **Seamless Browsing**: Browse through video results with keyboard-like navigation

**General Tab**:
- **Run Information**: ID, status, duration
- **Prompt Details**: Name, full text content
- **Timestamps**: Created and completed times
- **User Rating**: Interactive star rating system (1-5 stars) for completed runs with automatic display refresh
- **Status History**: Complete execution lifecycle

**Parameters Tab**:
- **Control Weights**: JSON display of visual, edge, depth, segmentation weights
- **Inference Parameters**: Complete parameter set including steps, guidance, seed
- **Configuration**: All execution settings used for the run

**Logs Tab**:
- **Log File Path**: Direct path to execution logs
- **Full Log Content**: Complete log output with copy functionality
- **Load Logs Button**: Refresh log content on demand
- **Formatted Display**: Syntax highlighting and readable formatting

**Output Tab**:
- **Video Preview**: Generated video playback
- **Output Path**: Complete file system path
- **Download Options**: Direct download functionality (handlers pending)
- **Delete Options**: Remove run outputs (handlers pending)

#### Batch Operations
- **Selection Management**: Visual count of selected runs
- **Bulk Actions**: Delete multiple runs simultaneously
- **Confirmation System**: Prevent accidental bulk operations
- **Progress Tracking**: Status updates during batch operations

### 📦 Active Jobs Tab

**Purpose**: Real-time monitoring of active containers with comprehensive system status, job queue management, and log streaming.

#### Production Job Queue System

The Active Jobs tab features a simplified, reliable job queue system designed exclusively for the Gradio UI, providing organized job management while the CLI continues to use direct execution. The system has been completely rebuilt to eliminate threading complexity and use database-level concurrency control.

**Key Features**:
- **UI-Only Architecture**: Queue system is exclusively for the Gradio UI interface
- **Database-First Design**: Uses database transactions for atomic job claiming without application locks
- **FIFO Processing**: First-in, first-out job processing with position tracking
- **SQLite Persistence**: Queue state survives UI restarts and maintains complete job history
- **Single Container Strategy**: Maintains one warm container preventing resource accumulation
- **Timer-Based Processing**: Uses Gradio Timer component for automatic processing every 2 seconds

**Job Queue Display**:
- **Queue Status**: Real-time display showing total queued jobs and current queue state
- **Queue Table**: Interactive table showing job position, ID, type, status, elapsed time, and actions
- **Position Tracking**: Shows queue position for each job with estimated wait times
- **Job Details**: Select any job to view detailed configuration and status information

**Supported Job Types**:
- **Inference**: Single prompt inference with configurable parameters
- **Batch Inference**: Multiple prompts processed together for efficiency (40% faster)
- **Enhancement**: AI-powered prompt enhancement using Pixtral model
- **Upscale**: Video upscaling operations with optional prompt guidance

**Queue Management**:
- **Timer-Based Processing**: Gradio Timer component automatically processes queued jobs every 2 seconds
- **Atomic Job Claiming**: Database-level locking ensures only one process can claim jobs at a time
- **Job Cancellation**: Cancel queued jobs (before they start running) and selected jobs from queue table
- **Intelligent Cleanup**: Automatic deletion of successful jobs and trimming of failed/cancelled jobs (keeps last 50)
- **Enhanced Job Control**: Kill active jobs with proper database status updates to prevent zombie runs
- **Live Status Updates**: Real-time queue status with timer-based refresh
- **Position Monitoring**: Track your job's position and estimated wait time
- **Graceful Shutdown**: Marks running jobs as cancelled when app closes to maintain state consistency

#### Enhanced System Status Display
- **SSH Connection Status**: Connection health monitoring with visual indicators
- **Docker Daemon Status**: Docker service status on remote instance
- **GPU Information**: Detailed GPU model, memory, CUDA version, and utilization metrics
- **Active Container Details**: Container name, status, ID, and creation time
- **Active Operation Tracking**: Current operation type (INFERENCE, UPSCALE, ENHANCE) with run and prompt IDs
- **Auto-refresh on Tab Switch**: Automatically refreshes status when tab is selected

#### Container Monitoring
- **Running Containers**: Real-time container status and lifecycle monitoring
- **Container Details**: Comprehensive container information including name and status
- **Zombie Run Detection**: Identifies and warns about orphaned containers or database inconsistencies
- **Manual Refresh**: "🔄 Refresh & Stream" button for on-demand status updates
- **Resource Monitoring**: GPU utilization and memory usage tracking

#### Enhanced Log Streaming System
- **Auto-start Log Streaming**: Automatically begins streaming when active containers are detected
- **Real-time Log Output**: Live log streaming with improved text display and autoscroll
- **Stream Controls**: Manual refresh and stream functionality
- **Log Management**: Clear logs functionality with improved text formatting
- **Enhanced Error Handling**: Better connection resilience and error reporting

#### Active Job Cards
- **Active Job Display**: Professional cards showing current operation details
- **Operation Type**: Clear indication of INFERENCE, UPSCALE, or ENHANCE operations
- **Run Information**: Run ID, prompt ID, start time, and current status
- **Container Information**: Container name, ID, and status for running operations
- **Idle State**: Clear "No Active Job" indication when system is idle

## Advanced Features

### Cross-Tab Navigation System

The interface features a sophisticated navigation system that allows seamless workflow progression from input discovery to final results.

#### Workflow Navigation Path
1. **Inputs Tab**: Browse and select input video directories
2. **Navigation to Prompts**: Use "→ View Prompts Using This Input" to see all prompts created from the selected input
3. **Navigation to Runs**: Use "→ View Runs Using This Input" to see all runs generated from prompts using the selected input
4. **Result Browsing**: Use Previous/Next buttons in Run Details to navigate through video results

#### Navigation Features

**From Inputs Tab**:
- **View Prompts Button**: Filters Prompts tab to show only prompts created from the selected input directory
- **View Runs Button**: Filters Runs tab to show only runs from prompts that use the selected input directory
- **Automatic Filtering**: Navigation automatically applies appropriate filters and updates the target tab

**In Run Details**:
- **Previous Button (◀)**: Navigate to the previous item in the gallery
- **Next Button (▶)**: Navigate to the next item in the gallery
- **Index Tracking**: Maintains current position in gallery for consistent navigation
- **Bounds Protection**: Previous button stops at the first item, Next button is handled by Gradio's bounds

#### Implementation Details

**Cross-Tab Navigation**:
- Uses `prepare_runs_navigation_from_input()` function to find all prompts using the selected input directory
- Calls existing `prepare_runs_navigation()` function to apply filtering and switch to Runs tab
- Updates navigation state and applies filter indicators to show active filtering

**Gallery Navigation**:
- Uses `navigate_gallery_prev()` and `navigate_gallery_next()` functions in app.py
- Maintains gallery selection index using Gradio State component
- Updates gallery selection without requiring thumbnail clicks

### Enhanced Status System

#### AI Enhancement Indicators
- **Enhanced Checkbox**: Visual indicator (✨ Enhanced) for AI-improved prompts
- **Status Integration**: Enhanced status displayed in prompt details
- **Enhancement History**: Track which prompts have been enhanced
- **Clear Differentiation**: Distinguish between standard and enhanced prompts

#### Status Tracking
- **Real-time Updates**: Live status changes across interface
- **Comprehensive States**: Pending, running, completed, failed, cancelled
- **Visual Indicators**: Color-coded status representation
- **Progress Tracking**: Real-time progress updates with gr.Progress()

### Professional Design System

#### Visual Design Elements
**Glassmorphism Effects**:
- Semi-transparent cards with blur effects
- Subtle border highlighting
- Depth and layering through transparency
- Professional aesthetic with modern appeal

**Gradient Animations**:
- Animated gradient headers with color shifting
- Smooth transitions between states
- Interactive hover effects with scaling
- Loading animations with shimmer effects

**Interactive Elements**:
- Button hover effects with shine animations
- Card hover states with elevation changes
- Smooth scaling transitions on interaction
- Visual feedback for all clickable elements

#### Layout and Typography
- **Consistent Spacing**: Professional spacing system
- **Typography Hierarchy**: Clear information hierarchy
- **Responsive Design**: Adapts to different screen sizes
- **Accessibility**: High contrast ratios and focus indicators

### Advanced Filtering and Search

#### Multi-Criteria Filtering
- **Combinable Filters**: Stack multiple filters for precise results
- **Real-time Updates**: Instant results as filters change
- **Performance Optimization**: Efficient filtering for large datasets
- **Filter Memory**: Maintains filter state during navigation

#### Search Functionality
- **Instant Search**: Real-time results as you type
- **Multiple Fields**: Search across prompt text and run IDs
- **Case Insensitive**: Flexible matching for user convenience
- **Search Highlighting**: Visual highlighting of matched terms

### Batch Operations System

#### Selection Management
- **Visual Feedback**: Clear indication of selected items
- **Selection Count**: Real-time count of selected items
- **Mass Selection**: Select All and Clear All functionality
- **Persistent Selection**: Maintains selection during operations

#### Batch Processing
- **Multiple Run Operations**: Process multiple runs simultaneously
- **Confirmation Systems**: Prevent accidental bulk operations
- **Progress Tracking**: Visual progress during batch operations
- **Error Handling**: Graceful handling of partial failures

## Design System

### Color Scheme and Variables

The interface uses a comprehensive CSS variable system for consistent theming:

```css
:root {
    --primary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    --secondary-gradient: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    --success-gradient: linear-gradient(135deg, #00d2ff 0%, #3a7bd5 100%);
    --dark-bg: #1a1b26;
    --card-bg: rgba(255, 255, 255, 0.02);
    --border-glow: rgba(102, 126, 234, 0.5);
}
```

### Animation System

#### Keyframe Animations
- **Gradient Shift**: Color-shifting animations for headers
- **Shimmer**: Loading state animations
- **Fade In Up**: Staggered animations for batch operations
- **Pulse**: Status indicator animations

#### Transition System
- **Cubic Bezier**: Professional easing curves
- **Consistent Timing**: Standardized animation durations
- **Hover States**: Interactive feedback on all elements
- **Loading States**: Visual feedback during operations

### Component Library

#### Card Components
- **Detail Cards**: Glassmorphism effect cards for information display
- **Interactive Cards**: Hover effects and transitions
- **Loading Cards**: Skeleton loading animations
- **Status Cards**: Color-coded status representation

#### Button System
- **Primary Buttons**: Gradient backgrounds with animation effects
- **Secondary Buttons**: Subtle styling for secondary actions
- **Icon Buttons**: Consistent icon placement and sizing
- **Hover Effects**: Scaling and shine animations

## Troubleshooting

### Common Issues

#### Interface Loading Problems
**Symptoms**: Blank interface or loading errors
**Solutions**:
1. Check browser console for JavaScript errors
2. Ensure stable internet connection
3. Try hard refresh (Ctrl+F5 or Cmd+Shift+R)
4. Verify CosmosAPI is properly initialized

#### Filtering Not Working
**Symptoms**: Filters don't update results
**Solutions**:
1. Clear all filters and reapply
2. Refresh the data using refresh buttons
3. Check for network connectivity issues
4. Verify backend data is accessible

#### Run Details Not Loading
**Symptoms**: Run details tabs show empty content
**Solutions**:
1. Click "Load Full Logs" button in Logs tab
2. Verify run exists in database
3. Check file permissions for log files
4. Refresh run history data

### Performance Optimization

#### Large Datasets
- Use result limits (100-500 max) for better performance
- Apply specific filters to reduce data volume
- Use date range filters for recent data only
- Clear browser cache if interface becomes slow

#### Network Issues
- Ensure stable connection to remote GPU instance
- Check SSH tunnel if using port forwarding
- Verify firewall allows access to Gradio port
- Test connectivity with `cosmos status` command

### Browser Compatibility

#### Recommended Browsers
- **Chrome/Chromium**: Full feature support and best performance
- **Firefox**: Good compatibility with CSS animations
- **Safari**: Basic compatibility, some animation differences
- **Edge**: Full compatibility with modern CSS features

#### Known Limitations
- Internet Explorer not supported
- Very old browser versions may have CSS issues
- Mobile browsers have limited functionality
- Some animations may be reduced on low-power devices

### Getting Help

#### Debug Information
When reporting issues, include:
1. Browser type and version
2. Console error messages (F12 → Console tab)
3. Steps to reproduce the problem
4. Expected vs actual behavior
5. Network connectivity status

#### Log Files
Relevant log files for debugging:
- Gradio server logs (terminal output)
- Browser console logs (F12 → Console)
- Backend API logs (if applicable)
- Network tab for failed requests (F12 → Network)

The Cosmos Workflow Manager UI provides a comprehensive, professional interface for managing AI video generation workflows. With its advanced filtering, batch operations, and real-time monitoring capabilities, it streamlines the entire process from input preparation to output management.