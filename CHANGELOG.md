# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed - Prompt Filter Persistence in Gradio UI (2025-01-21)
- **Fixed persistent prompt filtering in Runs tab**
  - Fixed bug where filter_type mismatch ("prompts" vs "prompt_ids") prevented navigation state from working
  - Made navigation_state persistent to maintain prompt filters when changing other filters (status, date, type)
  - Created unified filter handler that checks navigation_state for active prompt filtering
  - Fixed issue where empty filter results would show all runs instead of no runs
  - Fixed filter order - now applies all filters before limiting results for proper pagination
  - Updated Clear Filter button to properly reset navigation_state
  - Ensures filtering applies to all fetched runs, not just visible ones limited by Max Results setting

- **Improved filter reliability**
  - Prompt filtering now persists when using status, date, type, search, and rating filters
  - Switching tabs and returning maintains the active prompt filter
  - Multiple sequential prompt filters work reliably without degradation
  - Shows "No runs found" message when filters match no results (instead of showing all runs)

### Changed - Queue System Simplification (2025-01-20)
- **Complete Migration to SimplifiedQueueService**
  - Replaced complex QueueService (~680 lines) with SimplifiedQueueService (~400 lines)
  - Eliminated threading complexity and application-level locks
  - Uses database transactions with `SELECT ... FOR UPDATE SKIP LOCKED` for atomic job claiming
  - Implements single warm container strategy preventing container accumulation
  - Uses Gradio Timer component for automatic processing every 2 seconds instead of background threads
  - Maintains backward compatibility with same public API methods
  - Improved reliability through database-level concurrency control
  - Reduced complexity while maintaining full functionality

- **Architecture Simplification Benefits**
  - No background threads or complex lock management
  - Database handles all atomicity through transactions
  - Fresh database sessions prevent stale data issues
  - Linear execution flow easier to debug and maintain
  - Single warm container prevents resource accumulation
  - Timer-based processing integrates cleanly with Gradio lifecycle

### Fixed - Critical Bug Fixes (2025-01-19)
- **Batch Inference Infrastructure Fixes**
  - Fixed batch inference execution failing with "No such file or directory" errors
  - Added proper CRLF to LF conversion for batch_inference.sh script on Windows
  - Added required --controlnet_specs parameter with base spec for NVIDIA batch inference
  - Fixed batch output download to handle video_X subdirectory structure (outputs/batch_xxx/video_0/output.mp4)
  - Fixed control files to handle _0 suffix naming convention for batch operations
  - Corrected log paths for batch runs to use shared batch log instead of individual run paths

- **Enhancement Run System Fixes**
  - Removed incorrect thread-local storage implementation in QueueService that was causing SSH connection failures
  - Fixed duplicate prompt creation bug where enhanced prompts were being created twice
  - Removed legacy code path in cosmos_api.enhance_prompt() and replaced with proper error handling
  - Now only accepts "started" or "completed" status from execute_enhancement_run, fails fast on unexpected status
  - Fixed queue service spamming "GPU busy" messages during long operations

### Added - UI Feature Enhancement (2025-01-19)
- **Run Status Filter in Prompts Tab**
  - Added "Run Status" dropdown filter with options: "All", "No Runs", "Has Runs"
  - Helps identify unused prompts and manage prompt lifecycle efficiently
  - Filter works in combination with existing filters (search, enhanced status, date range)
  - Enables better prompt organization and workflow management
  - Improves user experience by highlighting prompts that haven't been used for inference yet

### Added - Enhanced Queue Management System (2025-01-18)
- **Automatic Job Cleanup and Database Management**
  - Automatic deletion of successful jobs to prevent database bloat and improve performance
  - Intelligent trimming of failed/cancelled jobs keeping last 50 for debugging purposes
  - Removed "Clear Completed" button as system now handles cleanup automatically
  - Enhanced database maintenance prevents queue table from growing indefinitely
  - Optimized queue performance through automated cleanup cycles

- **Enhanced Job Queue Functionality**
  - Fixed job selection in queue table to properly show job details when selected
  - Added "Cancel Selected Job" functionality for better job management
  - Enhanced "Kill Active Job" to update database status and prevent zombie runs
  - 5-second auto-refresh timer for real-time queue status updates
  - Improved job lifecycle management with proper status transitions

- **Graceful Shutdown and Error Handling**
  - Added graceful shutdown handler to mark running jobs as cancelled when app closes
  - Enhanced error handling for Docker container failures with fallback logging
  - Improved job state consistency during unexpected shutdowns
  - Better cleanup of resources when Gradio application terminates
  - Prevents orphaned jobs that stay "running" forever after app restart

### Added - User Rating System for Runs (2025-01-18)
- **Complete Rating System Implementation**
  - Added rating field (1-5 stars) to Run model in database schema
  - Rating system integration in Runs tab UI allowing users to rate completed runs
  - Rating displayed in runs table as numeric value (1-5) for quick assessment
  - Ratings persist in database and are included in run exports for analytics
  - Enhanced run tracking with user satisfaction metrics

- **UI Rating Integration**
  - Star rating component in run details for user feedback collection
  - Rating display in runs table for quick visual assessment
  - Automatic refresh of runs display after rating changes
  - Rating system only available for completed runs to ensure meaningful feedback
  - Seamless integration with existing run management workflow

### Enhanced - Recent Gradio UI Improvements (2025-01-18)
- **Auto-Download Control Files**
  - Automatic download of NVIDIA-generated control files (depth, normal, canny)
  - Enhanced workflow efficiency by automatically retrieving generated control files
  - Improved file management for complex inference operations with multiple control inputs
  - Streamlined post-processing workflow with automatic file organization

- **Gallery Navigation Enhancements**
  - Improved gallery navigation in Runs tab with enhanced user experience
  - Better thumbnail handling and video preview functionality
  - Enhanced metadata display for generated content
  - Improved gallery performance with optimized loading and rendering

- **Input-to-Runs Filtering and Navigation**
  - Enhanced navigation from Inputs tab to see related runs
  - Intelligent filtering system connecting inputs, prompts, and runs
  - Improved workflow traceability from source inputs to final results
  - Cross-tab navigation for better user experience and workflow management

- **Model-Specific UI Displays**
  - Dynamic UI parameter displays based on selected model type
  - Model-specific parameter visibility and configuration options
  - Enhanced user experience with contextual parameter controls
  - Improved parameter validation and user guidance based on model requirements

- **Enhanced Error Handling and Logging**
  - Improved fallback logging for Docker container failures
  - Enhanced error reporting and user feedback for failed operations
  - Better diagnostic information for troubleshooting failed runs
  - Comprehensive error handling across UI components for improved reliability

### Added - UI Navigation Enhancements (2025-01-17)
- **"View Runs using this input" button in Inputs tab**
  - Added new button below "View Prompts using this input" button in Inputs tab
  - Located in `cosmos_workflow/ui/tabs/inputs_ui.py` (lines 168-173)
  - When clicked, navigates to Runs tab and filters runs to show only those from prompts using the selected input directory
  - Implementation uses `prepare_runs_navigation_from_input` function that finds all prompts using the input directory, then calls existing `prepare_runs_navigation` function
  - Provides seamless navigation from input discovery to run results viewing

- **Previous/Next navigation buttons in Run Details**
  - Added "◀ Previous" and "Next ▶" buttons in Run Details header (lines 189-193 in `cosmos_workflow/ui/tabs/runs_ui.py`)
  - Allows users to navigate through gallery items without clicking individual thumbnails
  - Uses State component (`runs_selected_index`) to track current gallery index position
  - Implementation includes `navigate_gallery_prev` and `navigate_gallery_next` functions in `cosmos_workflow/ui/app.py`
  - Improves user experience by providing keyboard-like navigation through video results
  - Previous button decrements index with lower bound protection (minimum index 0)
  - Next button increments index and lets Gradio handle upper bounds automatically

### Added - Comprehensive Job Queue System for Gradio UI (2025-01-17)
- **JobQueue Database Model and Architecture**
  - Added `JobQueue` model to `cosmos_workflow/database/models.py` for persisting queue state
  - Supports four job types: `inference`, `batch_inference`, `enhancement`, and `upscale`
  - Complete job lifecycle tracking: `queued` → `running` → `completed`/`failed`/`cancelled`
  - FIFO (first-in, first-out) processing order with priority field for future enhancement
  - SQLite persistence ensures queue survives UI restarts and maintains state
  - Comprehensive timestamps: `created_at`, `started_at`, `completed_at` for full job tracking

