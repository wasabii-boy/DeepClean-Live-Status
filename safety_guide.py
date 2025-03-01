"""
DeepClean Safety Guide Module

This module provides safety information and best practices for cache cleaning
to help users avoid accidental data loss or system issues.
"""

import os

from rich import box
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()

# Safety guide categories and their content
SAFETY_GUIDES = {
    "general": {
        "title": "General Safety Guidelines",
        "content": """
# General Safety Guidelines for Cache Cleaning

## Before Cleaning
- **Always run with `--dry-run` first** to see what would be deleted
- **Create a backup** of important data before cleaning
- **Close applications** whose caches you're cleaning
- **Be cautious with system caches** as they may affect system stability

## During Cleaning
- **Start with small, safe categories** like browser caches
- **Pay attention to warnings** displayed by DeepClean
- **You can pause cleaning** at any time with the 'P' key
- **If unsure about a path**, skip it or research it first

## After Cleaning
- **Verify system functionality** after cleaning
- **Check application behavior** for any issues
- **Note any problems** for future reference
""",
    },
    "system_cache": {
        "title": "System Cache Safety",
        "content": """
# System Cache Safety

System caches are used by macOS and system services. Be careful when cleaning these.

## Safe to Clean
- `~/Library/Caches/` - User-level application caches
- `/Library/Caches/` - System-level application caches (with caution)
- Temporary files in `/tmp/` that aren't currently in use

## Use Caution With
- System logs and crash reports (may be needed for troubleshooting)
- Application state files (may reset application states)
- System preference caches (may reset some preferences)

## Avoid Cleaning
- Active system files in `/System/`
- Kernel caches and extensions
- System database files
""",
    },
    "browser_cache": {
        "title": "Browser Cache Safety",
        "content": """
# Browser Cache Safety

Browser caches are generally safe to clean but may affect your browsing experience.

## Effects of Cleaning
- Websites may load slower on first visit after cleaning
- You may be logged out of some websites
- Saved form data might be cleared depending on browser

## Safe to Clean
- Browser cache files (images, scripts, etc.)
- Browser cookies (will log you out of sites)
- Download history

## Consider Keeping
- Saved passwords (unless you have them backed up)
- Browser history (if you rely on it)
- Browser extensions data (may reset extensions)
""",
    },
    "development_cache": {
        "title": "Development Tools Safety",
        "content": """
# Development Tools Safety

Development caches can be large but may affect build times if cleaned.

## Package Manager Caches
- npm, pip, gem caches are generally safe to clean
- Will increase download time for next package installation
- Consider keeping if you have limited internet bandwidth

## IDE Caches
- JetBrains, VS Code caches are safe to clean
- May increase initial load time and indexing time
- Project-specific caches may reset project settings

## Build Caches
- Xcode derived data can be safely cleaned
- Maven, Gradle, Cargo caches are safe but will increase build times
- Docker image caches are safe but will require re-downloading images
""",
    },
    "application_cache": {
        "title": "Application Cache Safety",
        "content": """
# Application Cache Safety

Application caches vary widely in their purpose and safety.

## Media Applications
- Spotify, iTunes caches may contain offline content
- Cleaning will require re-downloading offline content
- Media editing app caches may contain unsaved work

## Communication Apps
- Slack, Discord caches may contain message history
- May need to re-download media and attachments
- Generally safe to clean but may slow down initial app load

## Productivity Apps
- Office, iWork caches are generally safe
- May contain auto-saved versions of documents
- Check for unsaved work before cleaning
""",
    },
    "macos_specific": {
        "title": "macOS-Specific Considerations",
        "content": """
# macOS-Specific Considerations

macOS has some unique caching mechanisms that require special attention.

## Safe to Clean
- Font caches (`~/Library/Caches/com.apple.FontRegistry/`)
- App Store caches (`~/Library/Caches/com.apple.appstore/`)
- iCloud caches (but may require re-syncing)

## Use Caution With
- Spotlight index (will rebuild automatically but takes time)
- iCloud Drive caches (may affect syncing)
- Time Machine local snapshots (may affect backup history)

## System Maintenance Alternatives
- Consider using built-in macOS maintenance scripts
- Use Disk Utility's First Aid for filesystem issues
- Use Activity Monitor to identify space usage
""",
    },
}

# Risk levels for different path types
PATH_RISK_LEVELS = {
    "low": [
        "~/Library/Caches/",
        "~/.cache/",
        "browser_cache",
        "npm_cache",
        "pip_cache",
        "yarn_cache",
        "tmp_files",
    ],
    "medium": [
        "/Library/Caches/",
        "application_state",
        "logs",
        "docker_cache",
        "xcode_cache",
    ],
    "high": [
        "/System/",
        "~/Library/Preferences/",
        "/Library/Preferences/",
        "kernel_cache",
        "system_database",
    ],
}


