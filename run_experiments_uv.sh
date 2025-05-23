#!/bin/bash

# Values: default, alternatives
MODEL_PROVIDER="anthropic" # MODEL_PROVIDER= deepseek, openai, anthropic, google, groq, deepseek, ollama
MODEL_NAME="claude-3-7-sonnet-20250219" # MODEL_NAME= deepseek-reasoner, gpt-4o-2024-11-20, gpt-4o-2024-08-06, chatgpt-4o-latest, o3-mini-2025-01-31, claude-3-5-sonnet-20241022, claude-3-7-sonnet-20250219, gemini-2.0-flash-thinking-exp, gemini-2.0-flash, gemini-2.0-flash-lite-preview-02-05
TOTAL_RUNS=1
MAX_STEPS=15
VISUAL_EFFECTS=true
USE_HTML=false
USE_AXTREE=true
USE_SCREENSHOT=false
RESULTS_DIR="./results"
PARALLEL_TASKS=1 # Add new default value after other defaults
AGENT_TYPE="workflow"  # AGENT_TYPE= simple, workflow

# Add default system message after other default values
SYSTEM_MESSAGE="""# Instructions

Review the current state of the page and all other information to find the best
possible next action to accomplish your goal. Your answer will be interpreted
and executed by a program, make sure to follow the formatting instructions.
Do not visit any external websites outside from the servicenow.com domain unless they are provided explicitly."""

# Array of task names
TASKS=(
    # 'workarena.servicenow.order-apple-mac-book-pro15'
    # 'workarena.servicenow.order-apple-watch'
    # 'workarena.servicenow.order-developer-laptop'
    # 'workarena.servicenow.order-development-laptop-p-c'
    'workarena.servicenow.order-ipad-mini'
    # 'workarena.servicenow.order-ipad-pro'
    # 'workarena.servicenow.order-loaner-laptop'
    # 'workarena.servicenow.order-sales-laptop'
    # 'workarena.servicenow.order-standard-laptop'
)

# Array of config IDs corresponding to each task (integers only)
CONFIG_IDS=(
    # 0  # config ID for order-apple-mac-book-pro15
    # 0  # config ID for order-apple-watch
    # 0  # config ID for order-developer-laptop
    # 0  # config ID for order-development-laptop-p-c
    2  # config ID for order-ipad-mini
    # 0  # config ID for order-ipad-pro
    # 0  # config ID for order-loaner-laptop
    # 0  # config ID for order-sales-laptop
    # 0  # config ID for order-standard-laptop
)

# Help function
function show_help {
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  -p, --provider       Model provider (openai, anthropic, groq, deepseek, ollama, google) (default: openai)"
    echo "  -m, --model-name     Model name (default: gpt-4)"
    echo "  -r, --runs           Total number of runs (default: 1)"
    echo "  -v, --visual         Enable visual effects (default: true)"
    echo "  -h, --html           Use HTML (default: false)"
    echo "  -a, --axtree         Use AXTree (default: true)"
    echo "  -s, --screenshot     Use screenshot (default: false)"
    echo "  --system-message    Custom system message for the agent"
    echo "  --max-steps         Maximum number of steps (default: 100)"
    echo "  -j, --jobs           Number of parallel tasks (default: 1)"
    echo "  -d, --results-dir    Directory for results (default: ./results)"
    echo "  --agent-type         Type of agent to use (simple or workflow) (default: simple)"
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
        -j|--jobs)
            PARALLEL_TASKS="$2"
            shift 2
            ;;
        -d|--results-dir)
            RESULTS_DIR="$2"
            shift 2
            ;;
        --agent-type)
            AGENT_TYPE="$2"
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
echo "Agent type: $AGENT_TYPE"
echo "Model provider: $MODEL_PROVIDER"
echo "Model name: $MODEL_NAME"
echo "Total runs: $TOTAL_RUNS"
echo "Visual effects: $VISUAL_EFFECTS"
echo "Use HTML: $USE_HTML"
echo "Use AXTree: $USE_AXTREE"
echo "Use Screenshot: $USE_SCREENSHOT"
echo "System message: $SYSTEM_MESSAGE"
echo "Max steps: $MAX_STEPS"
echo "Parallel tasks: $PARALLEL_TASKS"
echo "Results directory: $RESULTS_DIR"

