# Cosmos-Houdini-Experiments

A Python-based workflow system for running Nvidia Cosmos video generation experiments with Houdini integration.

## 🚀 **Features**

- **Automated Workflow**: Complete pipeline from prompt to final video output
- **Remote Execution**: Run experiments on remote GPU instances via SSH
- **Docker Integration**: Containerized execution environment
- **Batch Processing**: Handle multiple prompts and experiments
- **Upscaling Support**: Built-in video upscaling capabilities
- **Refactored Prompt Management**: Modern schema-based prompt system

## 🏗️ **Architecture**

The system is built with a modular, extensible architecture:

```
cosmos_workflow/
├── config/          # Configuration management
├── connection/      # SSH and remote connectivity
├── execution/       # Docker execution engine
├── prompts/         # Prompt management and schemas
├── transfer/        # File transfer operations
├── workflows/       # Workflow orchestration
└── utils/          # Utility functions
```

## 🔧 **Installation**

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd cosmos-houdini-experiments
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure the system**:
   ```bash
   # Edit config/config.toml with your settings
   cp cosmos_workflow/config/config.toml.example cosmos_workflow/config/config.toml
   ```

## ⚙️ **Configuration**

Create a `config.toml` file in `cosmos_workflow/config/`:

```toml
[ssh]
host = "your-remote-host.com"
username = "ubuntu"
key_path = "~/.ssh/id_rsa"
port = 22

[paths]
remote_dir = "/home/ubuntu/NatsFS/cosmos-transfer1"
local_prompts_dir = "./inputs/prompts"
local_runs_dir = "./inputs/runs"
local_videos_dir = "./inputs/videos"
local_outputs_dir = "./outputs"
local_notes_dir = "./notes"

[docker]
image = "nvcr.io/nvidia/cosmos:latest"
container_name = "cosmos-experiment"
```

## 🎯 **Refactored Prompt Management System**

The system now uses a modern, schema-based approach with two main components:

### **PromptSpec** - Prompt Definition
- **Purpose**: Defines a prompt without execution parameters
- **Contains**: Text prompt, video paths, control inputs, metadata
- **File Naming**: `{name}_{timestamp}_{hash}.json`
- **Example**: `cyberpunk_city_neon_2025-08-29T21-57-55_ps_c2b411e4355b.json`

### **RunSpec** - Execution Configuration
- **Purpose**: Defines actual inference runs with all parameters
- **Contains**: Control weights, inference parameters, execution status
- **File Naming**: `{prompt_name}_{timestamp}_{hash}.json`
- **Example**: `cyberpunk_city_neon_2025-08-29T21-57-55_rs_5d28ae21073e.json`

### **Benefits**
- **Separation of Concerns**: Prompts vs. execution parameters
- **Reusability**: Use same prompt with different parameters
- **Traceability**: Track which parameters produced which results
- **Organization**: Date-based directory structure
- **Uniqueness**: Hash-based IDs prevent conflicts

## 🚀 **Usage**

### **Basic Workflow**

1. **Create a PromptSpec**:
   ```bash
   python -m cosmos_workflow.main create-spec "cyberpunk_city" "Cyberpunk city at night with neon lights"
   ```

2. **Create a RunSpec**:
   ```bash
   python -m cosmos_workflow.main create-run prompt_spec.json --weights 0.3 0.4 0.2 0.1
   ```

3. **Run the experiment**:
   ```bash
   python -m cosmos_workflow.main run run_spec.json
   ```

### **Advanced Options**

- **Custom control weights**: `--weights 0.3 0.4 0.2 0.1`
- **Custom parameters**: `--num-steps 50 --guidance 8.5`
- **Multiple GPUs**: `--num-gpu 2 --cuda-devices "0,1"`
- **Skip upscaling**: `--no-upscale`
- **Custom upscale weight**: `--upscale-weight 0.7`

### **Modern Schema System**

The system uses a modern, schema-based approach that provides better organization and reusability:

```bash
# Create PromptSpec
python -m cosmos_workflow.main create-spec "building_flythrough" "Aerial view of a modern building"

# Create RunSpec from PromptSpec
python -m cosmos_workflow.main create-run prompt_spec.json --weights 0.25 0.25 0.25 0.25
```

## 📁 **Directory Structure**

```
inputs/
├── prompts/         # PromptSpec files (date-organized)
│   └── 2025-08-29/
│       └── cyberpunk_city_neon_2025-08-29T21-57-55_ps_c2b411e4355b.json
├── runs/            # RunSpec files (date-organized)
│   └── 2025-08-29/
│       └── cyberpunk_city_neon_2025-08-29T21-57-55_rs_5d28ae21073e.json
└── videos/          # Input video files
    └── cyberpunk_city_neon/
        ├── color.mp4
        ├── depth.mp4
        └── segmentation.mp4

outputs/             # Generated videos and results
notes/               # Experiment logs and notes
```

## 🔍 **Monitoring and Status**

Check remote instance status:
```bash
python -m cosmos_workflow.main status --verbose
```

## 🧪 **Testing**

Run the test suite:
```bash
pytest tests/
```

Check code coverage:
```bash
pytest --cov=cosmos_workflow tests/
```

## 🤝 **Contributing**

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📝 **License**

[Add your license information here]

## 🆘 **Support**

For issues and questions:
1. Check the documentation
2. Review existing issues
3. Create a new issue with detailed information
