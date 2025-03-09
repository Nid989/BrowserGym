"""
Experiment Summary Report Generator

This script reads all experiment directories in the specified folder or the current directory (if no path is provided) that match a specific naming convention (formatted as `YYYY-MM-DD_HH-MM-SS`).
Each experiment directory must contain a `summary_info.json` file with relevant details.
The script aggregates statistics and outputs a report in markdown format and saves it to a file.
Additionally, it generates a CSV version of the summary for easy import into Excel.

### Report Contents
- Number of runs (total, successful, failed)
- Date and time of each experiment (extracted from the folder name)
- Task name and instance (extracted from the folder name)
- Average number of steps per run (total, successful, failed)
- Average number of tokens processed per run (total, successful, failed)
- Cumulative elapsed time (total and agent-specific processing time)
- Error logs count (total, successful, failed)
- A detailed summary for each experiment directory and group by task

### Success/Failure Criteria
- A run is considered **successful** if `cum_reward == 1`
- A run is considered **failed** if `cum_reward == 0`

### Usage
```bash
python script.py [results_dir] [--debug]
```
- `[results_dir]`: Optional. Path to the directory containing multiple experiment subdirectories. Defaults to the current directory (`.`).
- `--debug`: Enables debug logging for detailed output.

### Example
```bash
python script.py ./results --debug
python script.py --debug  # Defaults to current directory
```

"""

from pathlib import Path
import json
import logging
import re
from typing import Dict, List
import argparse
import csv
from datetime import datetime
from collections import defaultdict

from browsergym.experiments.loop import ExpResult


# Utility function to load summary_info.json
def load_summary_info(exp_dir: Path) -> Dict:
    summary_path = exp_dir / "summary_info.json"
    if summary_path.exists():
        with open(summary_path, "r") as f:
            return json.load(f)
    return {}

# Utility function to format numbers consistently
def format_number(value):
    return f"{value:,}" if isinstance(value, int) else f"{value:.2f}"

# Utility function to write markdown tables
def write_table(md, header: List[str], rows: List[List[str]]):
    md.write("| " + " | ".join(header) + " |\n")
    md.write("|" + "---|" * len(header) + "\n")
    for row in rows:
        md.write("| " + " | ".join(row) + " |\n")

# Refactored function to write sections
def write_section(md, title: str, headers: List[str], rows: List[List[str]]):
    md.write(f"\n## {title}\n")
    write_table(md, headers, rows)

# Function to parse experiment metadata
def parse_experiment_metadata(exp_dir: Path) -> Dict:
    experiment_name = exp_dir.name
    match = re.match(r"(\d{4}-\d{2}-\d{2})_(\d{2}-\d{2}-\d{2})_DemoAgentArgs_on_workarena.servicenow.(.*)_(\d+)", experiment_name)
    if not match:
        return {}

    start_datetime_str = f"{match.group(1)} {match.group(2).replace('-', ':')}"
    start_datetime = datetime.strptime(start_datetime_str, "%Y-%m-%d %H:%M:%S")
    summary_info_path = exp_dir / "summary_info.json"
    
    # Check if summary_info.json exists before trying to get its modification time
    if summary_info_path.exists():
        end_datetime = datetime.fromtimestamp(summary_info_path.stat().st_mtime)
        elapsed_seconds = (end_datetime - start_datetime).total_seconds()
    else:
        # If file doesn't exist, set elapsed_seconds to 0 without logging
        elapsed_seconds = 0

    # Get model info from ExpResult
    model_provider = "Unknown"
    model_name = "Unknown"
    agent_type = "Unknown"
    try:
        exp_result = ExpResult(exp_dir)
        if exp_result.steps_info and exp_result.steps_info[0].agent_info:
            model_info = exp_result.steps_info[0].agent_info.get('model_info', {})
            model_provider = model_info.get('model_provider', 'Unknown')
            model_name = model_info.get('model_name', 'Unknown')
            agent_type = exp_result.steps_info[0].agent_info.get('agent_type', 'Unknown')
    except Exception as e:
        pass

    return {
        "start_datetime_str": start_datetime_str,
        "elapsed_seconds": elapsed_seconds,
        "task_name": match.group(3),
        "instance": int(match.group(4)),
        "model_provider": model_provider,
        "model_name": model_name,
        "agent_type": agent_type
    }

