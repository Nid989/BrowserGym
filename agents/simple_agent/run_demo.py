import argparse
import importlib.resources
import json
from pathlib import Path

# locally defined agent
from agent import DemoAgentArgs

# browsergym experiments utils
from browsergym.experiments import EnvArgs, ExpArgs, get_exp_result


def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ("yes", "true", "t", "y", "1"):
        return True
    elif v.lower() in ("no", "false", "f", "n", "0"):
        return False
    else:
        raise argparse.ArgumentTypeError("Boolean value expected.")


def parse_args():
    parser = argparse.ArgumentParser(description="Run experiment with hyperparameters.")
    parser.add_argument(
        "--model_name",
        type=str,
        default="gpt-4o-mini",
        help="OpenAI model name.",
    )
    parser.add_argument(
        "--model_provider",
        type=str,
        default="openai",
        choices=["openai", "anthropic", "groq", "deepseek", "ollama", "google"],
        help="Model provider to use (openai, anthropic, groq, deepseek, google, or ollama).",
    )
    parser.add_argument(
        "--task_name",
        type=str,
        default="openended",
        help="Name of the Browsergym task to run. If 'openended', you need to specify a 'start_url'",
    )
    parser.add_argument(
        "--start_url",
        type=str,
        default="https://www.google.com",
        help="Starting URL (only for the openended task).",
    )
    parser.add_argument(
        "--visual_effects",
        type=str2bool,
        default=True,
        help="Add visual effects when the agents performs actions.",
    )
    parser.add_argument(
        "--use_html",
        type=str2bool,
        default=False,
        help="Use HTML in the agent's observation space.",
    )
    parser.add_argument(
        "--use_axtree",
        type=str2bool,
        default=True,
        help="Use AXTree in the agent's observation space.",
    )
    parser.add_argument(
        "--use_screenshot",
        type=str2bool,
        default=False,
        help="Use screenshot in the agent's observation space.",
    )
    parser.add_argument(
        "--system_message",
        type=str,
        default="""\
# Instructions

Review the current state of the page and all other information to find the best
possible next action to accomplish your goal. Your answer will be interpreted
and executed by a program, make sure to follow the formatting instructions.
""",
        help="System message to be used by the agent.",
    )
    parser.add_argument(
        "--max_steps",
        type=int,
        default=100,
        help="Maximum number of steps for the environment.",
    )
    parser.add_argument(
        "--results_dir",
        type=str,
        default="./results",
        help="Directory for storing results",
    )
    parser.add_argument(
        "--config_id",
        type=int,
        default=None,
        help="ID of the task configuration to use",
    )

    return parser.parse_args()


def main():
    print(
        """\
Agent Evaluation Harness starting up ...
Creating simulation environment ..."""
    )

    args = parse_args()

    # setting up agent config
    agent_args = DemoAgentArgs(
        model_name=args.model_name,
        model_provider=args.model_provider,
        chat_mode=False,
        demo_mode="default" if args.visual_effects else "off",
        use_html=args.use_html,
        use_axtree=args.use_axtree,
        use_screenshot=args.use_screenshot,
        system_message=args.system_message,
        task_name=args.task_name,
    )

    # Setup task_kwargs based on whether config_id is provided
    task_kwargs = None

    # Only handle fixed_config if config_id is provided
    if args.config_id is not None and args.task_name.startswith("workarena.servicenow"):
        # Extract the task name after the "workarena.servicenow." prefix
        task_config_name = args.task_name.split(".", 2)[-1].replace("-", "_") + "_task"

        try:
            # Load configurations using importlib.resources
            config_content = importlib.resources.read_text(
                "browsergym.workarena.data_files.task_configs",
                f"{task_config_name}.json",
            )
            configs = json.loads(config_content)

            # Check if config_id is within valid range
            if 0 <= args.config_id < len(configs):
                fixed_config = configs[args.config_id]
                print(
                    f"Using configuration ID {args.config_id} for task {args.task_name}"
                )
                task_kwargs = {"fixed_config": fixed_config}
            else:
                print(
                    f"Warning: Config ID {args.config_id} is out of range (0-{len(configs) - 1}). Using default task behavior."
                )
        except Exception as e:
            print(f"Error loading configuration: {e}. Using default task behavior.")

    # setting up environment config
    env_args = EnvArgs(
        task_name=args.task_name,
        task_kwargs=task_kwargs,
        task_seed=None,
        max_steps=args.max_steps,
        headless=False,  # keep the browser open
        # use_chrome=args.use_chrome,
        # viewport={"width": 1500, "height": 1280},  # can be played with if needed
    )

    # for openended task, set environment and agent to interactive chat mode on a start url
    if args.task_name == "openended":
        agent_args.chat_mode = True
        env_args.wait_for_user_message = True
        env_args.task_kwargs = {"start_url": args.start_url}

    # setting up the experiment
    exp_args = ExpArgs(
        env_args=env_args,
        agent_args=agent_args,
    )

    # Update to use custom results directory
    exp_args.prepare(args.results_dir)
    # Allows recording the "exp_dir" name via terminal output in the "./run_experiment.sh" bash script.
    # Usual value; 'results/2025-04-22_23-13-02_DemoAgentArgs_on_workarena.servicenow.order-ipad-mini_28'
    # Desired value; '2025-04-22_23-13-02_DemoAgentArgs_on_workarena.servicenow.order-ipad-mini_28'
    exp_dir_path = Path(exp_args.exp_dir)
    results_dir_path = Path(args.results_dir)
    try:
        exp_dir_name = exp_dir_path.relative_to(results_dir_path)
    except ValueError:
        exp_dir_name = exp_dir_path.name
    # Print with a specific format for easy parsing by scripts
    print(f"EXPERIMENT_DIR={exp_dir_name}")

    exp_args.run()

    # loading and printing results
    exp_result = get_exp_result(exp_args.exp_dir)
    exp_record = exp_result.get_exp_record()

    for key, val in exp_record.items():
        print(f"{key}: {val}")


if __name__ == "__main__":
    main()