# Function to get random task
function get_random_task {
    local idx=$((RANDOM % ${#TASKS[@]}))
    local task=${TASKS[$idx]}
    local config_id=${CONFIG_IDS[$idx]}
    echo "$task $config_id"
}

# Update the task list generation to avoid empty tasks
echo "Preparing task list..."
TASK_LIST=""
for ((i=1; i<=$TOTAL_RUNS; i++)); do
    TASK_INFO=$(get_random_task)
    TASK=$(echo $TASK_INFO | cut -d' ' -f1)
    CONFIG_ID=$(echo $TASK_INFO | cut -d' ' -f2)
    
    if [ $i -eq $TOTAL_RUNS ]; then
        TASK_LIST+="$TASK $CONFIG_ID"  # No newline for last item
    else
        TASK_LIST+="$TASK $CONFIG_ID\n"
    fi
done

# Add debug output before parallel execution
echo "Generated tasks with config IDs:"
echo -e "$TASK_LIST"

# Determine the agent path based on agent type
AGENT_PATH="agents/simple_agent"
if [ "$AGENT_TYPE" = "workflow" ]; then
    AGENT_PATH="agents/workflow_agent"
fi

# Execute tasks in parallel with dynamic agent path
echo -e "$TASK_LIST" | grep -v '^$' | parallel --colsep ' ' -j "$PARALLEL_TASKS" \
    uv run --env-file .env ${AGENT_PATH}/run_demo.py \
        --model_provider "$MODEL_PROVIDER" \
        --task_name {1} \
        --model_name "$MODEL_NAME" \
        --max_steps "$MAX_STEPS" \
        --visual_effects "$VISUAL_EFFECTS" \
        --use_html "$USE_HTML" \
        --use_axtree "$USE_AXTREE" \
        --use_screenshot "$USE_SCREENSHOT" \
        --system_message "'$SYSTEM_MESSAGE'" \
        --results_dir "$RESULTS_DIR" \
        --config_id {2}

# Generate analysis after all runs are complete
echo "Generating experiment analysis..."
uv run --env-file .env experiments/logging/trace_formatter.py \
    --results_dir "$RESULTS_DIR" \
    --system_message "$SYSTEM_MESSAGE"

# generating summary statistics
echo "Generating summary statistics..."
uv run --env-file .env experiments/statistics/summary_statistics_report.py --results_dir "$RESULTS_DIR"

echo "All experiments and analysis complete!"

# # Basic run with default values (using OpenAI GPT-4)
# ./run_experiments.sh

# # Run with specific model provider and model name
# ./run_experiments.sh --provider "anthropic" --model-name "claude-3-sonnet-20240229"

# # Run with multiple options
# ./run_experiments.sh \
#     --provider "openai" \
#     --model-name "gpt-4o" \
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

# # Run with RAG agent
# python3 agents/rag_agent/run_demo.py \
#     --model_provider "openai" \
#     --model_name "gpt-4" \
#     --task_name "workarena.servicenow.order-apple-mac-book-pro15" \
#     --visual_effects true \
#     --use_html false \
#     --use_axtree true \
#     --use_screenshot false \
#     --max_steps 100

# Add a DeepSeek example in the comments
# # Run with DeepSeek
# ./run_experiments.sh \
#     --provider "deepseek" \
#     --model-name "deepseek-chat" \
#     --runs 1

# Add an Ollama example in the comments
# # Run with Ollama
# ./run_experiments.sh \
#     --provider "ollama" \
#     --model-name "deepseek-r1:14b" \
#     --runs 1

# Add new example in comments
# # Run with parallel execution
# ./run_experiments.sh \
#     --provider "openai" \
#     --model-name "gpt-4" \
#     --runs 10 \
#     --jobs 4

# Add new example in comments
# # Run with custom results directory
# ./run_experiments.sh \
#     --provider "openai" \
#     --model-name "gpt-4" \
#     --results-dir "./custom_results" \
#     --runs 1

# Add a Google example in the comments
# # Run with Google Gemini
# ./run_experiments.sh \
#     --provider "google" \
#     --model-name "gemini-1.5-pro" \
#     --runs 1

# Add example comments for different agent types
# # Run with simple agent (default)
# ./run_experiments.sh

# # Run with workflow agent
# ./run_experiments.sh --agent-type "workflow"

# # Run workflow agent with specific configuration
# ./run_experiments.sh \
#     --agent-type "workflow" \
#     --provider "openai" \
#     --model-name "gpt-4" \
#     --runs 3