- **QueueService - Production-Ready Job Management**
  - Created `QueueService` in `cosmos_workflow/services/queue_service.py` as CosmosAPI wrapper
  - **UI-Only Architecture**: Queue system exclusively for Gradio UI - CLI continues using direct CosmosAPI calls
  - **Critical GPU Conflict Prevention**: Checks actual running Docker containers before processing new jobs
  - Thread-safe implementation using `_job_processing_lock` to prevent race conditions when claiming jobs
  - Background processor thread runs continuously, automatically processing queued jobs
  - Intelligent job execution: only one job runs at a time due to single-GPU limitation
  - Position tracking and estimated wait times (120 seconds per job average)
  - Complete job management: add, cancel, clear completed, get status and position

- **Active Jobs Tab Integration and Queue Monitoring**
  - Enhanced Active Jobs tab with real-time queue status display and monitoring
  - Queue table shows job position, type, status, elapsed time, and action buttons
  - Background job processing with live status updates and queue position tracking
  - Job cancellation support for queued operations (running jobs require container kill)
  - Automatic queue refresh and status synchronization across UI components
  - Clear completed jobs functionality for queue maintenance and organization

- **Enhanced Job Types and Execution Support**
  - **Inference jobs**: Standard single-prompt inference with configurable parameters
  - **Batch inference jobs**: Multiple prompts processed together for efficiency
  - **Enhancement jobs**: AI-powered prompt enhancement using Pixtral model
  - **Upscale jobs**: Video upscaling operations with optional prompt guidance
  - All job types support full parameter configuration and result tracking
  - Queue service handles job-specific execution logic and result processing

- **Queue Architecture and Thread Safety**
  - **Single container paradigm enforcement**: Only one GPU operation at a time
  - Database session management with proper cleanup and thread safety
  - Background processor with configurable polling interval (2-second default)
  - Atomic job claiming prevents multiple threads from processing same job
  - Comprehensive error handling with failed job tracking and result storage
  - Graceful shutdown handling with processor thread cleanup

### Changed - Active Jobs Tab Improvements (2025-01-16)
- **Jobs & Queue Tab Renamed to "Active Jobs"**
  - Removed all queue-related functionality that never worked properly in production
  - Eliminated queue_status, queue_summary_card, and clear_queue functionality
  - Focused tab on actual running container monitoring and log streaming
  - Updated tab name to accurately reflect current functionality

- **Enhanced Auto-Refresh on Tab Switch**
  - Active Jobs tab now automatically refreshes when selected
  - Real-time container status updates when switching to the tab
  - Auto-start log streaming when active containers are detected
  - Improved user experience with immediate status feedback

- **Comprehensive System Status Display**
  - Enhanced GPU/container status display with detailed system information
  - Shows SSH connection status, Docker daemon status, and GPU information
  - Displays GPU utilization, memory usage, and CUDA version details
  - Comprehensive active operation tracking with run IDs and timestamps
  - Better detection and reporting of zombie runs and orphaned containers

- **Improved Log Streaming**
  - Enhanced log viewer integration with auto-start capability
  - Better log display formatting using log_viewer.get_text() for autoscroll
  - Improved error handling and connection resilience
  - Clear streaming status messages and user feedback

### Fixed - UI Reliability (2025-01-16)
- **Queue System Removal**
  - Removed non-functional queue management features
  - Eliminated misleading queue status indicators
  - Focused on actual container monitoring instead of theoretical queue state
  - Simplified UI to reflect actual system capabilities

- **Enhanced Error Handling**
  - Better error messages for container connection issues
  - Improved handling of missing containers or failed connections
  - More reliable status checking and reporting
  - Enhanced user feedback for system state changes

### Added - UI Enhancements and Run History System (2025-01-15)
- **Comprehensive Run History Tab Implementation**
  - New comprehensive Run History tab with advanced filtering, search, and batch operations
  - Multi-criteria filtering: status (all/completed/running/pending/failed/cancelled), date range (all/today/yesterday/last 7 days/last 30 days)
  - Text search functionality for prompt text and run IDs with real-time results
  - Configurable result limits (10-500 runs) with pagination support
  - Run statistics panel showing total runs, status breakdown, and success rate calculation
  - Interactive table with checkbox selection for batch operations
  - Multi-tab run details viewer: General, Parameters, Logs, and Output tabs
  - Batch operations: Select All/Clear Selection buttons with delete functionality
  - Professional card layouts with glassmorphism effects and loading skeleton animations

- **Model Type Removal and Interface Simplification**
  - Removed all model_type dropdowns and filters from the Gradio UI for cleaner interface
  - Simplified Create Prompt section by removing model_type selection
  - Removed model_type from Prompt Details display to focus on essential information
  - Updated all data tables to exclude model_type column, reducing visual clutter
  - Streamlined prompt operations to focus on core functionality

- **Enhanced Status Indicators**
  - Added enhanced status checkbox (✨ Enhanced) to Prompt Details view
  - Visual indicator for prompts that have been enhanced using AI enhancement features
  - Integrated enhanced status with prompt parameter display
  - Clear differentiation between standard and AI-enhanced prompts

- **Advanced Run Details System**
  - Multi-tab detailed run viewer with General, Parameters, Logs, and Output sections
  - General tab: Run ID, status, duration, prompt information, timestamps
  - Parameters tab: Control weights display (JSON format), inference parameters (JSON format)
  - Logs tab: Log file path display, full log content viewer with copy functionality
  - Output tab: Generated video preview, output path, download/delete buttons (handlers pending)
  - Professional card styling with hover effects and smooth transitions

- **Professional UI Design System**
  - Advanced CSS with gradient animations and glassmorphism card effects
  - Loading skeleton animations for better perceived performance
  - Professional gradient headers with animated color shifting effects
  - Interactive hover states and smooth transitions throughout interface
  - Improved visual hierarchy with consistent styling patterns
  - Enhanced button animations with shine effects and scaling transforms
  - Theme-aware design system with CSS variables for maintainability

### Enhanced - User Interface and Experience (2025-01-15)
- **Improved Filtering and Search Capabilities**
  - Advanced multi-criteria filtering system in Run History tab
  - Real-time search with text matching across prompt content and run IDs
  - Date range filtering with preset options for common time periods
  - Status-based filtering with comprehensive status support
  - Configurable result limits with performance optimization

- **Visual Design Improvements**
  - Comprehensive design system with consistent color schemes and typography
  - Enhanced card layouts with professional glassmorphism effects
  - Animated elements with smooth transitions and loading states
  - Interactive elements with hover effects and visual feedback
  - Improved accessibility with better contrast ratios and focus states

### Changed - Synchronous Execution Migration (2025-01-15)
- **Complete Migration from Asynchronous to Synchronous Execution**
  - All GPU operations now use blocking (synchronous) execution instead of lazy/async
  - Docker containers run without `-d` flag, naturally blocking until completion
  - GPU operations complete before returning control to caller
  - Eliminates complex background monitoring and StatusChecker dependencies
  - Simplifies execution flow and improves reliability

- **StatusChecker Removal**
  - Completely removed StatusChecker class and lazy evaluation monitoring
  - Eliminated async background monitoring threads that died with CLI exit
  - Removed container status polling and completion detection complexity
  - Database status updates occur synchronously during execution
  - No more orphaned "running" runs or container lifecycle management issues

- **Configuration-driven Timeouts**
  - Docker execution timeout now read from config.toml (docker_execution = 3600)
  - No more hardcoded timeouts in execution code
  - Configurable per-operation timeouts: inference (3600s), enhancement (1800s)
  - Automatic container cleanup on timeout to prevent resource leaks

### Added - Gradio Queue Implementation (2025-01-15)
- **Queue-based Job Processing**
  - Added Gradio queue with max_size=50 and default_concurrency_limit=1
  - Ensures sequential job processing (one inference at a time on GPU)
  - Queue persists on server side even if browser is closed
  - Queue status visible in Operations tab under "Execution Status"
  - Prevents concurrent GPU operations that could cause resource conflicts

- **Real-time Progress Tracking**
  - Enhanced UI with gr.Progress() for real-time operation tracking
  - Progress indicators show initialization, execution, and completion phases
  - Queue status display: "Queue: Ready | GPU: Available"
  - Auto-refresh queue status every 2 seconds with gr.Timer

### Added - Graceful Shutdown Handler (2025-01-15)
- **Simple Container Cleanup on Exit**
  - Added shutdown handler that kills Docker containers on server termination
  - Prevents orphaned GPU processes when Gradio server is killed
  - Uses existing kill_containers() method from CosmosAPI
  - Activated on SIGINT (Ctrl+C) and SIGTERM signals
  - Graceful cleanup with error handling and logging

