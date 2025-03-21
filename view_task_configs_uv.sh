#!/bin/bash

# Default values
OUTPUT_DIR="./cache/task_configs/"
SAVE_MAPPINGS=true
LIST_ONLY=false

# Array of default tasks (uncomment the ones you want to use by default)
TASKS=(
    # "order_apple_mac_book_pro15_task"
    # "order_apple_watch_task"
    # "order_developer_laptop_task"
    "order_development_laptop_pc_task"
    # "order_ipad_mini_task"
    # "order_ipad_pro_task"
    # "order_loaner_laptop_task"
    # "order_sales_laptop_task"
    # "order_standard_laptop_task"
)

# Help function
function show_help {
    echo "Usage: $0 [options] [task_names...]"
    echo "Options:"
    echo "  -o, --output-dir     Directory to save mapping files (default: ./cache/task_configs/)"
    echo "  -s, --save           Save the mappings to files (default: false)"
    echo "  -l, --list           Only list available task configurations (default: false)"
    echo "  --help               Show this help message"
    echo ""
    echo "Examples:"
    echo "  # View a specific task configuration"
    echo "  $0 order_ipad_mini_task"
    echo ""
    echo "  # View multiple task configurations"
    echo "  $0 order_ipad_mini_task order_apple_watch_task"
    echo ""
    echo "  # List all available task configurations"
    echo "  $0 --list"
    echo ""
    echo "  # View a task and save its mapping"
    echo "  $0 --save order_ipad_mini_task"
}

# Parse command line arguments
CUSTOM_TASKS=()
while [[ $# -gt 0 ]]; do
    case $1 in
        -o|--output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        -s|--save)
            SAVE_MAPPINGS=true
            shift
            ;;
        -l|--list)
            LIST_ONLY=true
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        -*)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
        *)
            # Add to custom tasks array if it's not an option
            CUSTOM_TASKS+=("$1")
            shift
            ;;
    esac
done

# If custom tasks specified, replace the default tasks
if [ ${#CUSTOM_TASKS[@]} -gt 0 ]; then
    TASKS=("${CUSTOM_TASKS[@]}")
fi

echo "Task Configuration Viewer"
echo "========================="
echo "Output directory: $OUTPUT_DIR"
echo "Save mappings: $SAVE_MAPPINGS"

# Create the script command
SCRIPT_CMD="uv run experiments/utils/view_task_configs.py"

# Handle list-only mode
if [ "$LIST_ONLY" = true ]; then
    echo "Listing all available task configurations..."
    $SCRIPT_CMD --list
    exit 0
fi

# If no tasks specified and not in list mode, show help
if [ ${#TASKS[@]} -eq 0 ] && [ "$LIST_ONLY" = false ]; then
    echo "No tasks specified. Use --help for usage information."
    show_help
    exit 1
fi

# Process each task
for ((i=0; i<${#TASKS[@]}; i++)); do
    TASK="${TASKS[$i]}"
    echo ""
    echo "Processing task: $TASK"
    
    # Remove .json extension if present to ensure consistent handling
    TASK_BASE=${TASK%.json}
    TASK_NAME="${TASK_BASE}.json"
    
    # Construct the command
    CMD="$SCRIPT_CMD --task $TASK_NAME"
    
    # Add save option if requested
    if [ "$SAVE_MAPPINGS" = true ]; then
        CMD="$CMD --save --output-dir $OUTPUT_DIR"
    fi
    
    # Execute the command
    echo "Running: $CMD"
    eval "$CMD"
    
    # Add a separator between tasks
    if [ $i -lt $((${#TASKS[@]} - 1)) ]; then
        echo ""
        echo "=================================================="
    fi
done

echo ""
echo "All task configurations processed!"

# # List all available task configurations
# ./experiments/utils/view_task_mappings.sh --list

# # View a specific task configuration
# ./experiments/utils/view_task_mappings.sh order_ipad_mini_task.json

# # View multiple task configurations
# ./experiments/utils/view_task_mappings.sh order_ipad_mini_task.json order_apple_watch_task.json

# # View and save mappings for multiple tasks
# ./experiments/utils/view_task_mappings.sh --save order_ipad_mini_task.json order_developer_laptop_task.json

# # Use a custom output directory
# ./experiments/utils/view_task_mappings.sh --save --output-dir ./my_mappings/ order_ipad_mini_task.json

# # Run in interactive mode
# ./experiments/utils/view_task_mappings.sh --interactive