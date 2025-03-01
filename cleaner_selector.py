#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DeepClean - Item Selector Module
This module provides a selector for choosing which items to clean
"""

import os
import sys
from typing import Any, Dict, List, Set, Tuple

try:
    from rich.box import ROUNDED
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Confirm, Prompt
    from rich.table import Table
except ImportError:
    print("Error: This module requires the Rich library.")
    print("Please install it with: pip install rich")
    sys.exit(1)

# Try to import safety guide
try:
    import safety_guide

    has_safety_guide = True
except ImportError:
    has_safety_guide = False
    print("Warning: Safety guide module not found. Safety guides will not be available.")

# Initialize console
console = Console()

# Paths to clean - same as in main application but duplicated for independence
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

# File patterns to clean
DEFAULT_PATTERNS = {
    "temporary_files": ["tmp", "temp", "bak", "old", "swp", "dmp", "dump"],
    "package_manager_files": ["tgz", "tar.gz", "zip", "whl", "egg"],
    "log_files": ["log", "logs"],
    "cache_files": ["cache"],
}


def expand_path(path: str) -> str:
    """Expand path with user home directory"""
    return os.path.expanduser(path)


def get_disk_usage(path: str) -> Tuple[int, str]:
    """Get disk usage for a path"""
    try:
        path = expand_path(path)
        if not os.path.exists(path):
            return (0, "Path doesn't exist")

        total_size = 0
        file_count = 0

        # Walk through directory and calculate size
        for root, dirs, files in os.walk(path, topdown=True, onerror=None):
            # Limit recursion level for performance
            if root.count(os.sep) - path.count(os.sep) > 5:
                continue

            try:
                # Calculate size of files in current directory
                file_count += len(files)
                for name in files:
                    try:
                        file_path = os.path.join(root, name)
                        if os.path.islink(file_path):
                            continue  # Skip symbolic links
                        total_size += os.path.getsize(file_path)
                    except (OSError, FileNotFoundError):
                        continue  # Ignore errors for individual files
            except (OSError, FileNotFoundError):
                continue  # Skip directories we can't access

            # Limit calculation for very large directories
            if file_count > 10000:
                return (total_size, f"~{file_count}+ files (sampling)")

        return (total_size, f"{file_count} files")
    except (OSError, FileNotFoundError):
        return (0, "Access denied")
    except (KeyboardInterrupt, SystemExit):
        raise  # Re-raise important exceptions
    except Exception as e:
        return (0, f"Error: {str(e)}")


def format_size(size: int) -> str:
    """Format size in human-readable format"""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} TB"


def show_selector() -> Dict[str, Any]:
    """Show the item selector interface"""
    # Initialize paths and patterns with defaults
    selected_paths = DEFAULT_PATHS.copy()
    selected_patterns = DEFAULT_PATTERNS.copy()

    # Show welcome message
    console.print(
        Panel(
            "[bold]DeepClean Item Selector[/bold]\n\n"
            "This tool lets you select which items to clean.\n"
            "Choose directories and file patterns carefully to avoid deleting important data.\n"
            "[italic yellow]Consider reviewing the Safety Guide before proceeding.[/italic yellow]",
            title="Welcome",
            border_style="green",
        )
    )

    # Main menu loop
    while True:
        console.print("\n[bold]Main Menu[/bold]")
        console.print("1. Select Path Categories")
        console.print("2. Select File Patterns")
        console.print("3. Add Custom Path")
        console.print("4. Show Current Selection")
        console.print("5. View Safety Guide")
        console.print("6. Finish and Return")
        console.print("0. Cancel and Return")

        choice = Prompt.ask(
            "Enter your choice", choices=["0", "1", "2", "3", "4", "5", "6"], default="6"
        )

        if choice == "1":
            selected_paths = select_path_categories(selected_paths)
        elif choice == "2":
            selected_patterns = select_file_patterns(selected_patterns)
        elif choice == "3":
            add_custom_path(selected_paths)
        elif choice == "4":
            show_current_selection(selected_paths, selected_patterns)
        elif choice == "5":
            show_safety_guide_menu()
        elif choice == "6":
            console.print("[green]Finished selection.[/green]")
            return {"paths": selected_paths, "patterns": selected_patterns}
        elif choice == "0":
            if Confirm.ask("Are you sure you want to cancel?", default=False):
                console.print("[yellow]Selection cancelled.[/yellow]")
                return {"paths": DEFAULT_PATHS, "patterns": DEFAULT_PATTERNS}


def select_path_categories(selected_paths: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """Select which path categories to clean"""
    console.print(
        Panel(
            "[bold]Path Categories[/bold]\nSelect which directories to clean\n"
            "[italic yellow]Select categories carefully and review the Safety Guide "
            "if unsure.[/italic yellow]",
            title="Path Selection",
        )
    )

    # Create a copy to modify
    result = selected_paths.copy()

    categories = list(DEFAULT_PATHS.keys())
    current_selection = {cat: (cat in result and len(result[cat]) > 0) for cat in categories}

    # Show table of categories with status
    while True:
        table = Table(title="Available Path Categories", box=ROUNDED)
        table.add_column("Number", style="cyan")
        table.add_column("Category", style="green")
        table.add_column("Status", style="yellow")
        table.add_column("Disk Usage", style="magenta")

        # Add each category to the table
        for i, category in enumerate(categories, 1):
            # Get disk usage for all paths in the category
            total_size = 0
            status_parts = []
            for path in DEFAULT_PATHS.get(category, []):
                size, status = get_disk_usage(path)
                total_size += size
                status_parts.append(f"{os.path.basename(path.rstrip('/'))}: {status}")

            # Format the total size
            total_size_str = format_size(total_size)

            # Determine if selected
            is_selected = current_selection[category]
            status = "[green]Selected[/green]" if is_selected else "[red]Not Selected[/red]"

            table.add_row(str(i), category, status, f"{total_size_str}\n" + "\n".join(status_parts))

        # Add control options
        table.add_row("A", "Select All", "", "")
        table.add_row("N", "Select None", "", "")
        table.add_row("D", "Done", "", "")

        # Show the table
        console.print(table)

        # Get user choice
        choice = Prompt.ask(
            "Enter number to toggle, A to select all, N to select none, D when done", default="D"
        )

        if choice.upper() == "A":
            # Select all categories
            for cat in categories:
                current_selection[cat] = True
        elif choice.upper() == "N":
            # Deselect all categories
            for cat in categories:
                current_selection[cat] = False
        elif choice.upper() == "D":
            # Done, construct the result
            for cat in categories:
                if current_selection[cat]:
                    # If selected, keep the default paths
                    result[cat] = DEFAULT_PATHS[cat].copy()
                else:
                    # If not selected, use empty list
                    result[cat] = []
            return result
        else:
            # Toggle a specific category
            try:
                index = int(choice) - 1
                if 0 <= index < len(categories):
                    cat = categories[index]
                    current_selection[cat] = not current_selection[cat]
            except ValueError:
                console.print(
                    "[red]Invalid choice. Please enter a number or one of the options.[/red]"
                )


def select_file_patterns(selected_patterns: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """Select which file patterns to clean"""
    console.print(
        Panel(
            "[bold]File Patterns[/bold]\nSelect which file types to clean",
            title="Pattern Selection",
        )
    )

    # Create a copy to modify
    result = selected_patterns.copy()

    # Get all categories and patterns
    categories = list(DEFAULT_PATTERNS.keys())
    current_selection = {cat: set(result.get(cat, [])) for cat in categories}

    # Show table of categories and patterns
    while True:
        table = Table(title="Available File Patterns", box=ROUNDED)
        table.add_column("Number", style="cyan")
        table.add_column("Category", style="green")
        table.add_column("Patterns", style="yellow")
        table.add_column("Status", style="magenta")

        # Add each category to the table
        for i, category in enumerate(categories, 1):
            all_patterns = DEFAULT_PATTERNS.get(category, [])
            selected_count = len(current_selection[category])
            total_count = len(all_patterns)

            # Format the patterns
            pattern_list = ", ".join(all_patterns)

            # Determine status
            status = f"[green]{selected_count}/{total_count} selected[/green]"
            if selected_count == 0:
                status = "[red]None selected[/red]"

            table.add_row(str(i), category, pattern_list, status)

        # Add control options
        table.add_row("D", "Done", "", "")

        # Show the table
        console.print(table)

        # Get user choice
        choice = Prompt.ask("Enter number to edit patterns or D when done", default="D")

        if choice.upper() == "D":
            # Done, construct the result
            for cat in categories:
                result[cat] = list(current_selection[cat])
            return result
        else:
            # Edit patterns for a specific category
            try:
                index = int(choice) - 1
                if 0 <= index < len(categories):
                    cat = categories[index]
                    current_selection[cat] = edit_patterns_for_category(cat, current_selection[cat])
                else:
                    console.print("[red]Invalid choice. Please enter a valid number or 'D'.[/red]")
            except ValueError:
                console.print("[red]Invalid choice. Please enter a number or 'D'.[/red]")


def edit_patterns_for_category(category: str, selected_patterns: Set[str]) -> Set[str]:
    """Edit the selected patterns for a specific category"""
    all_patterns = DEFAULT_PATTERNS.get(category, [])
    result = selected_patterns.copy()

    console.print(f"\n[bold]Editing patterns for: {category}[/bold]")

    while True:
        console.print("\nCurrent selection:")

        # Show list of patterns with selection status
        for i, pattern in enumerate(all_patterns, 1):
            is_selected = pattern in result
            status = "[green]✓[/green]" if is_selected else "[red]✗[/red]"
            console.print(f"{i}. {status} {pattern}")

        console.print("\nOptions:")
        console.print("A. Select All")
        console.print("N. Select None")
        console.print("D. Done")

        choice = Prompt.ask(
            "Enter number to toggle, A to select all, N to select none, D when done", default="D"
        )

        if choice.upper() == "A":
            # Select all patterns
            result = set(all_patterns)
        elif choice.upper() == "N":
            # Deselect all patterns
            result = set()
        elif choice.upper() == "D":
            # Done
            return result
        else:
            # Toggle a specific pattern
            try:
                index = int(choice) - 1
                if 0 <= index < len(all_patterns):
                    pattern = all_patterns[index]
                    if pattern in result:
                        result.remove(pattern)
                    else:
                        result.add(pattern)
                else:
                    console.print(
                        "[red]Invalid choice. Please enter a valid number or one "
                        "of the options.[/red]"
                    )
            except ValueError:
                console.print(
                    "[red]Invalid choice. Please enter a number or one of the options.[/red]"
                )


def add_custom_path(selected_paths: Dict[str, List[str]]) -> None:
    """Add a custom path to clean"""
    console.print(
        Panel(
            "[bold]Add Custom Path[/bold]\nAdd additional directories to clean", title="Custom Path"
        )
    )

    # Show existing categories
    console.print("\nExisting categories:")
    categories = list(selected_paths.keys())
    for i, category in enumerate(categories, 1):
        console.print(f"{i}. {category}")

    # Option to create new category
    console.print(f"{len(categories) + 1}. Create new category")

    # Get category
    while True:
        choice = Prompt.ask("Select category", default="1")

        try:
            choice_int = int(choice)
            if 1 <= choice_int <= len(categories):
                # Existing category
                category = categories[choice_int - 1]
                break
            elif choice_int == len(categories) + 1:
                # New category
                new_category = Prompt.ask("Enter new category name")
                if new_category and new_category not in selected_paths:
                    selected_paths[new_category] = []
                    category = new_category
                    break
                else:
                    console.print("[red]Invalid category name or already exists.[/red]")
            else:
                console.print("[red]Invalid choice.[/red]")
        except ValueError:
            console.print("[red]Please enter a number.[/red]")

    # Get the path to add
    path = Prompt.ask("Enter path to add (use ~ for home directory)")

    # Validate and expand the path
    expanded_path = expand_path(path)
    if not os.path.exists(expanded_path):
        if Confirm.ask(f"Path {expanded_path} doesn't exist. Add anyway?", default=False):
            selected_paths[category].append(path)
            console.print(f"[green]Added {path} to {category}.[/green]")
        else:
            console.print("[yellow]Path not added.[/yellow]")
    else:
        selected_paths[category].append(path)
        size, status = get_disk_usage(path)
        console.print(f"[green]Added {path} to {category}. Disk usage: {status}[/green]")


def show_current_selection(
    selected_paths: Dict[str, List[str]], selected_patterns: Dict[str, List[str]]
) -> None:
    """Show current selection of paths and patterns"""
    console.print(
        Panel(
            "[bold]Current Selection[/bold]\nPaths and patterns that will be cleaned",
            title="Selection Summary",
        )
    )

    # Show selected paths
    console.print("\n[bold]Selected Paths:[/bold]")
    table = Table(box=ROUNDED)
    table.add_column("Category", style="green")
    table.add_column("Paths", style="yellow")
    table.add_column("Disk Usage", style="magenta")

    has_paths = False
    for category, paths in selected_paths.items():
        if not paths:
            continue

        has_paths = True
        path_list = []
        total_size = 0

        for path in paths:
            size, status = get_disk_usage(path)
            total_size += size
            path_list.append(f"{path} ({status})")

        if path_list:
            total_size_str = format_size(total_size)
            table.add_row(category, "\n".join(path_list), total_size_str)

    if has_paths:
        console.print(table)
    else:
        console.print("[yellow]No paths selected.[/yellow]")

    # Show selected patterns
    console.print("\n[bold]Selected File Patterns:[/bold]")
    pattern_table = Table(box=ROUNDED)
    pattern_table.add_column("Category", style="green")
    pattern_table.add_column("Patterns", style="yellow")

    has_patterns = False
    for category, patterns in selected_patterns.items():
        if patterns:
            has_patterns = True
            pattern_table.add_row(category, ", ".join(patterns))

    if has_patterns:
        console.print(pattern_table)
    else:
        console.print("[yellow]No file patterns selected.[/yellow]")

    # Calculate total size
    total_disk_usage = 0
    for category, paths in selected_paths.items():
        for path in paths:
            size, _ = get_disk_usage(path)
            total_disk_usage += size

    console.print(f"\n[bold]Total estimated disk usage:[/bold] {format_size(total_disk_usage)}")

    # Wait for user to continue
    Prompt.ask("Press Enter to continue", default="")


def show_safety_guide_menu():
    """Show the safety guide menu"""
    if not has_safety_guide:
        console.print("[yellow]Safety guide module not available.[/yellow]")
        Prompt.ask("Press Enter to continue", default="")
        return

    console.print(
        Panel(
            "[bold]DeepClean Safety Guide[/bold]\n\n"
            "These guidelines will help you safely clean your system "
            "without losing important data.",
            title="Safety Guide",
            border_style="blue",
        )
    )

    # Main safety guide menu loop
    while True:
        console.print("\n[bold]Safety Guide Menu[/bold]")
        console.print("1. General Safety Guidelines")
        console.print("2. System Cache")
        console.print("3. Temporary Files")
        console.print("4. Logs")
        console.print("5. Package Managers")
        console.print("6. Browsers")
        console.print("7. Editors & IDEs")
        console.print("8. Applications")
        console.print("9. Docker & Kubernetes")
        console.print("0. Back to Main Menu")

        choice = Prompt.ask(
            "Enter your choice",
            choices=["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"],
            default="1",
        )

        if choice == "0":
            return
        elif choice == "1":
            safety_guide.show_safety_guide()  # General guidelines
        elif choice == "2":
            safety_guide.show_safety_guide("system_cache")
        elif choice == "3":
            safety_guide.show_safety_guide("temp")
        elif choice == "4":
            safety_guide.show_safety_guide("logs")
        elif choice == "5":
            safety_guide.show_safety_guide("package_managers")
        elif choice == "6":
            safety_guide.show_safety_guide("browsers")
        elif choice == "7":
            safety_guide.show_safety_guide("editors_and_ides")
        elif choice == "8":
            safety_guide.show_safety_guide("apps")
        elif choice == "9":
            safety_guide.show_safety_guide("docker")

        # Wait for user to continue
        Prompt.ask("Press Enter to return to the Safety Guide Menu", default="")


if __name__ == "__main__":
    # When run directly, show the selector and print result
    result = show_selector()
    console.print(result)
