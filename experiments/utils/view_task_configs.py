#!/usr/bin/env python3

import json
import importlib.resources
import argparse
import os
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

# Create a rich console for pretty output
console = Console()
# Create a plain console for errors and other information
plain_console = Console(highlight=False, style=None)


def list_task_configs():
    """List all available task configuration files."""
    package = "browsergym.workarena.data_files.task_configs"

    try:
        # Using files() instead of contents() to avoid deprecation warning
        files = [
            f.name
            for f in importlib.resources.files(package).iterdir()
            if f.name.endswith(".json") and f.name.startswith("order_")
        ]
        return files
    except ImportError:
        plain_console.print(f"Error: Could not import package '{package}'")
        return []


def load_task_config(task_name):
    """Load a specific task configuration file."""
    package = "browsergym.workarena.data_files.task_configs"

    try:
        # Using files() instead of read_text() to avoid deprecation warning
        resource_path = importlib.resources.files(package).joinpath(task_name)
        with resource_path.open("r") as f:
            return json.load(f)
    except Exception as e:
        plain_console.print(f"Error loading task config '{task_name}': {e}")
        return None


def display_task_config(config_data, task_name=None):
    """Display task configuration with index mapping in a simpler, more reliable way."""
    if not config_data:
        plain_console.print("No configuration data available.")
        return

    # Create a title for the configuration display
    title = (
        f"Configuration Mapping: {task_name}" if task_name else "Configuration Mapping"
    )
    console.print(Panel(title, style="bold blue"))

    # Process each configuration item
    for idx, item in enumerate(config_data):
        # Create panel for each index
        console.print(f"\n[bold magenta]Index {idx}[/bold magenta]")

        # Display the configuration cleanly
        table = Table(show_header=False, box=box.SIMPLE)
        table.add_column("Key", style="green")
        table.add_column("Value", style="yellow")

        for key, value in item.items():
            # Handle different value types
            if isinstance(value, dict):
                # For configuration dictionaries, format as JSON string
                formatted_value = json.dumps(value, indent=2)
                table.add_row(key, formatted_value)
            else:
                table.add_row(key, str(value))

        console.print(table)

        # Add a partition line between configurations except after the last one
        if idx < len(config_data) - 1:
            console.print("[dim]" + "-" * 80 + "[/dim]")


def save_task_config_mapping(config_data, task_name, output_dir="cache/task_configs/"):
    """Save the task configuration mapping to a file in a pretty format."""
    if not config_data:
        plain_console.print("No configuration data available to save.")
        return None

    # Create the output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Create a filename based on the task name
    file_name = task_name.replace(".json", "_mapping.txt")
    file_path = os.path.join(output_dir, file_name)

    try:
        # Now write the formatted version
        with open(file_path, "w") as f:
            # Create a title for the configuration display
            title = f"Configuration Mapping: {task_name}"
            f.write(f"{title}\n{'=' * len(title)}\n\n")

            # Process each configuration item
            for idx, item in enumerate(config_data):
                f.write(f"Index {idx}\n{'-' * 10}\n")

                for key, value in item.items():
                    if isinstance(value, dict):
                        f.write(f"{key}:\n")
                        formatted_value = json.dumps(value, indent=2)
                        for line in formatted_value.split("\n"):
                            f.write(f"  {line}\n")
                    else:
                        f.write(f"{key}: {value}\n")

                if idx < len(config_data) - 1:
                    f.write("\n" + "-" * 80 + "\n\n")

        plain_console.print(f"\nMapping saved to: {file_path}")
        return file_path
    except Exception as e:
        plain_console.print(f"Error saving mapping: {e}")
        return None


def display_task_list(task_files):
    """Display the list of available task configurations."""
    console.print("[bold blue]Available Task Configurations[/bold blue]")

    table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
    table.add_column("#", style="cyan", justify="right")
    table.add_column("Task Name", style="green")

    for idx, task_file in enumerate(task_files):
        table.add_row(str(idx + 1), task_file)

    console.print(table)


def main():
    parser = argparse.ArgumentParser(description="View WorkArena task configurations")
    parser.add_argument(
        "--list", action="store_true", help="List all available task configurations"
    )
    parser.add_argument(
        "--task", type=str, help="Specify task configuration file to view"
    )
    parser.add_argument(
        "--save", action="store_true", help="Save the mapping to a file"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="cache/task_configs/",
        help="Directory to save mapping files",
    )

    args = parser.parse_args()

    # Handle list mode
    if args.list:
        task_files = list_task_configs()
        if not task_files:
            return
        display_task_list(task_files)
        return

    # Handle task viewing mode
    if args.task:
        # Make sure the task name has .json extension
        task_name = args.task if args.task.endswith(".json") else f"{args.task}.json"
        config_data = load_task_config(task_name)
        if config_data:
            display_task_config(config_data, task_name)

            # Save the mapping if requested
            if args.save:
                save_task_config_mapping(config_data, task_name, args.output_dir)

    # If no arguments provided, just display help
    if not args.list and not args.task:
        parser.print_help()
        return


if __name__ == "__main__":
    main()
