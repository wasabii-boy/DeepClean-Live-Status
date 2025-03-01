#!/bin/bash
#
# DeepClean Startup Script
# A modern system cleaning utility for safely removing unnecessary files
# Version: 1.1.0
#

# Terminal colors for better readability
BOLD='\033[1m'
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Script configuration
VENV_DIR="venv"
PYTHON_MIN_VERSION="3.6"
REQUIRED_PACKAGES="rich psutil pathspec"
APP_SCRIPT="deepclean.py"

# Display banner
print_banner() {
    echo -e "${BLUE}${BOLD}"
    echo "======================================================================"
    echo "                    DeepClean System Cleaner Tool                     "
    echo "======================================================================"
    echo -e "${NC}"
    echo -e "${GREEN}Safely clean caches, temporary files, and free up disk space${NC}"
    echo
}

# Display usage information
print_usage() {
    echo -e "${CYAN}${BOLD}Common usage examples:${NC}"
    echo -e "  ${BOLD}./start_deepclean.sh --dry-run${NC}                   - Simulate cleaning (recommended first run)"
    echo -e "  ${BOLD}./start_deepclean.sh --selector${NC}                  - Show interactive cleaning selector"
    echo -e "  ${BOLD}./start_deepclean.sh --clean-temp-files --dry-run${NC} - Simulate cleaning temporary files"
    echo -e "  ${BOLD}./start_deepclean.sh --generate-report${NC}           - Clean and generate detailed report"
    echo
    echo -e "${YELLOW}${BOLD}SAFETY NOTICE:${NC} Always use ${BOLD}--dry-run${NC} first to preview changes!"
    echo
}

# Print keyboard controls
print_controls() {
    echo -e "${CYAN}${BOLD}Keyboard controls:${NC}"
    echo -e "  ${BOLD}Q${NC} - Quit the application"
    echo -e "  ${BOLD}P${NC} - Pause/resume cleaning"
    echo -e "  ${BOLD}S${NC} - Open the selector interface"
    echo -e "  ${BOLD}R${NC} - Generate a report"
    echo -e "  ${BOLD}H${NC} - Show safety guide"
    echo
}

# Check terminal capabilities
check_terminal() {
    if [ -t 0 ]; then
        # Running in a terminal, ensure TERM is set
        if [ -z "$TERM" ] || [ "$TERM" = "dumb" ]; then
            export TERM=xterm
        fi
        INTERACTIVE=true
    else
        echo -e "${YELLOW}Warning: Not running in a terminal. Keyboard controls may be limited.${NC}"
        INTERACTIVE=false
    fi
}

# Cleanup function for proper exit
cleanup() {
    if [ "$INTERACTIVE" = true ]; then
        echo -e "\n${GREEN}Terminal settings restored.${NC}"
    fi
    
    # Kill any background processes we created
    if [ -n "$KEYBOARD_PID" ]; then
        kill $KEYBOARD_PID 2>/dev/null || true
    fi
}

# Check Python version
check_python_version() {
    if ! command -v python3 &> /dev/null; then
        if ! command -v python &> /dev/null; then
            echo -e "${RED}Error: Python not found. Please install Python ${PYTHON_MIN_VERSION} or higher.${NC}"
            exit 1
        fi
        PYTHON_CMD="python"
    else
        PYTHON_CMD="python3"
    fi
    
    # Get Python version
    PY_VERSION=$($PYTHON_CMD --version 2>&1 | cut -d' ' -f2)
    echo -e "${CYAN}Detected Python: $PY_VERSION${NC}"
    
    # Compare versions (simplified check)
    PY_MAJOR=$(echo $PY_VERSION | cut -d. -f1)
    PY_MINOR=$(echo $PY_VERSION | cut -d. -f2)
    MIN_MAJOR=$(echo $PYTHON_MIN_VERSION | cut -d. -f1)
    MIN_MINOR=$(echo $PYTHON_MIN_VERSION | cut -d. -f2)
    
    if [ "$PY_MAJOR" -lt "$MIN_MAJOR" ] || ([ "$PY_MAJOR" -eq "$MIN_MAJOR" ] && [ "$PY_MINOR" -lt "$MIN_MINOR" ]); then
        echo -e "${RED}Error: Python ${PYTHON_MIN_VERSION} or higher is required.${NC}"
        echo -e "${RED}Current version: $PY_VERSION${NC}"
        exit 1
    fi
}

