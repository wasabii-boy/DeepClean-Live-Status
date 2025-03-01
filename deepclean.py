#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DeepClean - A deep cleaner for unnecessary files with Rich-based console interface
"""

import argparse
import hashlib
import glob
import json
import logging
import math
import os
import signal
import stat
import sys
import tempfile
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

# Add current directory to path to ensure module imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Dependency check at startup
DEPENDENCIES = {
    "psutil": "For monitoring system resources",
    "rich": "For rich display in the terminal",
    "pathspec": "For handling exclusion patterns",
}


def check_dependencies():
    """Checks that all dependencies are available and displays a helpful message if not"""
    missing = []

    for module, description in DEPENDENCIES.items():
        try:
            __import__(module)
        except ImportError:
            missing.append((module, description))

    if missing:
        print("\n" + "=" * 60)
        print("MISSING DEPENDENCIES ERROR")
        print("=" * 60)
        print("\nDeepClean needs the following missing Python modules:")
        for module, description in missing:
            print(f"  - {module}: {description}")

        print("\nYou can install them with the following command:")
        print("  pip install --user " + " ".join(m[0] for m in missing))
        print("\nOr use the start_deepclean.sh script which will handle dependencies for you.")
        print("=" * 60 + "\n")
        sys.exit(1)


# Check dependencies before continuing
check_dependencies()

# Import dependencies after verification
import psutil
from pathspec import PathSpec
from pathspec.patterns import GitWildMatchPattern
from rich.align import Align
from rich.box import ROUNDED
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# Initialize logging early
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filename="deepclean.log",
    filemode="w",
)
logger = logging.getLogger("DeepClean")

# Initialize console with proper terminal detection
console = Console(highlight=False, log_path=False, legacy_windows=True)


# Function to check terminal capabilities
def check_terminal_capabilities():
    """Check terminal capabilities and log warnings"""
    import shutil

    terminal_width, terminal_height = shutil.get_terminal_size()
    term = os.environ.get("TERM", "unknown")
    is_terminal = os.isatty(sys.stdout.fileno()) if hasattr(sys.stdout, "fileno") else False

    # Log terminal information
    logger.info(f"Terminal type: {term}")
    logger.info(f"Terminal size: {terminal_width}x{terminal_height}")
    logger.info(f"Is running in a terminal: {is_terminal}")

    # Check for potential issues
    if terminal_width < 80 or terminal_height < 24:
        print("WARNING: Terminal size is too small. Minimum recommended size: 80x24")
        print(f"Current terminal size: {terminal_width}x{terminal_height}")
        logger.warning(f"Terminal size too small: {terminal_width}x{terminal_height}")

    if term.lower() in ["dumb", "unknown"]:
        print("WARNING: Limited terminal capabilities detected.")
        print("The rich interface may not display correctly.")
        logger.warning(f"Limited terminal capabilities: {term}")

    return is_terminal


# Import our cleaner selector module
try:
    import cleaner_selector
except ImportError:
    print("Warning: Cleaner selector module not found. Running with default paths.")
    print("Make sure cleaner_selector.py is in the same directory as deepclean.py")
    cleaner_selector = None

# Call terminal check function
FULL_UI_SUPPORTED = check_terminal_capabilities()

# Import our safety guide module (with fallback if not available)
try:
    import safety_guide

    SAFETY_GUIDE_AVAILABLE = True
except ImportError:
    SAFETY_GUIDE_AVAILABLE = False
    print("Safety guide module not found. Safety features will be disabled.")

# Default paths to clean
DEFAULT_PATHS = {
    "cache": [
        "~/Library/Caches/",
        "~/.cache/",
    ],
    "temp": [
        "/tmp/",
        "/var/tmp/",
    ],
    "package_managers": [
        "~/.npm/_cacache",
        "~/.yarn/cache",
        "~/.gradle/caches",
        "~/.nuget/packages",
        "~/.pip/cache",
        "~/.cargo/registry/cache",
    ],
    "logs": [
        "~/Library/Logs/",
        "/var/log/",
    ],
}

# Files and directories to protect (never delete)
PROTECTED_PATTERNS = [
    # System and important user directories
    "**/.git/**",
    "**/node_modules/**",
    "**/Documents/**",
    "**/Pictures/**",
    "**/Music/**",
    "**/Videos/**",
    "**/Movies/**",
    "**/Downloads/**",
    "**/Desktop/**",
    "**/Applications/**",
    "**/Library/Application Support/**",
    "**/Library/Preferences/**",
    "**/System/**",
    "**/private/var/db/**",
    "**/usr/local/bin/**",
    # Code source and configuration files
    "**/*.py",
    "**/*.js",
    "**/*.java",
    "**/*.c",
    "**/*.cpp",
    "**/*.h",
    "**/*.swift",
    "**/*.go",
    "**/*.rs",
    "**/*.php",
    "**/*.rb",
    "**/*.html",
    "**/*.css",
    "**/*.scss",
    "**/*.sass",
    "**/*.less",
    "**/*.md",
    "**/*.txt",
    "**/*.json",
    "**/*.xml",
    "**/*.yaml",
    "**/*.yml",
    "**/*.toml",
    "**/*.ini",
    "**/*.conf",
    "**/*.cfg",
    # Project and documentation files
    "**/package.json",
    "**/requirements.txt",
    "**/Gemfile",
    "**/Cargo.toml",
    "**/pom.xml",
    "**/build.gradle",
    "**/Makefile",
    "**/README*",
    "**/LICENSE*",
    "**/CHANGELOG*",
    # Database and important files
    "**/*.db",
    "**/*.sqlite",
    "**/*.sqlite3",
    "**/*.plist",
    "**/*.key",
    "**/*.pem",
    "**/*.crt",
    "**/*.cer",
    "**/*.p12",
    "**/*.keychain",
    "**/*.password*",
    "**/*.secret*",
    "**/id_rsa*",
    "**/id_ed25519*",
    "**/known_hosts",
    "**/.ssh/**",
]


class FileProtection:
    """Class to handle file protection"""

    @staticmethod
    def is_recently_modified(path, days=7):
        """Checks if a file has been modified recently"""
        try:
            mtime = os.path.getmtime(path)
            file_time = datetime.fromtimestamp(mtime)
            return datetime.now() - file_time < timedelta(days=days)
        except (OSError, FileNotFoundError):
            return False

    @staticmethod
    def is_system_file(path):
        """Checks if a file is a critical system file"""
        system_dirs = [
            "/System",
            "/Library/StartupItems",
            "/Library/LaunchAgents",
            "/Library/LaunchDaemons",
            "/private/var/db/dslocal",
            "/usr/bin",
            "/usr/sbin",
            "/usr/libexec",
            "/usr/share",
            "/usr/lib",
            "/bin",
            "/sbin",
        ]

        return any(path.startswith(d) for d in system_dirs)

    @staticmethod
    def is_hidden_file(path):
        """Checks if a file is hidden"""
        return os.path.basename(path).startswith(".")

    @staticmethod
    def is_special_file(path):
        """Checks if a file has special permissions"""
        try:
            file_stat = os.stat(path)
            return bool(file_stat.st_mode & (stat.S_ISUID | stat.S_ISGID))
        except (OSError, FileNotFoundError):
            return False

    @staticmethod
    def compute_file_hash(path):
        """Calculates the hash of a file to detect duplicates"""
        try:
            with open(path, "rb") as f:
                file_hash = hashlib.md5()
                chunk = f.read(8192)
                while chunk:
                    file_hash.update(chunk)
                    chunk = f.read(8192)
                return file_hash.hexdigest()
        except (OSError, FileNotFoundError):
            return None


class DeepClean:
    """Main DeepClean Application"""

    def __init__(self, args):
        """Initialize the application with arguments"""
        self.args = args
        self.console = console

        # Initialize stats
        self.stats = {
            "analyzed_files": 0,
            "analyzed_dirs": 0,
            "cleaned_files": 0,
            "cleaned_dirs": 0,
            "cleaned_size": 0,
            "protected_files": 0,
            "skipped_recent_files": 0,
            "errors": 0,
            "start_time": time.time(),
        }

        # Initialize logs
        self.operations_log = []
        self.errors_log = []

        # Initialize state
        self.current_operation = "Initializing"
        self.last_cleaned = ""
        self.processing_event = threading.Event()
        self.processing_event.set()  # Started by default
        self.is_paused = False
        self.is_cleaning = False
        self.should_exit = False
        self.progress_percent = 0  # Initialize progress
        self.current_path_risk = "Low"  # Track risk level of current operation
        self.interrupt_flag = False  # Flag to indicate user interruption

        # Initialize file protections
        self.pathspec = PathSpec.from_lines(GitWildMatchPattern, PROTECTED_PATTERNS)
        self.file_protection = FileProtection()
        self.known_file_hashes = {}  # For detecting duplicates
        self.seen_file_hashes = {}  # For detecting duplicates

        # Initialize paths to clean
        self.paths_to_clean = DEFAULT_PATHS.copy()
        self.pattern_to_clean = {}

        # Setup signal handlers
        signal.signal(signal.SIGINT, self.handle_interrupt)

        # Setup rich layout
        self.setup_layout()

        # If the cleaner selector and --selector flag are available, show selector before starting
        if cleaner_selector and args.selector:
            self.should_show_selector = True
        else:
            self.should_show_selector = False

    def setup_layout(self):
        """Setup Rich layout for the interface"""
        self.layout = Layout()

        # Create the main sections with fixed sizes for header and footer
        self.layout.split(
            Layout(name="header", size=3), Layout(name="body"), Layout(name="footer", size=3)
        )

        # Split the body into sections with balanced ratios
        self.layout["body"].split_row(
            Layout(name="left", ratio=1),
            Layout(name="right", ratio=1),
        )

        # Split the left column
        self.layout["left"].split(
            Layout(name="stats", ratio=1),
            Layout(name="errors", ratio=2),
        )

        # Split the right column - Add a dedicated progress section
        if SAFETY_GUIDE_AVAILABLE:
            self.layout["right"].split(
                Layout(name="progress", size=6),
                Layout(name="status", ratio=1),
                Layout(name="safety", ratio=1),
                Layout(name="operations", ratio=2),
            )
        else:
            self.layout["right"].split(
                Layout(name="progress", size=6),
                Layout(name="status", ratio=1),
                Layout(name="operations", ratio=2),
            )

        # Initialize real-time cleaning stats
        self.current_file_size = 0
        self.current_speed = 0  # bytes per second
        self.avg_speed = 0
        self.estimated_time = "calculating..."
        self.last_update_time = time.time()
        self.last_size = 0
        self.last_progress_update = 0

    def update_layout(self):
        """Update the layout with current data"""
        # Make sure logs are initialized
        if not hasattr(self, "operations_log"):
            self.operations_log = []
        if not hasattr(self, "errors_log"):
            self.errors_log = []

        # Update header - simplified, no padding
        header = Panel(
            Align.center("[bold]🧹 DeepClean[/bold] - System Cleaner"),
            style="blue",
            border_style="blue",
            padding=0,
        )

        # Update stats panel - even more compact
        stats_table = Table(box=ROUNDED, expand=True, show_header=False, padding=(0, 1))
        stats_table.add_column("Metric", style="cyan")
        stats_table.add_column("Value", style="white")

        # Display only the most relevant stats in a logical order
        important_stats = [
            "cleaned_files",
            "cleaned_size",
            "analyzed_files",
            "protected_files",
            "skipped_recent_files",
            "errors",
        ]

        for key in important_stats:
            if key in self.stats:
                value = self.stats[key]
                emoji = "📊"
                if key == "cleaned_files":
                    emoji = "🧹"
                elif key == "cleaned_size":
                    emoji = "📦"
                elif key == "analyzed_files":
                    emoji = "🔍"
                elif key == "protected_files":
                    emoji = "🔒"
                elif key == "skipped_recent_files":
                    emoji = "⏱️"
                elif key == "errors":
                    emoji = "⚠️"

                if key == "cleaned_size":
                    stats_table.add_row(f"{emoji} {key}", self.format_size(value))
                else:
                    stats_table.add_row(f"{emoji} {key}", str(value))

        # Add real-time metrics
        if self.is_cleaning and not self.is_paused:
            stats_table.add_row("", "")
            stats_table.add_row(
                "[bold cyan]⚡ Current Speed[/bold cyan]",
                f"{self.format_size(self.current_speed)}/s",
            )
            stats_table.add_row("[bold cyan]⏱️ Est. Remaining[/bold cyan]", self.estimated_time)

        stats_panel = Panel(
            stats_table, title="[bold]📈 Statistics[/bold]", border_style="green", padding=0
        )

        # Update errors panel - keep to most recent errors with better formatting
        if self.errors_log:
            errors_content = ""
            for i, error in enumerate(self.errors_log[-8:]):  # Limit to 8 most recent errors
                if i > 0:
                    errors_content += "\n"
                errors_content += error
            errors_text = Text.from_markup(errors_content)
        else:
            errors_text = Text("🔍 No errors or warnings")

        errors_panel = Panel(
            errors_text, title="[bold]⚠️ Errors & Warnings[/bold]", border_style="red", padding=0
        )

        # Create a dedicated progress panel with animated bar
        progress_panel = self.create_progress_panel()

        # Add pause indicator to status
        pause_indicator = (
            "[bold red]⏸️ PAUSED[/bold red]"
            if self.is_paused
            else "[bold green]▶️ RUNNING[/bold green]"
        )

        # Update status panel with more compact layout
        mode_indicator = (
            "[bold yellow]🔍 Simulation[/bold yellow]"
            if self.args.dry_run
            else "[bold red]🗑️ Delete[/bold red]"
        )

        # Format last cleaned path more nicely
        last_cleaned = ""
        if self.last_cleaned:
            # Show only the basename of the last cleaned file with proper truncation
            last_file = os.path.basename(self.last_cleaned)
            if len(last_file) > 25:
                last_file = last_file[:22] + "..."
            last_cleaned = last_file

        # Create status content as a formatted string
        status_string = f"{pause_indicator}\n"
        status_string += f"[bold white]🔄 Current:[/bold white] {self.current_operation[:30]}\n"
        status_string += f"[bold white]🧹 Last cleaned:[/bold white] {last_cleaned}\n"

        # Add more real-time stats in the status panel
        status_string += f"[bold white]📂 Current file:[/bold white] {self.format_size(self.current_file_size)}\n"
        elapsed = time.time() - self.stats["start_time"]
        status_string += f"[bold white]⏱️ Elapsed:[/bold white] {self.format_time(elapsed)}\n"

        # Add system stats
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        status_string += f"[bold white]💾 Memory:[/bold white] {memory.percent}%\n"
        status_string += f"[bold white]💽 Disk:[/bold white] {disk.percent}%\n"
        status_string += f"[bold white]🔧 Mode:[/bold white] {mode_indicator}"

        status_panel = Panel(
            Text.from_markup(status_string),
            title="[bold]📊 Status[/bold]",
            border_style="cyan",
            padding=0,
        )

        # Update operations panel - format operations more cleanly
        if self.operations_log:
            ops_content = ""
            for i, op in enumerate(self.operations_log[-12:]):  # Limit to 12 most recent operations
                if i > 0:
                    ops_content += "\n"
                ops_content += op
            operations_text = Text.from_markup(ops_content)
        else:
            operations_text = Text("🔍 No operations yet")

        operations_panel = Panel(
            operations_text,
            title="[bold]🔄 Operations Log[/bold]",
            border_style="yellow",
            padding=0,
        )

        # Add safety panel if available
        if SAFETY_GUIDE_AVAILABLE:
            # Create safety panel based on current operation
            safety_panel = self.create_safety_panel()
            self.layout["safety"].update(safety_panel)
        else:
            # Create a placeholder safety panel with basic tips
            basic_tips = (
                "[bold]Basic Safety Tips[/bold]\n\n"
                "• [cyan]Always run with --dry-run first[/cyan]\n"
                "• [cyan]Close applications before cleaning their caches[/cyan]\n"
                "• [cyan]Back up important data before deep cleaning[/cyan]"
            )
            safety_panel = Panel(
                Text.from_markup(basic_tips),
                title="[bold]⚠️ Safety Guide[/bold]",
                border_style="teal",
                padding=0,
            )
            self.layout["safety"].update(safety_panel)

        # Update footer with clearer command display
        commands = "[bold blue]Q[/bold blue]:Quit | [bold blue]P[/bold blue]:Pause | [bold blue]S[/bold blue]:Selector | [bold blue]R[/bold blue]:Report | [bold blue]H[/bold blue]:Safety"
        footer = Panel(
            Align.center(Text.from_markup(f"⌨️ {commands}")),
            style="bold",
            border_style="blue",
            padding=0,
        )

        # Assign panels to layout
        self.layout["header"].update(header)
        self.layout["stats"].update(stats_panel)
        self.layout["errors"].update(errors_panel)
        self.layout["progress"].update(progress_panel)
        self.layout["status"].update(status_panel)
        self.layout["operations"].update(operations_panel)
        self.layout["footer"].update(footer)

    def create_progress_panel(self):
        """Create a dedicated progress panel with more detail"""
        # Calculate how much of the progress bar to fill
        filled_char = "█"
        empty_char = "░"
        bar_width = 50  # Wider progress bar for better visualization

        # Add pulsing effect when paused
        if self.is_paused:
            # Create a pulsing effect for the progress bar when paused
            pulse_index = int(time.time() * 2) % bar_width
            filled = min(int(self.progress_percent / 100 * bar_width), bar_width)
            bar = ""
            for i in range(bar_width):
                if i < filled:
                    bar += "[bold cyan]" + filled_char + "[/]"
                elif i == pulse_index:
                    bar += "[bold yellow]" + filled_char + "[/]"
                else:
                    bar += "[dim]" + empty_char + "[/]"
        else:
            # Standard progress bar when running
            filled = min(int(self.progress_percent / 100 * bar_width), bar_width)
            bar = (
                "[bold cyan]"
                + filled_char * filled
                + "[/][dim]"
                + empty_char * (bar_width - filled)
                + "[/]"
            )

        # Progress heading with percentage
        progress_heading = f"[bold]Progress: {self.progress_percent:.1f}%[/]"

        # Create a visually engaging progress display
        if self.is_cleaning and not self.is_paused:
            # Show an animated cleaning indicator
            spinner_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
            spinner = spinner_frames[int(time.time() * 10) % len(spinner_frames)]

            progress_text = f"{progress_heading}\n\n"
            progress_text += f"{bar}\n\n"
            progress_text += f"[bold cyan]{spinner} Cleaning in progress...[/]\n"

            # Add details about the current operation
            if self.current_operation:
                progress_text += f"[cyan]Current operation: {self.current_operation[:40]}[/]\n"

            # Add detailed stats
            progress_text += f"Speed: {self.format_size(self.current_speed)}/s | "
            progress_text += f"Remaining: {self.estimated_time}"
        elif self.is_paused:
            progress_text = f"{progress_heading}\n\n"
            progress_text += f"{bar}\n\n"
            progress_text += f"[bold yellow]⏸️ Cleaning paused. Press P to resume.[/]"
        elif self.is_cleaning:
            progress_text = f"{progress_heading}\n\n"
            progress_text += f"{bar}\n\n"
            progress_text += f"[bold yellow]Waiting to start...[/]"
        else:
            # Completed or not started
            if self.progress_percent >= 100:
                progress_text = f"{progress_heading}\n\n"
                progress_text += f"{bar}\n\n"
                progress_text += f"[bold green]✓ Cleaning completed![/]"
            else:
                progress_text = f"{progress_heading}\n\n"
                progress_text += f"{bar}\n\n"
                progress_text += f"[bold]Ready to start cleaning[/]"

        return Panel(
            Text.from_markup(progress_text),
            title="[bold]📊 Cleaning Progress[/bold]",
            border_style="cyan",
            padding=0,
        )

    def create_safety_panel(self):
        """Create the safety information panel based on current operation"""
        if not SAFETY_GUIDE_AVAILABLE:
            return Panel("Safety information not available", title="Safety", border_style="cyan")

        # Determine content based on current operation
        if self.is_cleaning and self.current_operation:
            # Extract category from operation text
            category = None
            operation_text = self.current_operation.lower()

            if "system cache" in operation_text or "~/library/caches" in operation_text:
                category = "system_cache"
            elif "temp" in operation_text:
                category = "temp"
            elif "log" in operation_text:
                category = "logs"
            elif "package" in operation_text or "npm" in operation_text or "pip" in operation_text:
                category = "package_managers"
            elif (
                "browser" in operation_text
                or "chrome" in operation_text
                or "firefox" in operation_text
            ):
                category = "browsers"
            elif "ide" in operation_text or "vscode" in operation_text or "xcode" in operation_text:
                category = "editors_and_ides"
            elif "docker" in operation_text or "kube" in operation_text:
                category = "docker"

            # Create safety content based on the current path
            safety_content = ""
            if self.last_cleaned:
                risk_level, risk_desc = safety_guide.get_risk_level(self.last_cleaned)
                tips = safety_guide.get_safety_tips(self.last_cleaned)

                risk_color = (
                    "red"
                    if risk_level == "high"
                    else "yellow" if risk_level == "medium" else "green"
                )

                safety_content = f"[bold]Path Safety Information[/bold]\n"
                safety_content += f"[{risk_color}]Risk Level: {risk_level.upper()}[/{risk_color}]\n"
                safety_content += f"{risk_desc}\n\n"

                if tips:
                    safety_content += "[bold cyan]Safety Tips:[/bold cyan]\n"
                    for tip in tips[:3]:  # Show top 3 tips
                        safety_content += f"• [cyan]{tip}[/cyan]\n"
            else:
                # Default safety information
                safety_content = "[bold]Safety Information[/bold]\n"
                safety_content += f"[cyan]Current Risk Level: {self.current_path_risk}[/cyan]\n\n"
                safety_content += "• [cyan]Close applications before cleaning their caches[/cyan]\n"
                safety_content += "• [cyan]Consider using dry-run mode first[/cyan]\n"
                safety_content += "• [cyan]Press H to view detailed safety guidelines[/cyan]"
        else:
            # Show general safety tips when not cleaning
            safety_content = "[bold]Safety Tips[/bold]\n\n"
            safety_content += "• [cyan]Always run in dry-run mode first[/cyan]\n"
            safety_content += "• [cyan]Close applications before cleaning[/cyan]\n"
            safety_content += "• [cyan]Back up important data[/cyan]\n"
            safety_content += "• [cyan]Press H to view detailed safety guides[/cyan]"

        return Panel(
            Text.from_markup(safety_content),
            title="[bold]⚠️ Safety Guide[/bold]",
            border_style="teal",
            padding=0,
        )

    def format_time(self, seconds):
        """Format time in a human-readable format"""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}m"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}h"

    def update_progress(self, percent, current_path=None, file_size=0):
        """Update progress percentage and related metrics"""
        self.progress_percent = min(percent, 100)  # Ensure it doesn't exceed 100%

        # Update current file size
        if file_size > 0:
            self.current_file_size = file_size

        # Calculate cleaning speed
        now = time.time()
        time_diff = now - self.last_update_time

        if time_diff >= 0.5:  # Update every half second for smoother animations
            size_diff = self.stats["cleaned_size"] - self.last_size

            if time_diff > 0 and size_diff > 0:
                # Calculate current speed
                self.current_speed = size_diff / time_diff

                # Update average speed with smoothing
                if self.avg_speed == 0:
                    self.avg_speed = self.current_speed
                else:
                    # Exponential moving average
                    self.avg_speed = 0.8 * self.avg_speed + 0.2 * self.current_speed

                # Estimate remaining time
                if self.avg_speed > 0 and self.progress_percent < 100:
                    # Estimate total size based on progress
                    total_estimated_size = self.stats["cleaned_size"] / (
                        self.progress_percent / 100
                    )
                    remaining_size = total_estimated_size - self.stats["cleaned_size"]

                    if remaining_size > 0:
                        remaining_seconds = remaining_size / self.avg_speed
                        self.estimated_time = self.format_time(remaining_seconds)
                    else:
                        self.estimated_time = "almost done"
                else:
                    self.estimated_time = "calculating..."

            # Save current values for next update
            self.last_update_time = now
            self.last_size = self.stats["cleaned_size"]

    def clean_directory(self, directory, pattern=None):
        """
        Clean a directory by removing files based on pattern
        """
        try:
            directory = self.expand_path(directory)
            if not os.path.exists(directory):
                return 0

            # Use pathlib for better path operations
            dir_path = Path(directory)
            if not dir_path.is_dir():
                return 0

            total_freed = 0
            file_count = 0
            self.update_status(f"Scanning {directory}")

            # Get all files in directory
            for file_path in dir_path.rglob("*"):
                if self.interrupt_flag:
                    self.log_error("Operation interrupted by user")
                    break

                if not file_path.is_file():
                    continue

                # Convert to string for compatibility with older functions
                file_path_str = str(file_path)

                # Skip protected files
                if self.is_protected(file_path_str):
                    self.stats["protected_files"] += 1
                    continue

                # Skip recently modified files
                if FileProtection.is_recently_modified(file_path_str, days=7):
                    self.stats["skipped_recent_files"] += 1
                    continue

                # Skip if doesn't match pattern
                if pattern and not any(ext in file_path_str.lower() for ext in pattern):
                    continue

                file_size = 0
                try:
                    file_size = os.path.getsize(file_path_str)
                except (OSError, FileNotFoundError) as e:
                    self.log_error(f"Error getting size of {file_path_str}: {str(e)}")
                    continue

                # Update display
                self.update_progress(0, file_path_str, file_size)

                # If in dry run mode, just log
                if self.args.dry_run:
                    self.add_operation(
                        f"Would delete: {file_path_str} ({self.format_size(file_size)})"
                    )
                    continue

                # Delete the file
                try:
                    os.remove(file_path_str)
                    total_freed += file_size
                    file_count += 1
                    self.stats["deleted_files"] += 1
                    self.stats["freed_space"] += file_size
                    self.add_operation(f"Deleted: {file_path_str} ({self.format_size(file_size)})")
                except (OSError, PermissionError, FileNotFoundError) as e:
                    self.log_error(f"Error during deletion of {file_path_str}: {str(e)}")
                    self.stats["errors"] += 1

            return total_freed
        except (OSError, PermissionError) as e:
            self.log_error(f"Error during cleaning of {directory}: {str(e)}")
            self.stats["errors"] += 1
            return 0

    def start_cleaning(self):
        """Start the cleaning process"""
        # Mark that we are cleaning
        self.is_cleaning = True

        # Add a safety notice before starting
        if SAFETY_GUIDE_AVAILABLE:
            self.add_operation(
                "[bold yellow]⚠️ SAFETY NOTICE[/bold yellow]: Press H to view detailed safety guidelines"
            )
            self.add_operation(
                "[bold yellow]⚠️ SAFETY NOTICE[/bold yellow]: Consider using dry-run mode for safety (--dry-run)"
            )

        # Add info about dry-run mode
        if self.args.dry_run:
            self.add_operation(
                "[bold green]ℹ️ SIMULATION MODE[/bold green]: No files will be deleted"
            )
        else:
            self.add_operation(
                "[bold red]⚠️ DELETE MODE[/bold red]: Files will be permanently deleted"
            )

        self.add_operation("Starting cleaning process...")

        # Calculate estimated total size for better progress calculation
        self.estimate_total_size()

        # Clean by category
        total_paths = (
            sum(len(paths) for paths in self.paths_to_clean.values()) + 2
        )  # +2 for tempdir and clean_temp_files
        completed_paths = 0

        for category, paths in self.paths_to_clean.items():
            for path in paths:
                # Pause if necessary
                while not self.processing_event.is_set():
                    time.sleep(0.1)

                # Check for exit request
                if self.should_exit:
                    self.is_cleaning = False
                    self.add_operation("Cleaning process stopped by user")
                    return

                self.update_status(f"Cleaning of {category}: {path}")
                # Launch a cleaning task per path
                self.clean_directory(path)

                # Update progress
                completed_paths += 1
                progress = int(completed_paths * 100 / total_paths)
                self.update_progress(progress)
                self.add_operation(f"Progress: {progress}% - Completed path: {path}")

        # Cleaning system temporary files
        self.update_status("Cleaning system temporary files")
        try:
            tempdir = tempfile.gettempdir()
            self.clean_directory(tempdir)
        except Exception as e:
            self.log_error(f"Error during cleaning of temporary directory: {str(e)}")

        # Update progress
        completed_paths += 1
        progress = int(completed_paths * 100 / total_paths)
        self.update_progress(progress)
        self.add_operation(f"Progress: {progress}% - Completed temporary directory")

        # Cleaning known temporary file types
        if getattr(self.args, "clean_temp_files", True):
            self.update_status("Searching for current temporary files")
            # Get patterns from selector if available, or use defaults
            if self.pattern_to_clean and "temporary_files" in self.pattern_to_clean:
                temp_extensions = self.pattern_to_clean["temporary_files"]
            else:
                temp_extensions = ["tmp", "temp", "bak", "old", "swp", "dmp", "dump"]

            self.clean_by_extension(temp_extensions)

        # Update progress to 100%
        completed_paths += 1
        self.update_progress(100)
        self.add_operation(f"Progress: 100% - Cleaning completed")

        # Automatic report generation if option is enabled
        if getattr(self.args, "generate_report", False):
            self.generate_report()

        # Finish
        self.update_status("Finished")
        self.is_cleaning = False

        # Display a summary in the operations journal
        duration = time.time() - self.stats["start_time"]
        self.add_operation(f"Cleaning finished in {self.format_time(duration)}")
        self.add_operation(
            f"Cleaned files: {self.stats['cleaned_files']}, Size: {self.format_size(self.stats['cleaned_size'])}"
        )

    def estimate_total_size(self):
        """Estimate the total size of all paths to clean for better progress calculation"""
        self.add_operation("Analyzing paths to estimate total size...")
        estimated_total = 0
        scanned_count = 0

        # Sample some directories to estimate
        for category, paths in self.paths_to_clean.items():
            for path in paths:
                expanded_path = self.expand_path(path)
                if os.path.exists(expanded_path):
                    try:
                        # Quick size estimation - scan just the top level
                        total_size = 0
                        file_count = 0
                        if os.path.isdir(expanded_path):
                            for item in os.scandir(expanded_path):
                                if not self.is_protected(item.path):
                                    try:
                                        if item.is_file():
                                            total_size += item.stat().st_size
                                            file_count += 1
                                    except (OSError, PermissionError):
                                        pass

                        if file_count > 0:
                            estimated_total += total_size
                            scanned_count += 1
                            # Log only for large directories
                            if total_size > 1024 * 1024 * 10:  # 10MB
                                self.add_operation(
                                    f"Estimated size for {path}: {self.format_size(total_size)}"
                                )
                    except Exception:
                        pass

                # Limit the number of scanned paths to keep startup fast
                if scanned_count >= 5:
                    break

    def handle_interrupt(self, signum, frame):
        """Handle keyboard interrupt signal"""
        self.add_operation("[bold red]⚠️ Interrupt received. Cleaning will stop...[/bold red]")
        self.should_exit = True
        # No need to call sys.exit() here as we want a clean shutdown

    def setup_keyboard_signals(self):
        """Set up signal handlers for keyboard events"""
        # Already handled in __init__
        # This is a placeholder for additional signal setup if needed
        pass

    def log_terminal_info(self):
        """Log information about the terminal environment for debugging"""
        term = os.environ.get("TERM", "unknown")
        is_terminal = os.isatty(sys.stdout.fileno()) if hasattr(sys.stdout, "fileno") else False

        logger.info(f"Terminal type: {term}")
        logger.info(f"Is running in a terminal: {is_terminal}")
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Platform: {sys.platform}")

    def format_size(self, size_bytes):
        """Format file size in a human-readable format"""
        if size_bytes == 0:
            return "0.00 B"
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = int(math.log(size_bytes, 1024)) if size_bytes > 0 else 0
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s:.2f} {size_names[i]}"

    def add_operation(self, message):
        """Add a message to the operations log"""
        timestamp = datetime.now().strftime("[%H:%M:%S]")
        self.operations_log.append(f"{timestamp} {message}")
        logger.info(message)

    def log_error(self, message):
        """Log an error message"""
        timestamp = datetime.now().strftime("[%H:%M:%S]")
        self.errors_log.append(f"{timestamp} {message}")
        self.stats["errors"] += 1
        logger.error(message)

    def update_status(self, operation, current_file=None):
        """Update the current operation status"""
        self.current_operation = operation
        if current_file:
            self.last_cleaned = current_file

    def expand_path(self, path):
        """Expand a path with user directory and environment variables"""
        expanded = os.path.expanduser(path)
        expanded = os.path.expandvars(expanded)
        return expanded

    def is_protected(self, path):
        """Check if a path is protected and should not be deleted"""
        # Basic protection checks
        if not os.path.exists(path):
            return False

        # Check if path matches any of the protected patterns
        if self.pathspec.match_file(path):
            return True

        # Check for system files
        if self.file_protection.is_system_file(path):
            return True

        # Check for special permission files
        if self.file_protection.is_special_file(path):
            return True

        # Check for recently modified files if enabled
        if getattr(self.args, "protect_recent", True) and self.file_protection.is_recently_modified(
            path, self.args.min_file_age
        ):
            self.stats["skipped_recent_files"] += 1
            return True

        return False

    def show_selector(self):
        """Show the cleaner selector interface"""
        if cleaner_selector:
            self.update_status("Showing selector")
            selected = cleaner_selector.show_selector()
            if selected:
                if "paths" in selected:
                    self.paths_to_clean = selected["paths"]
                if "patterns" in selected:
                    self.pattern_to_clean = selected["patterns"]

    def clean_empty_directories(self, directory):
        """Clean empty directories recursively"""
        if not os.path.exists(directory) or not os.path.isdir(directory):
            return

        try:
            # Walk bottom-up to properly remove empty dirs
            for root, dirs, files in os.walk(directory, topdown=False):
                for d in dirs:
                    dir_path = os.path.join(root, d)

                    # Skip if protected
                    if self.is_protected(dir_path):
                        continue

                    try:
                        # Check if directory is empty (only considering non-protected files)
                        is_empty = True
                        for item in os.scandir(dir_path):
                            if not self.is_protected(item.path):
                                is_empty = False
                                break

                        if is_empty:
                            if not self.args.dry_run:
                                os.rmdir(dir_path)
                                self.add_operation(f"Deleted empty directory: {dir_path}")
                                self.stats["cleaned_dirs"] += 1
                            else:
                                self.add_operation(
                                    f"Simulation: Would delete empty directory: {dir_path}"
                                )
                                self.stats["cleaned_dirs"] += 1
                    except (OSError, PermissionError) as e:
                        self.log_error(
                            f"Error while checking/removing directory {dir_path}: {str(e)}"
                        )
        except Exception as e:
            self.log_error(f"Error during cleaning of empty directories in {directory}: {str(e)}")

    def clean_by_extension(self, extensions):
        """Clean files with specific extensions"""
        if not extensions:
            return

        self.update_status(f"Searching for files with extensions: {', '.join(extensions)}")

        # Get temporary directory for search
        temp_dir = tempfile.gettempdir()
        home_dir = os.path.expanduser("~")

        # Common places to look for temp files
        search_dirs = [
            temp_dir,
            os.path.join(home_dir, "Library", "Caches"),
            os.path.join(home_dir, ".cache"),
        ]

        for directory in search_dirs:
            if not os.path.exists(directory):
                continue

            # Search recursively for files with given extensions
            for ext in extensions:
                ext_pattern = f"*.{ext}"
                search_pattern = os.path.join(directory, "**", ext_pattern)

                # Find files using glob
                try:
                    for file_path in glob.glob(search_pattern, recursive=True):
                        # Skip if protected
                        if self.is_protected(file_path):
                            continue

                        # Get file size
                        try:
                            file_size = os.path.getsize(file_path)
                        except (OSError, FileNotFoundError):
                            file_size = 0

                        # Cleaning action
                        if not self.args.dry_run:
                            try:
                                os.remove(file_path)
                                self.stats["cleaned_files"] += 1
                                self.stats["cleaned_size"] += file_size
                                self.update_status(f"Cleaning temporary files", file_path)
                                self.add_operation(
                                    f"Deleted: {file_path} ({self.format_size(file_size)})"
                                )
                            except Exception as e:
                                self.log_error(f"Error during deletion of {file_path}: {str(e)}")
                        else:
                            # Simulation mode
                            self.stats["cleaned_files"] += 1
                            self.stats["cleaned_size"] += file_size
                            self.update_status(f"Simulation of cleaning temporary files", file_path)
                            self.add_operation(
                                f"Simulation: {file_path} ({self.format_size(file_size)})"
                            )
                except Exception as e:
                    self.log_error(f"Error searching for {ext_pattern} files: {str(e)}")

    def find_duplicates(self, file_path, file_size):
        """Check for duplicate files based on hash"""
        # Skip small files (< 10MB) for performance reasons
        if file_size < 10 * 1024 * 1024:
            return False

        file_hash = None
        try:
            file_hash = FileProtection.compute_file_hash(file_path)
        except (OSError, PermissionError, FileNotFoundError) as e:
            self.log_error(f"Error computing hash for {file_path}: {str(e)}")
            return False

        if not file_hash:
            return False

        # If we've seen this hash before
        if file_hash in self.seen_file_hashes:
            original_path = self.seen_file_hashes[file_hash]
            # Make sure the original file still exists
            if os.path.exists(original_path):
                self.stats["duplicate_files"] += 1
                self.add_operation(f"Found duplicate: {file_path} identical to {original_path}")
                return True

        # Add to seen hashes
        self.seen_file_hashes[file_hash] = file_path
        return False

    def generate_report(self):
        """Generate a detailed report of the cleaning operation"""
        self.update_status("Generating report")

        try:
            # Create report directory if it doesn't exist
            report_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
            if not os.path.exists(report_dir):
                os.makedirs(report_dir)

            # Generate a unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = os.path.join(report_dir, f"deepclean_report_{timestamp}.txt")

            # Write the report
            with open(report_file, "w") as f:
                f.write("=" * 80 + "\n")
                f.write(f"DeepClean Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 80 + "\n\n")

                # Write stats
                f.write("STATISTICS\n")
                f.write("-" * 80 + "\n")
                for key, value in self.stats.items():
                    if key == "cleaned_size":
                        f.write(f"{key}: {self.format_size(value)}\n")
                    elif key == "start_time":
                        duration = time.time() - value
                        f.write(f"duration: {self.format_time(duration)}\n")
                    else:
                        f.write(f"{key}: {value}\n")
                f.write("\n")

                # Write operations log
                f.write("OPERATIONS LOG\n")
                f.write("-" * 80 + "\n")
                for op in self.operations_log:
                    f.write(f"{op}\n")
                f.write("\n")

                # Write errors log if any
                if self.errors_log:
                    f.write("ERRORS LOG\n")
                    f.write("-" * 80 + "\n")
                    for err in self.errors_log:
                        f.write(f"{err}\n")
                    f.write("\n")

                # Write info about paths cleaned
                f.write("PATHS CLEANED\n")
                f.write("-" * 80 + "\n")
                for category, paths in self.paths_to_clean.items():
                    f.write(f"Category: {category}\n")
                    for path in paths:
                        f.write(f"  - {path}\n")
                f.write("\n")

                # Write system info
                f.write("SYSTEM INFORMATION\n")
                f.write("-" * 80 + "\n")
                f.write(f"Python version: {sys.version}\n")
                f.write(f"Platform: {sys.platform}\n")
                f.write(f"Total memory: {self.format_size(psutil.virtual_memory().total)}\n")
                f.write(f"Total disk: {self.format_size(psutil.disk_usage('/').total)}\n")
                f.write("\n")

                # Write a footer
                f.write("=" * 80 + "\n")
                f.write("End of report\n")
                f.write("=" * 80 + "\n")

            # Add operation log entry
            self.add_operation(f"Report generated: {report_file}")

            # Open the report if possible
            if not self.args.dry_run and not getattr(self.args, "no_open_report", False):
                try:
                    if sys.platform == "darwin":  # macOS
                        os.system(f"open {report_file}")
                    elif sys.platform.startswith("linux"):  # Linux
                        os.system(f"xdg-open {report_file}")
                    elif sys.platform == "win32":  # Windows
                        os.system(f"start {report_file}")
                except Exception:
                    pass

        except Exception as e:
            self.log_error(f"Error generating report: {str(e)}")

    def run(self):
        """Run the application"""
        # If selector is enabled, show it first
        if self.should_show_selector:
            self.show_selector()

        # Log information about the terminal environment for debugging
        self.log_terminal_info()

        # Register keyboard event handler with signal
        self.setup_keyboard_signals()

        # Start main loop
        self.add_operation("🚀 DeepClean started")

        # Check if we should use simple output mode
        use_simple_output = getattr(self.args, "simple_output", False)

        if use_simple_output:
            # Simple output mode without fancy UI
            self.run_simple_mode()
        else:
            # Rich interactive UI mode
            self.run_rich_mode()

        # Final stats message
        if self.stats["cleaned_files"] > 0:
            self.console.print(f"\n[bold green]Cleaning completed![/bold green]")
            self.console.print(f"Cleaned [bold]{self.stats['cleaned_files']}[/bold] files")
            self.console.print(
                f"Total size: [bold]{self.format_size(self.stats['cleaned_size'])}[/bold]"
            )
        else:
            self.console.print("\n[bold yellow]No files cleaned.[/bold yellow]")

        # Show errors if any
        if self.stats["errors"] > 0:
            self.console.print(f"\n[bold red]Encountered {self.stats['errors']} errors.[/bold red]")
            self.console.print("Check the log file for details.")

    def run_rich_mode(self):
        """Run the application with Rich interactive UI"""
        try:
            with Live(self.layout, refresh_per_second=5, screen=True) as live:
                # Start cleaning in a separate thread
                cleaning_thread = threading.Thread(target=self.start_cleaning)
                cleaning_thread.daemon = True
                cleaning_thread.start()

                # Main interface loop
                try:
                    while not self.should_exit and (
                        cleaning_thread.is_alive() or not self.is_cleaning
                    ):
                        # Update layout
                        self.update_layout()

                        # Small delay
                        time.sleep(0.2)

                    # Make sure to update one last time
                    self.update_layout()

                    # Add exit message
                    self.add_operation("👋 DeepClean exiting...")
                    self.update_layout()

                    # If we've been interrupted, wait a bit before exiting
                    if self.should_exit:
                        time.sleep(0.5)

                except KeyboardInterrupt:
                    self.should_exit = True
                    self.add_operation("⚠️ Interrupted by user. Exiting...")
                    self.update_layout()
                    time.sleep(0.5)
                except Exception as e:
                    self.log_error(f"Fatal error: {str(e)}")
                    self.update_layout()
                    time.sleep(1)
        except Exception as e:
            # If Rich Live display fails, fall back to simple mode
            self.log_error(f"Rich UI error: {str(e)}. Falling back to simple mode.")
            self.run_simple_mode()

    def run_simple_mode(self):
        """Run the application with simple console output (no Rich Live display)"""
        self.console.print("[bold blue]DeepClean - System Cleaner[/bold blue]")
        self.console.print("-" * 60)
        if self.args.dry_run:
            self.console.print(
                "[yellow]Running in simulation mode - no files will be deleted[/yellow]"
            )
        else:
            self.console.print(
                "[red]Running in delete mode - files will be permanently deleted[/red]"
            )
        self.console.print("-" * 60 + "\n")

        # Start cleaning in the main thread (no separate thread needed)
        # but track progress with periodic updates
        progress_thread = threading.Thread(target=self._print_progress_updates)
        progress_thread.daemon = True
        progress_thread.start()

        try:
            # Start cleaning
            self.start_cleaning()

            # Signal progress thread to stop
            self.should_exit = True
            progress_thread.join(timeout=1.0)

            # Print final summary
            self.console.print("\n" + "-" * 60)
            self.console.print("[bold]Cleaning Summary:[/bold]")
            self.console.print(f"Files analyzed: {self.stats['analyzed_files']}")
            self.console.print(f"Files cleaned: {self.stats['cleaned_files']}")
            self.console.print(
                f"Total size cleaned: {self.format_size(self.stats['cleaned_size'])}"
            )
            self.console.print(f"Protected files: {self.stats['protected_files']}")
            self.console.print(f"Errors encountered: {self.stats['errors']}")
            duration = time.time() - self.stats["start_time"]
            self.console.print(f"Total duration: {self.format_time(duration)}")
            self.console.print("-" * 60)
        except KeyboardInterrupt:
            self.console.print("\n[bold red]Operation interrupted by user.[/bold red]")
            self.should_exit = True
        except Exception as e:
            self.console.print(f"\n[bold red]Error: {str(e)}[/bold red]")
            self.log_error(f"Fatal error in simple mode: {str(e)}")

    def _print_progress_updates(self):
        """Print periodic progress updates for simple mode"""
        last_files = 0
        last_size = 0

        while not self.should_exit:
            # Only print if there are changes
            if self.stats["cleaned_files"] > last_files or self.stats["cleaned_size"] > last_size:
                self.console.print(
                    f"Progress: {self.progress_percent:.1f}% - Cleaned {self.stats['cleaned_files']} files ({self.format_size(self.stats['cleaned_size'])})"
                )

                # Print current operation
                if self.current_operation:
                    self.console.print(f"[dim]Current: {self.current_operation}[/dim]")

                # Update tracking variables
                last_files = self.stats["cleaned_files"]
                last_size = self.stats["cleaned_size"]

            # Sleep to avoid excessive output
            time.sleep(1.0)


def main():
    """Main function that parses arguments and launches the application"""
    parser = argparse.ArgumentParser(description="DeepClean - Deep cleaner for files")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without deleting files")
    parser.add_argument("--verbose", action="store_true", help="Show more information")
    parser.add_argument("--config", type=str, help="Custom configuration file")
    parser.add_argument(
        "--min-file-age", type=int, default=7, help="Minimum age of files to delete (in days)"
    )
    parser.add_argument("--clean-empty-dirs", action="store_true", help="Delete empty directories")
    parser.add_argument("--detect-duplicates", action="store_true", help="Detect duplicate files")
    parser.add_argument(
        "--clean-temp-files", action="store_true", help="Clean known temporary files"
    )
    parser.add_argument(
        "--generate-report", action="store_true", help="Generate a report after cleaning"
    )
    parser.add_argument(
        "--selector", action="store_true", help="Show item selector before cleaning"
    )
    parser.add_argument(
        "--simple-output", action="store_true", help="Use simple output mode without rich UI"
    )

    args = parser.parse_args()

    # Check if we should disable the rich UI based on terminal capabilities
    if not FULL_UI_SUPPORTED and not args.simple_output:
        print("WARNING: Limited terminal capabilities detected.")
        print("Switching to simple output mode for better compatibility.")
        args.simple_output = True

    # Load custom configuration if specified
    if args.config and os.path.exists(args.config):
        try:
            with open(args.config, "r") as f:
                config = json.load(f)
                if "paths" in config:
                    DEFAULT_PATHS.update(config["paths"])
                if "protected" in config:
                    PROTECTED_PATTERNS.extend(config["protected"])
                if "options" in config:
                    options = config["options"]
                    if (
                        "min_file_age_days" in options and args.min_file_age == 7
                    ):  # Do not override CLI argument
                        args.min_file_age = options["min_file_age_days"]
        except Exception as e:
            print(f"Error during configuration loading: {str(e)}")
            logger.exception("Configuration error")

    try:
        # Launch application
        app = DeepClean(args)
        app.run()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        logger.exception("Fatal error")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