### Enhanced - UI and User Experience (2025-01-15)
- **Professional Design Improvements**
  - Advanced gradient animations and glassmorphism effects
  - Enhanced card hover effects with smooth transitions
  - Professional gradient headers with color shifting animations
  - Improved button animations with shine effects and scaling
  - Theme-aware styling with CSS variables

- **Synchronous Operation Feedback**
  - Operations now show "Completed" instead of "Started in background"
  - Removed "Monitor progress with cosmos status" messages
  - Real-time completion status with output path display
  - Clear indication when operations finish successfully
  - Improved error messaging for failed operations

### Technical - Architecture Simplification (2025-01-15)
- **Simplified Execution Model**
  - Single execution thread per operation - no background complexity
  - Direct exit code handling from Docker containers
  - Immediate output downloading after container completion
  - Database status updates occur synchronously during execution
  - Eliminated need for container monitoring and completion detection

- **stream_output Parameter**
  - Added stream_output parameter to control console log streaming
  - CLI uses stream_output=True for real-time progress visibility
  - UI uses stream_output=False for cleaner interface
  - Maintains backwards compatibility with existing code

- **Improved Error Handling**
  - Synchronous execution provides immediate error feedback
  - Container failures detected immediately through exit codes
  - No more timeout-based error detection or polling failures
  - Cleaner error propagation through execution stack

### Deprecated - Asynchronous Components (2025-01-15)
- **Removed Background Monitoring**
  - StatusChecker class and all related monitoring infrastructure
  - Container status polling and lazy evaluation patterns
  - Background thread management and lifecycle complexity
  - Async execution patterns that caused CLI exit issues

- **Simplified Status Management**
  - No more "running" status persistence after CLI exit
  - Direct transition from "pending" to "completed"/"failed"
  - Eliminated intermediate statuses like "downloading" and "uploading"
  - Status always reflects actual operation state

### Added - Operations Tab UI Implementation (2025-09-10)
- **Advanced Operations Interface in Gradio UI**
  - New Operations tab with sophisticated two-column layout for improved workflow management
  - Left column: Prompt selection with comprehensive filtering and search capabilities
  - Right column: Inference controls with fine-grained parameter adjustment
  - Enhanced user experience with intuitive prompt-to-inference workflow

- **Inference Controls Enhancement**
  - Adjustable weights for all control modalities: visual, edge, depth, segmentation (0.0-1.0 range)
  - Advanced parameter controls for inference customization
  - Real-time parameter validation and visual feedback
  - Streamlined inference execution with immediate visual confirmation

- **AI-Powered Prompt Enhancement Integration**
  - Pixtral AI model integration for intelligent prompt enhancement
  - Semantic analysis and improvement of user prompts for better video generation
  - Enhanced description quality through advanced language model processing
  - Optional enhancement workflow with quality comparison features

### Fixed - Theme System and Visual Improvements (2025-09-10)
- **Theme System Overhaul**
  - Fixed theme system to properly respect system dark/light mode preferences
  - Automatic theme detection and application across all UI components
  - Consistent visual styling between light and dark modes
  - Improved user experience with seamless theme transitions

- **LogViewer CSS Architecture**
  - Replaced hardcoded colors in LogViewer with CSS variables for better maintainability
  - Theme-aware log display with proper contrast ratios in both light and dark modes
  - Improved readability and accessibility of log streaming interface
  - Consistent styling across all logging components

### Enhanced - Status Synchronization System (2025-09-10)
- **Improved Status Tracking**
  - Enhanced status synchronization between UI components and backend systems
  - Real-time status updates across all interface elements
  - Better error handling and status reporting for long-running operations
  - Consistent status indicators throughout the application

### Added - Phase 1 Upscaling Refactor Complete (2025-09-10)
- **Video-Agnostic Upscaling System**
  - Complete refactor enabling upscaling of any video file, not just inference run outputs
  - New CLI interface with mutually exclusive options: `--from-run` or `--video`
  - Support for guided upscaling with optional `--prompt` parameter
  - Added `--dry-run` mode for previewing upscaling operations without execution
  - Comprehensive validation of video formats and run completion status

- **Enhanced CLI Commands**
  - `cosmos upscale --from-run rs_123` - upscale from existing inference run
  - `cosmos upscale --video path/to/video.mp4` - upscale arbitrary video file
  - `cosmos upscale --prompt "cinematic quality" --weight 0.7` - guided upscaling with custom prompts
  - `cosmos upscale --dry-run` - preview mode showing what would be upscaled
  - Improved error handling with detailed validation messages

