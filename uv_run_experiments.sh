#!/bin/bash

# Default values
MODEL_PROVIDER="openai"
MODEL_NAME="gpt-4"
TOTAL_RUNS=1
MAX_STEPS=100
VISUAL_EFFECTS=true
USE_HTML=false
USE_AXTREE=true
USE_SCREENSHOT=false
RESULTS_DIR="./results"

# Add default system message after other default values
SYSTEM_MESSAGE="""# Instructions

Review the current state of the page and all other information to find the best
possible next action to accomplish your goal. Your answer will be interpreted
and executed by a program, make sure to follow the formatting instructions. 
Exempt from visiting any external websites which are not provided explicitly."""

# Array of task names
TASKS=(
    'workarena.servicenow.order-apple-mac-book-pro15'
    'workarena.servicenow.order-apple-watch'
    'workarena.servicenow.order-developer-laptop'
    'workarena.servicenow.order-development-laptop-p-c'
    'workarena.servicenow.order-ipad-mini'
    'workarena.servicenow.order-ipad-pro'
    'workarena.servicenow.order-loaner-laptop'
    'workarena.servicenow.order-sales-laptop'
    'workarena.servicenow.order-standard-laptop'
)

# Help function
function show_help {
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  -p, --provider       Model provider (openai, anthropic, groq) (default: openai)"
    echo "  -m, --model-name     Model name (default: gpt-4)"
    echo "  -r, --runs           Total number of runs (default: 1)"
    echo "  -v, --visual         Enable visual effects (default: true)"
    echo "  -h, --html           Use HTML (default: false)"
    echo "  -a, --axtree         Use AXTree (default: true)"
    echo "  -s, --screenshot     Use screenshot (default: false)"
    echo "  --system-message    Custom system message for the agent"
    echo "  --max-steps         Maximum number of steps (default: 100)"
    echo "  --help              Show this help message"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--provider)
            MODEL_PROVIDER="$2"
            shift 2
            ;;
        -m|--model-name)
            MODEL_NAME="$2"
            shift 2
            ;;
        -r|--runs)
            TOTAL_RUNS="$2"
            shift 2
            ;;
        -v|--visual)
            VISUAL_EFFECTS="$2"
            shift 2
            ;;
        -h|--html)
            USE_HTML="$2"
            shift 2
            ;;
        -a|--axtree)
            USE_AXTREE="$2"
            shift 2
            ;;
        -s|--screenshot)
            USE_SCREENSHOT="$2"
            shift 2
            ;;
        --system-message)
            SYSTEM_MESSAGE="$2"
            shift 2
            ;;
        --max-steps)
            MAX_STEPS="$2"
            shift 2
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

echo "Starting experiments with following configuration:"
echo "Model provider: $MODEL_PROVIDER"
echo "Model name: $MODEL_NAME"
echo "Total runs: $TOTAL_RUNS"
echo "Visual effects: $VISUAL_EFFECTS"
echo "Use HTML: $USE_HTML"
echo "Use AXTree: $USE_AXTREE"
echo "Use Screenshot: $USE_SCREENSHOT"
echo "System message: $SYSTEM_MESSAGE"
echo "Max steps: $MAX_STEPS"

# Function to get random task
function get_random_task {
    local idx=$((RANDOM % ${#TASKS[@]}))
    echo "${TASKS[$idx]}"
}

# Run experiments
for ((i=1; i<=$TOTAL_RUNS; i++)); do
    TASK=$(get_random_task)
    echo "Run $i/$TOTAL_RUNS: Running task $TASK"

    uv run --env-file .env agents/simple_agent/run_demo.py \
        --model_provider "$MODEL_PROVIDER" \
        --task_name "$TASK" \
        --model_name "$MODEL_NAME" \
        --max_steps "$MAX_STEPS" \
        --visual_effects "$VISUAL_EFFECTS" \
        --use_html "$USE_HTML" \
        --use_axtree "$USE_AXTREE" \
        --use_screenshot "$USE_SCREENSHOT" \
        --system_message "$SYSTEM_MESSAGE"

    # Check if the run was successful
    if [ $? -ne 0 ]; then
        echo "Error in run $i with task $TASK"
    fi
done

# Generate analysis after all runs are complete
echo "Generating experiment analysis..."
uv run --env-file .env experiments/logging/trace_formatter.py \
    --results_dir "$RESULTS_DIR" \
    --system_message "$SYSTEM_MESSAGE"

# generating summary statistics
echo "Generating summary statistics..."
uv run --env-file .env experiments/statistics/summary_statistics_report.py "$RESULTS_DIR"

echo "All experiments and analysis complete!"

# # Basic run with default values (using OpenAI GPT-4)
# ./run_experiments.sh

# # Run with specific model provider and model name
# ./run_experiments.sh --provider "anthropic" --model-name "claude-3-sonnet-20240229"

# # Run with multiple options
# ./run_experiments.sh \
#     --provider "openai" \
#     --model-name "gpt-4" \
#     --runs 3 \
#     --max-steps 50 \
#     --visual true \
#     --html false \
#     --axtree true \
#     --screenshot false

# # Run with Groq and custom system message
# ./run_experiments.sh \
#     --provider "groq" \
#     --model-name "mixtral-8x7b-32768" \
#     --system-message "Custom instructions here" \
#     --runs 1

# # Show help
# ./run_experiments.sh --help