# Generate summary statistics
def generate_summary_statistics(exp_dirs: List[Path]) -> Dict[str, Dict]:
    summary = {
        "total_runs": 0,
        "successful_runs": 0,
        "failed_runs": 0,
        "steps": {"total": 0, "successful": 0, "failed": 0},
        "tokens": {"total": 0, "successful": 0, "failed": 0},
        "elapsed_time": {"total": 0, "successful": 0, "failed": 0},
        "error_logs": {"total": 0, "successful": 0, "failed": 0},
        "experiments": {},
        "tasks": defaultdict(lambda: {
            "total_runs": 0, "successful_runs": 0, "failed_runs": 0,
            "steps": {"total": 0, "successful": 0, "failed": 0},
            "tokens": {"total": 0, "successful": 0, "failed": 0},
            "elapsed_time": {"total": 0, "successful": 0, "failed": 0},
            "error_logs": {"total": 0, "successful": 0, "failed": 0}
        })
    }

    for idx, exp_dir in enumerate(sorted(exp_dirs, key=lambda d: d.name), start=1):
        metadata = parse_experiment_metadata(exp_dir)
        if not metadata:
            continue

        experiment_name = exp_dir.name
        summary_info = load_summary_info(exp_dir)
        
        # Flag if summary_info.json is missing
        summary_missing = not summary_info
        
        if not summary_missing:
            cum_reward = summary_info.get("cum_reward", 0)
            is_success = cum_reward == 1
            n_steps = summary_info.get("n_steps", 0)
            n_tokens = summary_info.get("stats.cum_n_token_pruned_html", 0)
            has_error = 1 if summary_info.get("err_msg") else 0

            task_name = metadata["task_name"]
            instance = metadata["instance"]

            summary["experiments"][experiment_name] = {
                "index": idx,
                "date_time": metadata["start_datetime_str"],
                "model_provider": metadata["model_provider"],
                "model_name": metadata["model_name"],
                "agent_type": metadata["agent_type"],
                "task": task_name,
                "instance": instance,
                "n_steps": n_steps,
                "tokens_pruned_html": n_tokens,
                "elapsed_time": metadata["elapsed_seconds"],
                "agent_processing_time": summary_info.get("stats.cum_agent_elapsed", 0),
                "cum_reward": cum_reward,
                "err_msg": summary_info.get("err_msg", ""),
                "summary_missing": False
            }

            summary["total_runs"] += 1
            summary["tasks"][task_name]["total_runs"] += 1

            task_metrics = summary["tasks"][task_name]

            if is_success:
                summary["successful_runs"] += 1
                task_metrics["successful_runs"] += 1
                summary["steps"]["successful"] += n_steps
                summary["tokens"]["successful"] += n_tokens
                summary["elapsed_time"]["successful"] += metadata["elapsed_seconds"]
                summary["error_logs"]["successful"] += has_error
                task_metrics["steps"]["successful"] += n_steps
                task_metrics["tokens"]["successful"] += n_tokens
                task_metrics["elapsed_time"]["successful"] += metadata["elapsed_seconds"]
                task_metrics["error_logs"]["successful"] += has_error
            else:
                summary["failed_runs"] += 1
                task_metrics["failed_runs"] += 1
                summary["steps"]["failed"] += n_steps
                summary["tokens"]["failed"] += n_tokens
                summary["elapsed_time"]["failed"] += metadata["elapsed_seconds"]
                summary["error_logs"]["failed"] += has_error
                task_metrics["steps"]["failed"] += n_steps
                task_metrics["tokens"]["failed"] += n_tokens
                task_metrics["elapsed_time"]["failed"] += metadata["elapsed_seconds"]
                task_metrics["error_logs"]["failed"] += has_error

            summary["steps"]["total"] += n_steps
            summary["tokens"]["total"] += n_tokens
            summary["elapsed_time"]["total"] += metadata["elapsed_seconds"]
            summary["error_logs"]["total"] += has_error
        else:
            # Just store the experiment with a flag indicating summary is missing
            summary["experiments"][experiment_name] = {
                "index": idx,
                "date_time": metadata.get("start_datetime_str", ""),
                "model_provider": metadata.get("model_provider", ""),
                "model_name": metadata.get("model_name", ""),
                "agent_type": metadata.get("agent_type", ""),
                "task": metadata.get("task_name", ""),
                "instance": metadata.get("instance", ""),
                "summary_missing": True
            }

    return summary