def get_risk_level(path):
    """
    Determine the risk level of cleaning a specific path.

    Args:
        path (str): The path to evaluate

    Returns:
        tuple: (risk_level, description) where risk_level is 'low', 'medium', or 'high'
    """
    # Default to medium if we can't determine
    risk_level = "medium"

    # Check against our known paths
    for level, paths in PATH_RISK_LEVELS.items():
        for risk_path in paths:
            if risk_path in path:
                risk_level = level
                break

    descriptions = {
        "low": "Generally safe to clean with minimal impact",
        "medium": "Use caution and verify what will be deleted first",
        "high": "High risk of system or application issues - use extreme caution",
    }

    return risk_level, descriptions[risk_level]


def get_safety_tips(path):
    """
    Get specific safety tips for a given path.

    Args:
        path (str): The path to get tips for

    Returns:
        list: List of safety tips relevant to the path
    """
    tips = []

    # System cache tips
    if "Library/Caches" in path:
        tips.append("Close applications before cleaning their caches")
        tips.append("System caches may rebuild automatically after cleaning")

    # Browser cache tips
    if any(browser in path.lower() for browser in ["chrome", "firefox", "safari", "edge"]):
        tips.append("Cleaning browser caches will log you out of websites")
        tips.append("Browser performance may be slower initially after cleaning")

    # Development tips
    if any(dev in path.lower() for dev in ["npm", "pip", "gem", "gradle", "maven", "cargo"]):
        tips.append("Package manager caches will require re-downloading packages")
        tips.append("Build times may increase after cleaning")

    # IDE tips
    if any(ide in path.lower() for ide in ["jetbrains", "vscode", "xcode"]):
        tips.append("IDE indexing will need to be rebuilt after cleaning")
        tips.append("Project loading may be slower initially")

    # Application tips
    if any(app in path.lower() for app in ["spotify", "slack", "discord", "zoom"]):
        tips.append("Media and message history may need to be re-downloaded")
        tips.append("Check for unsaved content before cleaning")

    # Docker tips
    if "docker" in path.lower():
        tips.append("Docker images will need to be re-downloaded")
        tips.append("Container data may be lost if not properly persisted")

    # Default tips if none matched
    if not tips:
        tips.append("Run with --dry-run first to see what would be deleted")
        tips.append("Create backups of important data before cleaning")

    return tips


def show_safety_guide(category="general"):
    """
    Display the safety guide for a specific category.

    Args:
        category (str): The category to display
    """
    if category not in SAFETY_GUIDES:
        category = "general"

    guide = SAFETY_GUIDES[category]

    console.clear()
    console.print(
        Panel(
            Markdown(guide["content"]),
            title=f"[bold blue]{guide['title']}[/bold blue]",
            subtitle="[italic]Press any key to return[/italic]",
            border_style="blue",
            expand=False,
            width=100,
        )
    )

    # Wait for key press
    console.input("Press Enter to continue...")


def show_safety_menu():
    """
    Display the safety guide menu and handle user selection.

    Returns:
        str: The selected category or None if user exits
    """
    console.clear()

    table = Table(box=box.ROUNDED, border_style="blue", title="DeepClean Safety Guide")
    table.add_column("Option", style="cyan", no_wrap=True)
    table.add_column("Description", style="white")

    for i, (key, guide) in enumerate(SAFETY_GUIDES.items(), 1):
        table.add_row(f"{i}", guide["title"])

    table.add_row("0", "Return to main menu")

    console.print(
        Panel(
            Text("Select a safety guide to view", style="bold"),
            title="[bold blue]DeepClean Safety Guide[/bold blue]",
            border_style="blue",
        )
    )
    console.print(table)

    choice = console.input("[bold cyan]Enter your choice (0-6): [/bold cyan]")

    try:
        choice_num = int(choice)
        if choice_num == 0:
            return None

        if 1 <= choice_num <= len(SAFETY_GUIDES):
            return list(SAFETY_GUIDES.keys())[choice_num - 1]
    except ValueError:
        pass

    return "general"  # Default to general if invalid choice


def get_risk_panel(path):
    """Get a panel showing risk level for a path"""
    try:
        # Expand path
        expanded_path = path
        if "~" in path:
            expanded_path = os.path.expanduser(path)

        # Get risk level and tips
        risk_level = get_risk_level(expanded_path)
        tips = get_safety_tips(expanded_path)

        # Create colored risk indicator
        if risk_level == "high":
            risk_text = "[bold red]HIGH RISK[/bold red]"
        elif risk_level == "medium":
            risk_text = "[bold yellow]MEDIUM RISK[/bold yellow]"
        else:
            risk_text = "[bold green]LOW RISK[/bold green]"

        # Create the panel content
        content = Text()
        content.append(f"Risk Level: {risk_text}\n\n", style="bold")

        if tips:
            content.append("Safety Tips:\n", style="bold")
            for tip in tips:
                content.append(f"• {tip}\n")

        # Return the panel
        return Panel(
            content,
            title=f"[bold]Safety Analysis for {path}[/bold]",
            border_style="blue",
            padding=(1, 2),
        )
    except (ValueError, KeyError, AttributeError) as e:
        # Handle specific exceptions that might occur during panel creation
        error_text = Text(f"Error analyzing path: {str(e)}")
        return Panel(
            error_text, title=f"[bold red]Error Analyzing {path}[/bold red]", border_style="red"
        )


if __name__ == "__main__":
    # Test the safety guide
    show_safety_menu()