- **API Architecture Changes**
  - Replaced `CosmosAPI.upscale_run()` with `CosmosAPI.upscale()` for video-agnostic functionality
  - New signature: `upscale(video_source: str, control_weight: float = 0.5, prompt: str | None = None)`
  - No backward compatibility - old method removed (wasn't working anyway)
  - Enhanced parameter validation and error reporting

- **JSON Format Improvements**
  - Updated `to_cosmos_upscale_json()` to accept optional prompt parameter
  - Conditional prompt inclusion - only added to JSON when explicitly provided
  - Cleaner JSON structure following "include only when needed" design principle
  - Improved documentation for upscaling JSON format

- **Comprehensive Test Coverage**
  - 26 total tests across all upscaling functionality, all passing
  - 9 tests specifically for JSON prompt handling and conditional inclusion
  - 11 tests for CLI validation, edge cases, and error handling
  - 6 tests for GPU executor upscaling operations
  - Complete test coverage for video-agnostic upscaling workflows

### Added - StatusChecker Feature for Lazy Container Monitoring (2025-09-09)
- **Complete StatusChecker Implementation**
  - New StatusChecker class in cosmos_workflow/execution/status_checker.py for lazy container monitoring
  - Replaces broken async background monitoring with reliable lazy evaluation approach
  - Checks container status only when run data is queried via get_run() or list_runs()
  - Parses [COSMOS_COMPLETE] exit markers from container logs to determine final status
  - Automatically downloads outputs when containers complete successfully
  - Supports all model types: inference, enhancement, upscaling with appropriate file handling

- **Lazy Sync Integration with DataRepository**
  - StatusChecker initialized in DataRepository for automatic status synchronization
  - Lazy sync triggered when get_run() or list_runs() is called on running containers
  - Caching system prevents redundant checks on already-completed runs
  - Database status automatically updated from "running" to "completed"/"failed"
  - Seamless integration preserves existing API while adding background completion detection

- **Enhanced Shell Script Exit Markers**
  - Updated inference.sh, upscale.sh, and batch_inference.sh to write [COSMOS_COMPLETE] markers
  - Exit markers include actual exit codes: [COSMOS_COMPLETE] exit_code=0/1
  - Reliable completion detection independent of container status
  - Marker parsing supports multi-line logs and various output formats

- **CosmosAPI StatusChecker Initialization**
  - StatusChecker automatically initialized in CosmosAPI when dependencies available
  - Seamless integration with existing facade pattern architecture
  - No changes required to CLI commands or user workflows
  - Background monitoring functionality restored without performance impact

- **Comprehensive Test Coverage**
  - Complete test suite for StatusChecker class functionality
  - DataRepository lazy sync integration tests
  - Container status checking and log parsing tests
  - Output downloading tests for all supported model types
  - Edge case handling for missing containers, failed downloads, and malformed logs

### Fixed - Background Monitoring System (2025-09-09)
- **Resolved CLI Exit Termination Issue**
  - Fixed problem where background monitoring threads died when CLI commands exited
  - Replaced unreliable async background threads with lazy evaluation approach
  - StatusChecker only activates when run data is actively queried by users
  - Eliminates orphaned "running" runs that never update to completion status

- **Container Status Synchronization**
  - Fixed runs staying "running" forever after containers complete
  - Automatic status updates based on actual container completion markers
  - Proper handling of container failures with error message capture
  - Reliable exit code detection from log files instead of container inspection

- **Output Download Reliability**
  - Fixed race conditions where outputs were downloaded before generation completed
  - Downloads now trigger only after confirmed container completion
  - Model-specific output handling for inference (output.mp4), enhancement (batch_results.json), upscaling (output_4k.mp4)
  - Proper error handling when expected output files are missing

### Architecture - Lazy Evaluation Monitoring Pattern (2025-09-09)
- **Design Philosophy Shift**
  - Moved from "push" (background threads) to "pull" (lazy evaluation) monitoring pattern
  - StatusChecker activates only when users query run status through get_run() or list_runs()
  - Eliminates background thread lifecycle management and CLI exit dependencies
  - More reliable and predictable than async monitoring approaches

- **Integration Points**
  - StatusChecker initialized in both DataRepository and CosmosAPI for comprehensive coverage
  - Seamless integration with existing database operations and query methods
  - No changes to CLI commands or user-facing APIs required
  - Maintains facade pattern integrity while adding monitoring capabilities


### Added - Enhanced Delete Command (2025-09-09)
- **Output File Preservation by Default**
  - `--keep-outputs` flag: Default behavior now keeps output files during deletion
  - `--delete-outputs` flag: Explicit flag required to remove output files
  - Safer deletion workflow protects valuable generated content by default

- **Bulk Deletion Operations**
  - `--all` flag for `cosmos delete prompt` to delete all prompts at once
  - `--all` flag for `cosmos delete run` to delete all runs at once
  - Special confirmation prompt ("DELETE ALL") required for bulk operations
  - Preview shows counts and sample items before bulk deletion

- **Enhanced File Preview System**
  - Detailed file information including file types, counts, and total sizes
  - File type breakdown (e.g., "3 mp4 files (45.2 MB), 2 json files (1.3 KB)")
  - Smart file sampling shows up to 3 files per type with individual sizes
  - Total file count and size summary for informed deletion decisions

- **Improved Delete Preview Display**
  - Rich formatted output with colored panels and status indicators
  - File size formatting in human-readable units (KB, MB, GB)
  - Sample file listings with "... and X more" indicators
  - Clear distinction between files being kept vs deleted

### Added - Phase 5 Background Monitoring and Non-Blocking Operations (2025-09-08)
- **Complete Container Monitoring System**
  - Added `_get_container_status()` method to check Docker container status via `docker inspect`
  - Added `_monitor_container_completion()` to launch background monitoring threads
  - Added `_monitor_container_internal()` that runs in thread to poll container status every 5 seconds
  - Uses configurable timeout from config.toml (docker_execution = 3600 seconds) with automatic container cleanup
  - Monitors container state changes and handles completion, failure, and timeout scenarios

- **Automated Completion Handlers**
  - `_handle_inference_completion()` - downloads outputs and updates database when inference completes
  - `_handle_enhancement_completion()` - downloads enhanced text and updates database when enhancement finishes
  - `_handle_upscaling_completion()` - downloads 4K video and updates database when upscaling completes
  - All handlers properly distinguish success (exit code 0), failure (non-zero exit), and timeout (exit code -1)
  - Automatic database status updates eliminate orphaned "running" runs

- **Non-Blocking Execution Pattern**
  - Updated `execute_run()`, `execute_enhancement_run()`, `execute_upscaling_run()` for true non-blocking operation
  - Operations detect "started" status from DockerExecutor and return immediately
  - Background monitoring threads handle all completion tasks without blocking user workflows
  - CosmosAPI integration updated to pass service for database updates during background processing

### Fixed - Phase 5 Critical Issues (2025-09-08)
- **Database Synchronization**
  - Fixed runs staying "running" forever after containers complete
  - Database now automatically updates to "completed" or "failed" status when containers finish
  - Eliminated orphaned containers and zombie runs through proper monitoring

- **Enhancement File Contamination**
  - Fixed enhancement polling shared directories and finding old files
  - Enhancement now uses run-specific directories and proper completion detection
  - Replaced inefficient file polling with direct container monitoring

- **Output Download Timing**
  - Fixed downloading outputs before they exist
  - Outputs now download only after successful container completion
  - Proper error handling when containers fail before producing outputs

- **Container Resource Management**
  - Added timeout handling with automatic container cleanup
  - Prevents resource leaks from long-running or stuck containers
  - Proper container lifecycle management with monitoring threads

### Added - Phase 4 Unified Status Tracking (2025-09-08)
- **Enhanced Status Display for Active Operations**
  - Added get_active_operations() method to CosmosAPI for unified operation tracking
  - Enhanced check_status() to include active run details (type, run ID, prompt ID, start time)
  - Status command now displays what's actually running instead of just container presence
  - Shows operation type (INFERENCE, UPSCALE, ENHANCE) with run and prompt IDs
  - Detects and warns about orphaned containers and zombie runs for better debugging

- **Container Naming Implementation (Simplified Approach)**
  - All Docker containers now receive descriptive names at creation time
  - Container names follow format: cosmos_{model_type}_{run_id[:8]} for easy identification
  - Inference containers: `cosmos_transfer_{run_id[:8]}`
  - Upscaling containers: `cosmos_upscale_{run_id[:8]}`
  - Enhancement containers: `cosmos_enhance_{run_id[:8]}`
  - Batch containers: `cosmos_batch_{batch_name[:8]}`
  - Names are set once at container creation, retrieved via get_active_container()
  - No complex tracking needed - Docker is the single source of truth for container names

- **Unified GPU Operation Monitoring**
  - Single source of truth for all GPU operations across inference, upscaling, and enhancement
  - Consistent status reporting pattern for all operation types
  - Detection of inconsistent states (containers without runs, runs without containers)
  - Enhanced error reporting and user guidance based on actual system state

### Added - Phase 3 Upscaling Implementation (2025-09-08)
- **Independent Upscaling Run System**
  - Added `upscale_run()` method to CosmosAPI that creates separate database runs with model_type="upscale"
  - Independent upscaling execution tracking with complete status lifecycle: pending → running → completed/failed
  - New CLI command "cosmos upscale <run_id>" for upscaling completed inference runs
  - Upscaling creates separate run directories as `outputs/run_{run_id}/` for proper organization
  - Complete separation from inference operations following "One GPU Operation = One Database Run" principle
  - Links upscaling runs to parent inference runs via execution_config["parent_run_id"] for traceability

- **Enhanced GPU Execution Layer**
  - Added `execute_upscaling_run()` method to GPUExecutor for independent upscaling execution
  - Fixed DockerExecutor constructor mismatch in GPUExecutor initialization
  - Proper run directory creation and output organization for upscaling operations
  - Independent log files and status tracking separate from inference processes
  - Support for configurable control weights (0.0-1.0 range) with 0.5 default

- **Breaking Changes - Upscaling Architecture**
  - Removed upscaling parameters from `execute_run()` and `quick_inference()` methods
  - Upscaling now requires separate run creation and execution for better tracking
  - Previous combined inference+upscaling workflow replaced with two-step process
  - Database schema unchanged - leverages existing Run model with specialized model_type

### Fixed - Phase 3 Implementation (2025-09-08)
- **GPU Executor Constructor Issues**
  - Fixed DockerExecutor constructor mismatch preventing proper initialization
  - Resolved parameter passing issues in GPUExecutor instantiation
  - Proper service initialization and configuration management

### Added - Phase 2 Prompt Enhancement Database Runs (2025-09-08)
- **Complete Enhancement Run Tracking System**
  - `enhance_prompt()` method now creates database runs with model_type="enhance" for proper tracking
  - Enhancement operations stored in database outputs field with enhanced text, duration, and metadata
  - Run directories created as `outputs/run_{run_id}/` for consistent organization
  - Status tracking through complete lifecycle: pending → running → completed/failed
  - Support for both create_new and overwrite modes with validation against existing runs
  - Added "enhance" and "upscale" to SUPPORTED_MODEL_TYPES for extensible AI model support

- **New GPUExecutor Enhancement Method**
  - `execute_enhancement_run()` method provides run-tracked enhancement execution
  - Creates proper run directory structure with logs and results storage
  - Handles run_id parameter for directory creation and result tracking
  - Enhanced backward compatibility with legacy `run_prompt_upsampling()` method
  - Maintains existing enhancement functionality while adding database integration

- **Enhanced DataRepository Run Creation**
  - `create_run()` method accepts optional model_type parameter for override functionality
  - Enables "enhance" runs on "transfer" prompts with proper model type tracking
  - Supports specialized run types (enhance, upscale) while maintaining prompt model compatibility
  - Proper validation and error handling for model type combinations

### Fixed - Wrapper Pattern Compliance (2025-09-07)
- **Eliminated Docker Command String Violations**
  - Added new static methods to DockerCommandBuilder: build_logs_command(), build_info_command(), build_images_command(), build_kill_command()
  - Replaced 7 raw Docker command string violations with wrapper method calls
  - Updated cosmos_workflow/execution/docker_executor.py (5 violations fixed)
  - Updated cosmos_workflow/api/workflow_operations.py (2 violations fixed)
  - All Docker operations now use proper wrapper pattern as mandated by architecture
  - Added integration tests for kill_containers functionality
  - Maintains consistent error handling and security practices across all Docker operations

### Added - Utility Functions and Code Deduplication (2025-09-07)
- **New Utility Functions in cosmos_workflow/utils/workflow_utils.py**
  - `ensure_directory(path)`: Creates directories if they don't exist, replacing 14 instances of duplicate `path.mkdir(parents=True, exist_ok=True)` calls
  - `get_log_path(operation, identifier, run_id)`: Standardizes log path generation across 8 different locations in the codebase
  - `sanitize_remote_path(path)`: Converts Windows paths to POSIX format for remote systems, replacing 11 instances of manual path conversion
- **Enhanced DockerExecutor with New Detection Methods**
  - `get_active_container()`: Returns structured info about the single active cosmos container, expects exactly one running container
  - `get_gpu_info()`: Detects GPU information via nvidia-smi, returns GPU model, memory, driver version, and CUDA version
  - Added warning system when multiple containers detected (violates single container paradigm)
  - Improved container auto-detection for log streaming functionality
- **Code Reduction and Standardization**
  - Eliminated approximately 100 lines of duplicate code through centralized utility functions
  - Standardized directory creation, log path generation, and remote path handling across entire codebase
  - Single container paradigm enforcement with warnings for multiple running containers
  - Fixed `cosmos status` command to properly display GPU information (e.g., "NVIDIA H100 PCIe (81559 MB)")
- **Improved Status Command**
  - GPU detection now works correctly and displays GPU model and memory information
  - Container detection uses centralized `get_active_container()` method
  - Status tips updated to reflect current system state and single container expectation

### Added - GPU Detection and Container Management (2025-09-07)
- **Centralized Container Management**
  - New `get_active_container()` method in DockerExecutor for single-source container detection
  - Automatic detection and warning for multiple running containers
  - Structured container information with ID, name, status, and creation time
  - Refactored `stream_container_logs()` to use centralized container detection
  - Eliminated duplicate `docker ps` calls throughout codebase
- **GPU Detection Features**
  - New `get_gpu_info()` method to detect GPU via nvidia-smi
  - Automatic detection of GPU model, memory, driver version, and CUDA version
  - Integration with `cosmos status` command to display GPU information
  - Graceful handling when GPU drivers are not available
- **Status Command Improvements**
  - Fixed `cosmos status` to properly display GPU information
  - Updated to show single container paradigm with warnings for multiple containers
  - Improved status tips based on actual system state

### Added - Log Visualization Interface (2025-09-07)
- **Complete Log Visualization System**
  - New `cosmos_workflow/ui/log_viewer.py`: Core log viewer component with LogEntry dataclass, LogFilter, and LogViewer classes
  - New `cosmos_workflow/ui/log_viewer_web.py`: Web-based log viewer integration for Gradio interface
  - Real-time log streaming integration with existing RemoteLogStreamer
  - Advanced filtering capabilities: by level, search text, regex patterns, and time ranges
  - Export functionality supporting JSON, plain text, and CSV formats
  - Performance optimizations including virtual scrolling, caching, and batch updates
  - HTML formatting with syntax highlighting and responsive design
  - Accessibility features including screen reader support and keyboard navigation
  - Background log monitoring with configurable buffer sizes and update callbacks
  - Stream callback system for real-time log integration from remote sources

### Added - Real-Time Log Streaming Infrastructure (2025-09-07)
- **Complete Phase 3 Logging Infrastructure Implementation**
  - New `RemoteLogStreamer` class with seek-based position tracking using `tail -c +position`
  - Real-time log streaming integrated into DockerExecutor for both inference and upscaling
  - Background thread streaming during GPU execution without blocking execution flow
  - Efficient streaming that only reads new content, preventing re-reading of entire files
  - Support for completion markers, callback functions, and configurable timeouts
  - Automatic parent directory creation for local log files
  - Buffer size control for memory efficiency (8KB default)
  - Error resilience with graceful fallback and comprehensive logging

- **New Monitoring Module**
  - `cosmos_workflow/monitoring/log_streamer.py`: Complete RemoteLogStreamer implementation
  - `cosmos_workflow/monitoring/__init__.py`: Module initialization and exports
  - Comprehensive test coverage with 23 unit tests across streaming and integration scenarios
  - `tests/unit/monitoring/test_log_streamer.py`: Core streaming functionality tests
  - `tests/unit/execution/test_docker_executor_streaming.py`: DockerExecutor integration tests

- **Enhanced Docker Execution**
  - Updated `cosmos_workflow/execution/docker_executor.py` with integrated log streaming
  - Log streaming starts automatically during inference and upscaling operations
  - Configurable poll intervals (default 2.0s) and timeout handling (default 3600s)
  - Completion marker detection for clean stream termination
  - Thread safety with daemon threads that don't block process shutdown

### Changed - Complete 2-Step Workflow Refactoring (2025-09-06)
- **Major Architecture Refactoring to 2-Step Workflow**
  - Eliminated manual run creation - `cosmos create run` command removed
  - `cosmos inference` now accepts prompt IDs directly instead of run IDs
  - Batch inference merged into main inference command (provide multiple prompt IDs)
  - All CLI commands now exclusively use WorkflowOperations API layer
  - Complete abstraction achieved - no direct service/orchestrator access from CLI
  - Removed ~1,400+ lines of deprecated code and obsolete files
  - Added comprehensive architecture documentation with usage examples

- **CLI Command Updates**
  - `cosmos inference ps_xxx` replaces `cosmos create run ps_xxx` + `cosmos inference rs_xxx`
  - `cosmos inference ps_001 ps_002 ps_003` replaces `cosmos batch-inference rs_001 rs_002 rs_003`
  - `cosmos enhance ps_xxx` replaces `cosmos prompt-enhance ps_xxx`
  - All commands now return immediately actionable results

- **WorkflowOperations API Enhancements**
  - Added `check_status()`, `stream_container_logs()`, `verify_integrity()` operations
  - Removed deprecated `create_run()` and `execute_run()` methods
  - All operations return simple dictionaries for consistent interface
  - Complete separation between data operations (Service) and execution (Orchestrator)

### Changed - WorkflowOperations API Simplified (Step 1) (2025-09-06)
- **Simplified WorkflowOperations API for easier usage**
  - `quick_inference()` is now the primary inference method accepting `prompt_id` directly
  - `batch_inference()` now accepts list of `prompt_ids` instead of run_ids
  - Both methods create runs internally, eliminating the need for manual run creation in most workflows
  - `create_run()` and `execute_run()` remain available as low-level methods for advanced use cases
  - Updated docstrings emphasize that most users should use the simplified methods
  - Maintains backward compatibility while providing a more intuitive API

### Added - CLI Batch Inference Command (2025-09-06)
- **New `cosmos batch-inference` CLI command**
  - Command syntax: `cosmos batch-inference <run_ids...>` with options `--batch-name` and `--dry-run`
  - Processes multiple inference jobs in parallel on GPU for improved performance
  - 40-60% performance improvement over individual runs through reduced model loading overhead
  - Automatic splitting of batch outputs into individual run folders with proper naming
  - Complete integration with database-first architecture using run IDs (rs_xxxxx format)
  - Dry-run mode for previewing batch execution without GPU processing
  - Custom batch naming for organized output management

### Added - Batch Inference Support (2025-09-06)
- **Comprehensive Batch Inference System**
  - Added capability to run multiple inference jobs together using NVIDIA Cosmos Transfer's batch mode
  - New `to_cosmos_batch_inference_jsonl()` function converts run/prompt pairs to JSONL format
  - JSONL format supports per-video control overrides and auto-generation of missing controls
  - Batch processing reduces GPU initialization overhead by keeping models in memory
  - Automatic splitting of batch output folder into individual run folders with proper naming

- **New Batch Processing Functions**
  - `cosmos_workflow.utils.nvidia_format.to_cosmos_batch_inference_jsonl()`: Converts multiple runs to JSONL
  - `cosmos_workflow.utils.nvidia_format.write_batch_jsonl()`: Writes batch data to JSONL file
  - `cosmos_workflow.execution.docker_executor.run_batch_inference()`: Executes batch on GPU
  - `cosmos_workflow.workflows.workflow_orchestrator.execute_batch_runs()`: Orchestrates complete batch workflow

- **Production Script**
  - New `scripts/batch_inference.sh` for GPU batch execution with logging and environment setup
  - Batch spec generation for reproducibility and debugging
  - Complete error handling and execution logs per batch

- **Comprehensive Test Coverage**
  - 39 new tests across 3 test files covering all batch inference functionality
  - Unit tests for JSONL conversion, batch orchestration, and Docker execution
  - Tests validate JSONL format compliance with NVIDIA Cosmos Transfer requirements
  - Edge case testing for missing videos, empty batches, and error conditions

### Removed - Database Cleanup (2025-09-06)
- **Removed unused Progress model**
  - Deleted Progress model from database schema (was never implemented in production)
  - Removed all Progress-related tests (6 test methods)
  - Updated documentation to remove Progress references
  - Simplified database to 2 core models: Prompt and Run
  - No migration needed as Progress was never used in production code

### Fixed - Data Architecture Improvements (2025-09-06)
- **Critical Path Fixes**
  - Fixed output filename mismatch: changed from `result.mp4` to `output.mp4` to match actual GPU outputs
  - Enhanced run outputs JSON with metadata fields: `type`, `output_dir`, `primary_output`
  - Improved text enhancement tracking with proper run type identification
  - Simplified Gallery video retrieval logic, removed multiple fallback paths

- **Logging Consolidation**
  - Moved logs from `/logs/runs/` to run output directories (`outputs/run_xxx/execution.log`)
  - Removed unused `/logs` and `/notes` directories
  - All run artifacts now centralized in single directory per run

- **Data Integrity Tools**
  - Added `cosmos verify` command to check database-filesystem consistency
  - Detects missing files, orphaned directories, and data mismatches
  - Reports statistics and warnings for proactive maintenance
  - Manifest generation for downloaded files to track transfer completeness

- **UI Improvements**
  - Gallery now filters out text enhancement runs properly
  - Cleaner path handling with consistent expectations
  - Better error handling for missing video files

### Added - Gradio UI Improvements (2025-09-05)
- **Enhanced Gradio Web Interface**
  - All 4 control weights now available: visual, edge, depth, segmentation (0.0-1.0 range)
  - Optional video inputs: color required, depth/segmentation optional
  - Smart JSON generation: only includes controls with weight > 0
  - Efficient seek-based log tailing for better performance with large files
  - Improved prompt details display with full video paths and status indicators
  - ASCII-safe status indicators for Windows compatibility
  - Video status shows missing count: "[!] Missing (3)" or "[OK] (3 videos)"

- **Control Weight System**
  - Independent control weights for all 4 modalities
  - Weights apply even without input videos (model auto-generates)
  - Flexible configuration matching NVIDIA Cosmos Transfer approach
  - Only non-zero weights included in GPU JSON payload

- **Database Import Tool**
  - New script: scripts/import_json_prompts.py
  - Imports legacy JSON prompts into database using cosmos CLI
  - Preserves prompt names, text, and negative prompts
  - Successfully imported 16 prompts from 2025-09-03 archive

### Added - Service Layer Architecture Complete
- **Complete database-first service layer architecture**
  - Database-first approach: all data stored in SQLAlchemy database
  - Commands work with database IDs: ps_xxxxx (prompts), rs_xxxxx (runs)
  - No persistent JSON files - only created temporarily for NVIDIA GPU scripts
  - Three core models: Prompt, Run, Progress for comprehensive workflow tracking
  - Production-ready system with 453 passing tests

- **WorkflowService - Complete business logic layer**
  - CRUD operations for prompts and runs with transaction safety
  - Query methods: list_prompts(), list_runs(), search_prompts(), get_prompt_with_runs()
  - Input validation and sanitization with security features
  - Returns dictionaries optimized for CLI display
  - Support for multiple AI models through flexible JSON columns

- **WorkflowOrchestrator - GPU execution only**
  - Simplified to handle ONLY GPU execution: inference and upscaling
  - execute_run() method takes database dictionaries, returns results
  - run_prompt_upsampling() for AI prompt enhancement
  - Creates temporary NVIDIA-format JSON for GPU scripts only
  - No data persistence - pure execution layer

- **Database-first CLI commands**
  - cosmos create prompt "text" video_dir - creates prompt in DB, returns ps_xxxxx ID
  - cosmos create run ps_xxxxx - creates run from prompt ID, returns rs_xxxxx ID
  - cosmos inference rs_xxxxx - executes run on GPU with status tracking
  - cosmos list prompts/runs - lists with filtering and rich display
  - cosmos search "query" - full-text search with highlighted matches
  - cosmos show ps_xxxxx - detailed view with run history
  - cosmos prompt-enhance ps_xxxxx - AI enhancement creating new prompts and runs
  - All commands support --json for machine-readable output

### Changed - Architecture Simplified
- **BREAKING: Complete migration to database-first service architecture**
  - Replaced JSON file storage with SQLAlchemy database for all data operations
  - Clear separation of concerns: data layer (service) vs execution layer (orchestrator)
  - Extensible architecture supporting future AI models (reason, predict, etc.)
  - Clean, maintainable codebase without over-engineering

- **WorkflowService handles all data operations**
  - Business logic layer with comprehensive CRUD operations
  - Transaction safety with automatic rollback on errors
  - Input validation and security features (path traversal protection)
  - Query methods for listing, searching, and filtering prompts and runs
  - Returns dictionaries optimized for CLI display and JSON output

- **WorkflowOrchestrator simplified to execution only**
  - Removed all data persistence responsibilities
  - execute_run() takes database dictionaries, executes on GPU infrastructure
  - Creates temporary NVIDIA-format JSON files only for GPU script compatibility
  - Handles inference, upscaling, and AI prompt enhancement without data storage
  - Clean execution results returned to service layer for persistence

### Database Foundation
- **Flexible database schema supporting multiple AI models**
  - Prompt model with JSON columns for model-specific inputs and parameters
  - Run model for execution lifecycle tracking with real-time status updates
  - Progress model for granular progress tracking during execution stages
  - Extensible design allows adding future AI models without schema changes
  - Built-in security validation and input sanitization
  - Connection management with automatic session handling and transaction safety

### Fixed
- **Fixed RunSpec timestamp formatting issue in `cosmos create run` command**
  - Removed duplicate timezone suffix that was causing "+00:00+00:00" in timestamps
  - Now correctly uses `datetime.now(timezone.utc).isoformat()` without extra timezone indicator
  - Ensures timestamps are properly formatted for JSON serialization

### Changed
- **Improved `cosmos prompt-enhance` command to use true batch processing**
  - Now processes multiple prompts in a single batch instead of one at a time
  - Significantly improves performance when enhancing multiple prompts
  - Reduces GPU initialization overhead by keeping model in memory for entire batch
  - Maintains progress tracking while processing all prompts together

### Fixed
- **Integrated CosmosConverter for NVIDIA Cosmos Transfer format compatibility**
  - FileTransferService now automatically converts PromptSpec to NVIDIA format during upload
  - Ensures proper field mapping (prompt_text → prompt, control_paths → control_path)
  - Handles path separator conversion from Windows to Unix for remote systems
  - Falls back to original format if conversion fails, ensuring robustness
  - Video directories are now correctly detected from PromptSpec's input_video_path field

### Changed
- **Switched to read-only pre-commit hooks for predictable formatting workflow**
  - Pre-commit hooks now only check formatting/linting, never modify files
  - Prevents unexpected changes and commit-stash-reapply churn
  - Developers format manually with `ruff format .` and `ruff check . --fix`
  - Recommended: Configure editor to format on save for seamless workflow
  - Updated pyproject.toml to set `fix = false` globally
  - Updated .pre-commit-config.yaml with explicit read-only arguments

### Changed - 2025-09-04 (Smart Naming Refactor)
- **Refactored smart naming from spaCy to KeyBERT for improved semantic extraction**
  - Replaced spaCy dependency parsing with KeyBERT semantic keyword extraction
  - Now uses all-MiniLM-L6-v2 SBERT model for lightweight embeddings
  - Configured with n-grams (1-2) and MMR diversity (0.7) to avoid duplicate keywords
  - Added comprehensive stopword filtering for both common English and VFX domain terms
  - Fallback to simple keyword extraction when KeyBERT is unavailable
  - Names limited to 3 words maximum for better conciseness
  - New dependencies: keybert and sentence-transformers (replacing spacy)

### Changed - 2025-09-03 (PromptSpecManager Refactor)
- **Refactored prompt specification creation to use PromptSpecManager**
  - CLI `create prompt` command now uses PromptSpecManager instead of direct PromptSpec creation
  - Enhanced prompts now get smart names based on content (e.g., "futuristic_city") instead of generic "_enhanced" suffix
  - Upsampling workflow uses PromptSpecManager for consistent spec creation
  - Improved separation of concerns with centralized spec management
  - All prompt spec creation now goes through a single, consistent API

### Added - 2025-09-03 (File Transfer)
- **New `download_file()` method in FileTransferService**
  - Downloads single files from remote instance via SFTP
  - Automatically creates parent directories if needed
  - Handles Windows path conversion for cross-platform compatibility
  - Provides granular file download control alongside existing directory download

### Fixed - 2025-09-03 (Batch Upsampling)
- **Fixed batch prompt upsampling duplicate results issue**
  - Batch processing now returns unique results for each prompt instead of duplicates
  - Added `determine_offload_mode()` function to automatically force offload=False for batches > 1
  - Prevents model reinitialization between prompts by keeping it in memory for batches
  - Renamed `working_prompt_upsampler.py` to `prompt_upsampler.py` to reflect production status
  - Made module importable for testing by handling missing GPU dependencies gracefully
  - Added comprehensive unit tests following TDD principles with real function calls

### Added - 2025-09-03 (Docker Log Streaming)
- **Docker log streaming feature**
  - New `--stream` flag for `cosmos status` command to stream container logs in real-time
  - Auto-detection of most recent container when no container ID specified
  - Graceful Ctrl+C handling to stop streaming
  - Helpful error messages when no containers are running
  - 24-hour timeout for long-running log streams

### Changed - 2025-09-02 (CLI Migration Complete)
- **Migrated to modular CLI structure**
  - Switched from monolithic `cli.py` (800+ lines) to modular `cli/` directory
  - Maintained 100% backward compatibility
  - Improved display with Rich formatting and emojis
  - Better error handling and consistent output
  - Maximum file size reduced by 76% (217 lines vs 800+)

### Added - 2025-09-01 (CLI Refactoring Complete)
- **Phase 1: Created modular CLI architecture foundation**
  - New `cosmos_workflow/cli_new/` directory structure for refactored CLI
  - `base.py`: Core utilities including CLIContext class and error handling decorator
  - `completions.py`: All autocomplete functions consolidated in one place
  - `helpers.py`: Rich display utilities for tables, progress, and formatting
  - Foundation for splitting 935-line CLI into manageable ~100-200 line modules

- **Phase 2 & 3: Migrated all commands to modular structure**
  - `status.py` (63 lines): Remote GPU status checking
  - `prepare.py` (156 lines): Video sequence preparation
  - `enhance.py` (164 lines): Prompt enhancement with AI
  - `inference.py` (117 lines): Inference execution
  - `create.py` (217 lines): Create prompt and run specifications
  - Main CLI integration in `__init__.py` (71 lines)
  - Successfully reduced max file size by 76% (935 → 217 lines)
  - All 23 tests still passing, 100% functionality preserved

- **Display Utilities Added**
  - Success/error/warning/info display functions with consistent styling
  - Table creation helpers for structured output
  - Progress context managers for long operations
  - Formatting utilities for paths, IDs, file sizes, and durations
  - Dry-run mode display helpers

- **Error Handling Improvements**
  - Centralized error handling decorator for consistent error messages
  - UTF-8 encoding support for Windows terminals
  - Graceful handling of keyboard interrupts

### Changed - 2025-09-01 (Documentation)
- **Streamlined CLAUDE.md**
  - Reduced from 192 to 83 lines (57% reduction)
  - Moved documentation & commit policy to top with red emphasis
  - Simplified structure while keeping all critical information
  - Added clear "commit as you go" requirement

### Changed - 2025-09-01 (Major CLI Improvements)
- **Merged Commands for Simplicity**
  - Combined `run`, `inference`, and `upscale` into single `inference` command
  - Default behavior: run both inference and upscaling (most common use case)
  - Use `--no-upscale` flag for inference only
  - Removed deprecated `run` and `upscale` commands completely

- **Autocomplete System Overhaul**
  - Created reusable autocomplete functions, eliminating ~25 lines of duplicate code
  - Added smart autocomplete for video files, directories, and prompt specs
  - Fixed pattern matching to use prefix matching instead of substring
  - Added proper autocomplete for `--videos-dir` and `--video` options
  - Autocomplete now works properly in Git Bash and CMD on Windows

- **Parameter Simplification**
  - Removed `--num-gpu` and `--cuda-devices` from all commands (always uses 1 GPU)
  - Simplified `prompt-enhance`: `--resolution` now implies preprocessing
  - Removed unnecessary flags: `--save-dir`, `--num-frames`, `--preprocess`
  - `prompt-enhance` now accepts multiple files as arguments

- **Bug Fixes**
  - Fixed critical PromptSpec metadata bug in upsample_integration.py
  - Fixed prompt-enhance to properly create new PromptSpecs with `_enhanced` suffix
  - Properly generates new IDs for enhanced PromptSpecs
  - Fixed `is_upsampled` and `parent_prompt_text` fields

### Removed - 2025-09-01 (Codebase Cleanup)
- **Old CLI Files**
  - Removed `cli_old.py` (obsolete argparse-based CLI)
  - Removed deprecated `run` and `upscale` commands
  - Removed `setup_completion.py` (integrated into main CLI)

- **Test Files & Directories**
  - Removed obsolete CLI tests that referenced old argparse-based CLI
  - Deleted `tests/unit/cli/` directory with outdated test files
  - Removed `test_bash_script_execution_workflow` and `TestCLIWorkflow` class from integration tests
  - Deleted all root-level test scripts (`test_resolution_*.py`, `quick_resolution_test.py`, etc.)
  - Removed unused test directories (`resolution_tests/`, `test_videos/`, `test_images/`, `testing/`)

- **Scripts & Utilities**
  - Deleted redundant scripts from `scripts/` directory (kept only essential remote execution files)
  - Removed `check_remote_results.py`, `deploy_and_test_upsampler.py`, `test_actual_resolution_limits.py`
  - Deleted unused shell scripts (`ssh_lambda.sh`, `upsample_prompt.sh`, `run_upsampler_docker.sh`)
  - Removed linting helper scripts (`lint.py`, `fix_all_linting.py`)

- **Build Artifacts & Cache**
  - Cleaned up all cache directories (`.mypy_cache/`, `.ruff_cache/`, `htmlcov/`)
  - Removed all log files and test JSON outputs
  - Deleted empty directories (`notes/`, `art/`, `test_notes/`)

### Added - 2025-09-01 (Documentation)
- **Documentation & Commit Policy** in CLAUDE.md
  - Added mandatory documentation update requirement before commits
  - Clear policy: update CHANGELOG.md immediately after features
  - Requirement to update README.md for user-facing changes
  - "Document as you code" principle

### Changed - 2025-09-01 (CLI Refactor)
- **Complete CLI Overhaul**
  - Migrated from argparse to Click framework for better UX
  - Reorganized commands into logical groups (`create prompt`, `create run`)
  - Added rich console output with colors and progress indicators
  - Renamed `upsample` command to `prompt-enhance` for clarity
  - Removed deprecated `convert-sequence` command (use `prepare` instead)
  - Added shell completion support for Bash, Zsh, Fish, PowerShell, and Git Bash
  - Improved help text and command examples throughout

- **Simplified Installation**
  - Removed pip package configuration - now using standalone scripts
  - Created `cosmos` Python script and `cosmos.bat` for direct execution
  - Updated documentation with manual setup instructions
  - No pip installation required - just install dependencies and run

- **Documentation Updates**
  - Updated README.md with new command structure and examples
  - Updated CLAUDE.md with simplified setup instructions
  - Added shell completion setup instructions for all platforms
  - Clarified that pip is not required for CLI usage

### Added - 2025-09-01 (Resolution Discovery)
- **Major Resolution Limit Discovery**
  - Found actual maximum resolution: 940×529 (497,260 pixels)
  - This is 3x higher than initially documented 320×180 limit
  - Created comprehensive resolution testing framework
  - Added `docs/RESOLUTION_LIMITS_FINAL.md` with production guidelines
  - Created `docs/SESSION_SUMMARY_2025_09_01.md` documenting findings

### Fixed - 2025-09-01
- **SSH Unicode Encoding Error**
  - Fixed Windows encoding issues in `cosmos_workflow/connection/ssh_manager.py`
  - Added try/catch blocks with ASCII fallback for special characters
  - Resolves `'charmap' codec can't encode character` errors

### Changed - 2025-09-01
- **Updated Resolution Documentation**
  - Corrected token formula findings (formula is wrong)
  - Updated `docs/TESTING_RESULTS.md` with actual limits
  - Documented that 960×540 reports 4,157 actual tokens (not 17,936 estimated)
  - Clarified pixel threshold is 497,000-518,000, not token-based

### Added - 2025-08-31 (Testing & Documentation)
- **Comprehensive Testing Documentation**
  - Created `docs/TESTING_RESULTS.md` with performance benchmarks
  - Documented batch processing performance (45% speedup without offloading)
  - Identified resolution limits and token usage patterns
  - Added GPU memory usage profiles
  - Established testing framework for future models

- **Comprehensive Test Coverage for WorkflowOrchestrator**
  - Added 25 unit tests achieving 93.79% coverage (up from 13.66%)
  - Test categories: initialization, helpers, workflows, convenience methods, logging, edge cases
  - Created `tests/unit/workflows/test_workflow_orchestrator.py`
  - All tests use proper mocking for fast, isolated execution

- **Upsampling Workflow Integration**
  - Created `cosmos_workflow/workflows/upsample_integration.py` - Mixin for WorkflowOrchestrator
  - Added `cosmos_workflow/workflows/resolution_tester.py` - Resolution testing utilities
  - Integrated prompt upsampling into CLI with `upsample` command
  - Added support for batch upsampling with checkpoint recovery
  - Implemented token estimation formula: `tokens = width × height × frames × 0.0173`

- **Resolution Analysis Tools**
  - Created resolution testing framework for finding maximum safe resolutions
  - Documented safe resolution limits (320×180 @ 2 frames = 1,992 tokens)
  - Added automatic video preprocessing for high-resolution inputs
  - Created test video generation capabilities for resolution testing

### Changed - 2025-08-31 (Test Suite)
- **Test Suite Cleanup**
  - Removed outdated integration tests using non-existent methods
  - Fixed SFTP integration tests with proper context manager mocking
  - Achieved full green baseline: 614 tests passing, 0 failing
  - Added missing methods to FileTransferService for test compatibility

- **Documentation Improvements**
  - Clarified "legacy" methods are actually convenience methods
  - Updated workflow orchestrator comments to reflect true purpose
  - Created test plan document with coverage analysis
  - Created comprehensive testing and merge strategy documentation

- **Script Cleanup**
  - Removed 24 redundant/experimental upsampling scripts
  - Kept only 4 essential scripts: working_prompt_upsampler.py, deploy_and_test_upsampler.py, test_actual_resolution_limits.py, check_remote_results.py
  - Consolidated upsampling logic into workflow integration

- **Docker Integration**
  - Updated upsampling to use DockerCommandBuilder pattern (consistent with inference)
  - Added proper environment variable setup for VLLM
  - Integrated with existing SSH/SFTP infrastructure

### Fixed - 2025-08-31
- **SFTP Test Failures**
  - Fixed mock configuration to properly mock get_sftp() context manager
  - Added upload_directory() and download_directory() to FileTransferService
  - Resolved all 8 SFTP integration test failures

- **Resolution Token Limits Identified**
  - Maximum safe resolution: 320×180 @ 2 frames (1,992 tokens)
  - Token formula verified: `tokens = width × height × frames × 0.0173`
  - Videos above 426×240 will fail with vocab errors

- **Upsampling Issues**
  - Fixed VLLM multiprocessing spawn method requirement
  - Resolved token limit errors with high-resolution videos
  - Fixed environment variable setup for TorchElastic

### Security - 2025-08-31 (Planned)
- **Version Pinning Requirements**
  - Need to stop using `:latest` Docker tags
  - Plan to pin specific model checkpoint versions
  - Document all dependency versions for reproducibility

### Added - 2024-12-30 (Modern Linting & Code Quality)
- **Comprehensive Linting Setup**
  - Integrated Ruff (v0.12.11) - Fast, all-in-one Python linter replacing black, isort, flake8, pylint
  - Added MyPy (v1.17.1) for static type checking
  - Added Bandit (v1.8.6) for security vulnerability scanning
  - Added Safety (v3.6.0) for dependency vulnerability checking
  - Configured pre-commit hooks for automated code quality checks
  - Created Makefile for convenient command access

- **Code Quality Improvements**
  - Fixed 473+ linting issues automatically (76% reduction)
  - Converted all logging f-strings to lazy % formatting for better performance
  - Added UTC timezone to all datetime.now() calls
  - Fixed docstring formatting across codebase
  - Reorganized and optimized imports
  - Applied consistent code formatting

### Added - 2024-12-31 (Test Suite Reorganization & Baseline)
- **Comprehensive Test Suite Reorganization**
  - Created clear test structure: unit/, integration/, system/
  - Added shared fixtures in conftest.py for all test categories
  - Created test utilities and mock objects in fixtures/
  - Added sample test data in fixtures/sample_data/
  - Created pytest.ini with test markers and configuration

- **Integration Test Suite**
  - test_sftp_workflow.py - SFTP file transfer testing
  - test_workflow_orchestration.py - Complete pipeline testing
  - test_video_pipeline.py - Video processing integration

- **System Test Suite**
  - test_end_to_end_pipeline.py - Full user workflow tests
  - test_performance.py - Performance benchmarks

- **CI/CD Configuration**
  - GitHub Actions workflow (.github/workflows/test.yml)
  - Pre-commit hooks configuration (.pre-commit-config.yaml)
  - Multi-stage testing pipeline with coverage reporting

### Fixed - 2024-12-31
- **Test Compatibility Issues**
  - Fixed CLI test arguments for create-spec command
  - Updated convert-sequence test for new default metadata generation
  - Fixed SFTP test imports (FileTransferManager → FileTransferService)
  - Marked outdated Docker executor tests as skipped

- **Test Coverage Baseline**
  - 239 unit tests passing
  - 2 tests skipped (need refactoring)
  - Overall structure ready for expansion

### Added - 2024-12-30 (Phase 3: Windows SFTP & Full GPU Inference Pipeline)
- **Windows-Compatible SFTP File Transfer System**
  - Complete replacement of rsync with pure Python SFTP implementation
  - Cross-platform file transfer (Windows/Linux/macOS)
  - Recursive directory upload/download support
  - Progress tracking and error handling

- **Full Remote GPU Inference Pipeline**
  - End-to-end workflow: upload → inference → upscaling → download
  - Real GPU execution on remote instances
  - Support for multi-GPU configurations
  - Automatic output organization and timestamping

- **Enhanced Configuration System**
  - Unified config.toml for all settings
  - Environment-specific configurations (local/remote)
  - Docker image and runtime configurations
  - SSH connection pooling and reuse

### Added - 2024-12-29 (Phase 2: AI Integration & Smart Naming)
- **AI-Powered Description Generation**
  - Automatic video content analysis using BLIP AI model
  - Generates natural language descriptions from video frames
  - Optional AI features with graceful fallback

- **Smart Naming System**
  - Intelligent name generation from AI descriptions
  - Context-aware naming using NLP techniques
  - Configurable name length and style

- **Enhanced Cosmos Sequence Processing**
  - prepare-inference command with auto-detection
  - Support for all Cosmos control modalities
  - Automatic metadata generation with AI insights

### Added - 2024-12-28 (Phase 1: PNG to Video Conversion)
- **Video Processing Pipeline**
  - convert-sequence command for PNG to video conversion
  - Support for custom resolutions (720p, 1080p, 4K)
  - Frame rate control and video standardization
  - Metadata extraction and generation

- **Local AI Features**
  - Video metadata extraction (resolution, fps, duration)
  - Frame analysis and object detection
  - Caption generation for video content
  - Tag extraction and classification

### Changed - 2024-12-27 (Major Refactoring)
- **Schema System Overhaul**
  - Separated PromptSpec and RunSpec for better separation of concerns
  - Added DirectoryManager for organized file management
  - Implemented hash-based unique IDs
  - Added comprehensive validation

- **Workflow Architecture**
  - Modular service-based architecture
  - Clear separation of SSH, transfer, and execution layers
  - Improved error handling and logging
  - Support for partial workflow execution

### Initial Release - 2024-12-20
- **Core Workflow System**
  - Python-based replacement for bash scripts
  - SSH connection management with Paramiko
  - Docker container orchestration
  - Prompt and run specification schemas

- **CLI Interface**
  - create-spec: Create prompt specifications
  - create-run: Create run configurations
  - run: Execute workflows on remote GPU
  - status: Check remote instance status

- **Configuration Management**
  - TOML-based configuration
  - Support for multiple environments
  - SSH key authentication
  - Docker runtime configuration

## Version History

### [0.3.0] - 2024-12-30
- Modern linting and code quality tools
- Comprehensive test suite reorganization
- Windows SFTP compatibility
- Full GPU inference pipeline

### [0.2.0] - 2024-12-29
- AI integration for descriptions and naming
- Enhanced video processing
- Cosmos sequence preparation

### [0.1.0] - 2024-12-20
- Initial release
- Core workflow system
- Basic CLI interface
- Configuration management
