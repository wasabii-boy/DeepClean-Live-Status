# DeepClean

![Version](https://img.shields.io/badge/version-1.1.0-blue)
![Python](https://img.shields.io/badge/python-3.6%2B-brightgreen)
![License](https://img.shields.io/badge/license-MIT-green)

**DeepClean** is a sophisticated system cleaning utility designed to safely remove unnecessary files while preserving your important data. It features a modern, interactive terminal interface built with the Rich library, providing real-time feedback throughout the cleaning process.

## 🚀 Key Features

- **Interactive Terminal Interface**: Beautiful and intuitive UI with real-time progress and stats
- **Safe Cleaning**: Advanced protection patterns ensure important files are never deleted
- **Multiple Cleaning Options**: 
  - System & application caches
  - Package manager caches (npm, pip, yarn, etc.)
  - Temporary files & directories
  - Log files
  - Empty directories
  - Duplicate file detection
- **Simulation Mode**: Preview cleaning actions without deleting anything
- **Comprehensive Reports**: Generate detailed cleaning reports for audit purposes
- **Interactive Selector**: Choose exactly what to clean with an easy-to-use menu
- **Multi-layered Protection**:
  - Protected patterns for important files
  - Recent file protection (configurable age threshold)
  - System file detection
  - Special permission checks

## 📋 System Requirements

- Python 3.6 or higher
- Dependencies:
  - `rich`: Modern terminal UI components
  - `psutil`: System resource monitoring
  - `pathspec`: Pattern matching for file protection

## 💻 Installation & Quick Start

### Option 1: Using the startup script (recommended)

```bash
# Clone the repository
git clone https://github.com/yourusername/deepclean.git
cd deepclean

# Make the startup script executable
chmod +x start_deepclean.sh

# Run DeepClean with simulation mode
./start_deepclean.sh --dry-run
```

### Option 2: Manual installation

```bash
# Clone the repository
git clone https://github.com/yourusername/deepclean.git
cd deepclean

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install rich psutil pathspec

# Run DeepClean in simulation mode
python deepclean.py --dry-run
```

## 🔍 Command-line Options

| Option | Description |
|--------|-------------|
| `--dry-run` | **Recommended for first use!** Simulate cleaning without deleting files |
| `--verbose` | Show more detailed information during operation |
| `--config <file>` | Use a custom configuration file |
| `--min-file-age <days>` | Set minimum age for files to clean (default: 7 days) |
| `--clean-empty-dirs` | Enable deletion of empty directories |
| `--detect-duplicates` | Find and remove duplicate files |
| `--clean-temp-files` | Clean temporary files across the system |
| `--generate-report` | Create a detailed report after cleaning |
| `--selector` | Launch the interactive cleaning selector before starting |
| `--simple-output` | Use simplified output (useful for smaller terminals) |

## ⌨️ Keyboard Controls

When running the interactive interface:

| Key | Function |
|-----|----------|
| `Q` | Quit the application |
| `P` | Pause/Resume cleaning |
| `S` | Open the selector interface |
| `R` | Generate a cleaning report |
| `H` | Show safety guidelines |

## 🔒 Safety First

DeepClean incorporates multiple safety mechanisms to protect your data:

- **Protected Patterns**: Over 50 patterns that prevent deletion of important files
- **Recent File Protection**: Files modified within the last 7 days (configurable) are preserved
- **System File Detection**: Critical system files are automatically protected
- **Permission Checks**: Files with special permissions are never deleted
- **Dry Run Mode**: Always test with `--dry-run` before actual cleaning

## ⚙️ Configuration

You can customize DeepClean by creating a `config.json` file:

```json
{
    "paths": {
        "cache": [
            "~/Library/Caches/",
            "~/.cache/"
        ],
        "temp": [
            "/tmp/",
            "/var/tmp/"
        ],
        "custom": [
            "~/path/to/custom/directory"
        ]
    },
    "protected": [
        "**/important-files/**",
        "**/*.keep",
        "**/critical-data/**"
    ],
    "options": {
        "min_file_age_days": 14,
        "clean_empty_dirs": true
    }
}
```

## 🔧 Troubleshooting

If you encounter any issues:

1. **Check the log file**: Review `deepclean.log` for detailed error information
2. **Use dry-run mode**: Run with `--dry-run` to safely test functionality
3. **Permission issues**: Ensure you have proper permissions for directories being cleaned
4. **Dependency problems**: Run `pip install -r requirements.txt` to reinstall dependencies
5. **Terminal issues**: Try `--simple-output` flag for better compatibility with smaller terminals

## 📊 Understanding Reports

DeepClean generates comprehensive reports that include:

- Files analyzed and cleaned
- Total space saved
- Protected and skipped files
- Detailed operations log
- System information
- Errors encountered (if any)

Reports are saved in the `reports/` directory with timestamps.

## 📝 License

This project is released under the MIT License. See the LICENSE file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request or open an Issue.

## 📢 Disclaimer

While DeepClean is designed to be safe, always back up important data before performing system cleaning operations. Use at your own risk. 