# Set up Python virtual environment
setup_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        echo -e "${YELLOW}Creating virtual environment...${NC}"
        $PYTHON_CMD -m venv "$VENV_DIR"
        if [ $? -ne 0 ]; then
            echo -e "${RED}Error: Failed to create virtual environment.${NC}"
            echo -e "${YELLOW}You may need to install the venv module:${NC}"
            echo -e "  $PYTHON_CMD -m pip install --user virtualenv"
            exit 1
        fi
    fi
    
    # Activate virtual environment
    if [ -f "$VENV_DIR/bin/activate" ]; then
        source "$VENV_DIR/bin/activate"
        echo -e "${GREEN}Using virtual environment: $VENV_DIR${NC}"
    elif [ -f "$VENV_DIR/Scripts/activate" ]; then
        source "$VENV_DIR/Scripts/activate"
        echo -e "${GREEN}Using virtual environment: $VENV_DIR${NC}"
    else
        echo -e "${YELLOW}Warning: Could not activate virtual environment.${NC}"
        echo -e "${YELLOW}Using system Python instead.${NC}"
    fi
}

# Install required dependencies
install_dependencies() {
    echo -e "${CYAN}Checking dependencies...${NC}"
    
    # Check if pip is available
    if ! command -v pip &> /dev/null; then
        echo -e "${RED}Error: pip not found. Please install pip.${NC}"
        exit 1
    fi
    
    # Check if dependencies are installed
    if ! python -c "import rich, psutil, pathspec" 2>/dev/null; then
        echo -e "${YELLOW}Installing required dependencies...${NC}"
        pip install $REQUIRED_PACKAGES
        
        # Verify installation
        if ! python -c "import rich, psutil, pathspec" 2>/dev/null; then
            echo -e "${RED}Error: Failed to install dependencies.${NC}"
            echo -e "${RED}Please install them manually:${NC}"
            echo -e "  pip install $REQUIRED_PACKAGES"
            exit 1
        fi
        
        echo -e "${GREEN}Dependencies installed successfully.${NC}"
    else
        echo -e "${GREEN}All required dependencies are satisfied.${NC}"
    fi
}

# Check if the DeepClean script exists
check_script() {
    if [ ! -f "$APP_SCRIPT" ]; then
        echo -e "${RED}Error: $APP_SCRIPT not found.${NC}"
        echo -e "${RED}Make sure you're in the correct directory.${NC}"
        exit 1
    fi
}

# Main execution flow
main() {
    # Register cleanup on exit
    trap cleanup EXIT SIGINT SIGTERM
    
    # Display information
    print_banner
    check_terminal
    print_controls
    print_usage
    
    # Environment setup
    check_python_version
    setup_venv
    install_dependencies
    check_script
    
    # Start the application
    echo -e "${CYAN}${BOLD}Starting DeepClean...${NC}"
    
    # Pass all arguments to the DeepClean script
    if [ "$INTERACTIVE" = true ]; then
        echo -e "${GREEN}Running in interactive terminal mode.${NC}"
        python "$APP_SCRIPT" "$@"
    else
        echo -e "${YELLOW}Running in non-interactive mode.${NC}"
        python "$APP_SCRIPT" "$@" --simple-output
    fi
    
    # Script completed
    if [ $? -eq 0 ]; then
        echo -e "\n${GREEN}${BOLD}DeepClean completed successfully.${NC}"
    else
        echo -e "\n${YELLOW}${BOLD}DeepClean exited with issues. Check the log for details.${NC}"
    fi
}

# Execute main function
main "$@" 