# Save summary as markdown and CSV
def save_summary(summary: Dict, results_dir: Path):
    last_experiment_time = max(exp_dir.name for exp_dir in results_dir.iterdir() if re.match(r"\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}", exp_dir.name))
    timestamp = last_experiment_time.replace("_", " ").replace("-", ":", 1).replace("-", ":", 1)
    markdown_file = results_dir / f"{timestamp[0:4]}-{timestamp[5:7]}-{timestamp[8:10]}_statistics.md"
    csv_file = results_dir / f"{timestamp[0:4]}-{timestamp[5:7]}-{timestamp[8:10]}_statistics.csv"

    with open(markdown_file, "w") as md:
        md.write("# Experiment Summary Report\n")

        # Experiment details table
        experiment_rows = []
        for experiment, stats in sorted(summary["experiments"].items(), key=lambda item: item[1]["date_time"]):
            if stats.get("summary_missing", False):
                # Create a row with just the basic info and empty cells for the rest
                row = [
                    str(stats['index']), 
                    stats.get('date_time', ''), 
                    stats.get('model_provider', ''), 
                    stats.get('model_name', ''), 
                    stats.get('agent_type', ''),
                    stats.get('task', ''), 
                    str(stats.get('instance', '')), 
                    '', '', '', '', '', 
                    'No summary_info.json found',
                    experiment
                ]
            else:
                # Create a normal row with all the data
                row = [
                    str(stats['index']), 
                    stats['date_time'], 
                    stats['model_provider'], 
                    stats['model_name'], 
                    stats['agent_type'],
                    stats['task'], 
                    str(stats['instance']), 
                    str(stats['n_steps']),
                    str(stats['tokens_pruned_html']), 
                    f"{stats['elapsed_time']:.2f}", 
                    f"{stats['agent_processing_time']:.2f}",
                    "Yes" if stats['cum_reward'] == 1 else "No", 
                    str(stats['err_msg'] or "").replace('\n', ' ').replace('\r', ' '),
                    experiment
                ]
            experiment_rows.append(row)
            
        write_section(md, "Experiment Details", 
                     ["#", "Date & Time", "Model Provider", "Model Name", "Agent Type", "Task", "Instance", 
                      "Steps", "Tokens (Pruned HTML)", "Time Elapsed (s)", "Agent Time (s)", 
                      "Success", "Error Message", "Folder Name"], 
                     experiment_rows)

        # Overall summary table
        overall_rows = [
            ["Runs", format_number(summary['total_runs']), format_number(summary['successful_runs']), format_number(summary['failed_runs'])],
            ["Steps", format_number(summary['steps']['total']), format_number(summary['steps']['successful']), format_number(summary['steps']['failed'])],
            ["Tokens", format_number(summary['tokens']['total']), format_number(summary['tokens']['successful']), format_number(summary['tokens']['failed'])],
            ["Elapsed Time (s)", format_number(summary['elapsed_time']['total']), format_number(summary['elapsed_time']['successful']), format_number(summary['elapsed_time']['failed'])],
            ["Error Logs", format_number(summary['error_logs']['total']), format_number(summary['error_logs']['successful']), format_number(summary['error_logs']['failed'])]
        ]
        write_section(md, "Overall Summary", ["Metric", "Total", "Successful", "Failed"], overall_rows)

        # Overview table for tasks
        task_overview_rows = [
            [task, format_number(stats['total_runs']), format_number(stats['successful_runs']), format_number(stats['failed_runs'])]
            for task, stats in summary["tasks"].items()
        ]
        write_section(md, "Task Overview", ["Task", "Total Runs", "Successful Runs", "Failed Runs"], task_overview_rows)

        # Task grouped summary
        for task, stats in summary["tasks"].items():
            task_rows = [
                ["Runs", format_number(stats['total_runs']), format_number(stats['successful_runs']), format_number(stats['failed_runs'])],
                ["Steps", format_number(stats['steps']['total']), format_number(stats['steps']['successful']), format_number(stats['steps']['failed'])],
                ["Tokens", format_number(stats['tokens']['total']), format_number(stats['tokens']['successful']), format_number(stats['tokens']['failed'])],
                ["Elapsed Time (s)", format_number(stats['elapsed_time']['total']), format_number(stats['elapsed_time']['successful']), format_number(stats['elapsed_time']['failed'])],
                ["Error Logs", format_number(stats['error_logs']['total']), format_number(stats['error_logs']['successful']), format_number(stats['error_logs']['failed'])]
            ]
            write_section(md, f"{task} Task Metrics", ["Metric", "Total", "Successful", "Failed"], task_rows)

    with open(csv_file, "w", newline='') as csvf:
        csv_writer = csv.writer(csvf, delimiter=';')
        csv_writer.writerow(["Index", "Date & Time", "Model Provider", "Model Name", "Agent Type", "Task", 
                           "Instance", "Steps", "Tokens (Pruned HTML)", "Time Elapsed (s)", 
                           "Agent Time (s)", "Success", "Error Message", "Folder Name"])
        
        for experiment, stats in sorted(summary["experiments"].items(), key=lambda item: item[1]["date_time"]):
            if stats.get("summary_missing", False):
                # Create a row with just the basic info and empty cells for the rest
                csv_writer.writerow([
                    str(stats['index']), 
                    stats.get('date_time', ''), 
                    stats.get('model_provider', ''), 
                    stats.get('model_name', ''), 
                    stats.get('agent_type', ''),
                    stats.get('task', ''), 
                    str(stats.get('instance', '')), 
                    '', '', '', '', '', 
                    'No summary_info.json found',
                    experiment
                ])
            else:
                # Create a normal row with all the data
                csv_writer.writerow([
                    str(stats['index']), 
                    stats['date_time'], 
                    stats['model_provider'], 
                    stats['model_name'], 
                    stats['agent_type'],
                    stats['task'], 
                    str(stats['instance']),
                    str(stats['n_steps']), 
                    str(stats['tokens_pruned_html']), 
                    f"{stats['elapsed_time']:.2f}", 
                    f"{stats['agent_processing_time']:.2f}", 
                    "Yes" if stats['cum_reward'] == 1 else "No", 
                    str(stats['err_msg'] or "").replace('\n', ' ').replace('\r', ' '),
                    experiment
                ])

    print(f"Markdown summary saved to {markdown_file}")
    print(f"CSV summary saved to {csv_file}")

# Main function to run the script
def main():
    parser = argparse.ArgumentParser(description="Analyze experiment results and generate a summary report.")
    parser.add_argument("--results_dir", type=str, nargs="?", default=".", help="Path to the results directory containing experiment subdirectories.")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode logging for more detailed output.")

    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)

    results_dir = Path(args.results_dir)
    if not results_dir.exists():
        print(f"Error: Results directory {results_dir} does not exist")
        exit(1)

    exp_dirs = [d for d in results_dir.iterdir() if d.is_dir() and re.match(r"\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}", d.name)]

    if not exp_dirs:
        print(f"No experiment directories found in {results_dir}")
        exit(0)

    summary = generate_summary_statistics(exp_dirs)
    save_summary(summary, results_dir)

if __name__ == "__main__":
    main()