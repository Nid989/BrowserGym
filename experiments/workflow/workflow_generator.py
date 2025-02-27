"""
Task Workflow Generator

This module implements a workflow generation system using LangChain and Anthropic's Claude
to create detailed, data-driven task workflows based on historical execution traces.
"""

import os
import re
import getpass
import pandas as pd
from typing import List, Dict, Optional, Literal
from typing_extensions import TypedDict
from pathlib import Path

from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langchain_anthropic import ChatAnthropic
from langgraph.graph import MessagesState, StateGraph, START, END


# Constants
# source directory containing past traces to derive the workflow from
TRACES_PATH = "results_local/claude-3.5-sonnet"

SYSTEM_MESSAGE = """Objective:
Create a detailed, optimal workflow for a specified task. Your final output should be clear, actionable, and supported by data from past execution traces.

Instructions:

1. Review the Sample Workflow:
   - You will be provided with a sample workflow for a completely different task.
   - Examine this sample carefully to understand the expected structure, format, and level of detail for your output.

2. Understand the Task:
   - Focus on the specific task provided (e.g., order.ipad-pro).
   - Note any task-specific requirements or constraints mentioned.

3. Utilize Available Tools:
   - You have access to multiple tools designed to assist in gathering information.
   - Use these tools in the correct sequence to access a list of folders, where each folder contains execution traces from past instances of the task.

4. Access and Process Traces:
   - Retrieve the list of folders using the provided tools.
   - Open each folder and examine the trace files to extract key insights, steps, and data relevant to the task.
   - **Important:** Do not generate the workflow based on a single trace or one selected folder. Each folder may contain valuable and distinct information. Be explorative and integrate insights from multiple traces to form a comprehensive understanding of the task.
   - Integrate the information from each trace into your workflow draft.

5. Iterative Refinement:
   - Continuously update and refine your workflow based on the new insights from each trace.
   - After processing each folder, assess whether additional information from other traces can further optimize the workflow.
   - Repeat this process iteratively until you determine that no further improvements can be made.

6. Finalization:
   - Once you believe that all valuable insights have been incorporated and the workflow is in its optimal state, finalize the workflow.
   - Ensure that every step in the workflow is clear, actionable, and backed by data from the traces.

7. Output:
   - Provide the complete, finalized workflow as your output.

Additional Notes:
   - Be explicit in detailing each step of your process.
   - Document any assumptions or decision points briefly if needed.
   - The goal is to have a comprehensive, optimized workflow that can be directly applied to the given task."""

class DataFrameManager:
    """Manages the global DataFrame instance and related operations."""

    _instance = None
    _csv_file = None
    _df = None

    @classmethod
    def initialize(cls, base_path: Path) -> None:
        """Initialize the DataFrame from a CSV file in the specified directory."""
        if cls._df is None:
            cls._csv_file = cls._find_csv_file(base_path)
            cls._df = pd.read_csv(cls._csv_file, delimiter=";")

    @staticmethod
    def _find_csv_file(base_path: Path) -> Path:
        """Find the first CSV file in the specified directory."""
        csv_files = list(base_path.glob('*.csv'))
        if not csv_files:
            raise FileNotFoundError("No CSV file found in the directory")
        return csv_files[0]

    @classmethod
    def get_df(cls) -> pd.DataFrame:
        """Get the DataFrame instance."""
        return cls._df

class HistoryManager:
    """Manages the retrieval and caching of execution trace histories."""

    def __init__(self, base_path: Path = Path(TRACES_PATH)):
        self.base_path = base_path
        self._history_cache: Dict[str, str] = {}
        self._is_initialized = False

    def _extract_trace_content(self, markdown_content: str) -> Optional[str]:
        """Extract trace content from markdown file."""
        sections = markdown_content.split('# 2 - Instance Type')
        if len(sections) < 2:
            return None

        instance_type_section = sections[1]
        instance_steps = re.findall(r'## InstanceStep(\d+)', instance_type_section)
        if not instance_steps:
            return None

        last_step = max([int(step) for step in instance_steps])
        step_sections = instance_type_section.split(f'## InstanceStep{last_step:03d}')
        if len(step_sections) < 2:
            return None

        last_step_content = step_sections[1]
        history_sections = last_step_content.split('### History of Past Actions')
        if len(history_sections) < 2:
            return None

        history_content = history_sections[1].split('### Next Action')[0].strip()
        return history_content if history_content else None

    def _initialize_cache(self):
        """Initialize the history cache with successful traces."""
        if self._is_initialized:
            return

        df = DataFrameManager.get_df()
        successful_traces = df[df['Success'] == 'Yes']['Folder Name'].tolist()

        for trace_folder in self.base_path.glob('*'):
            if trace_folder.name in successful_traces:
                analysis_file = trace_folder / 'experiment_analysis.md'
                if analysis_file.exists():
                    content = analysis_file.read_text(encoding='utf-8')
                    history_content = self._extract_trace_content(content)
                    if history_content:
                        self._history_cache[trace_folder.name] = history_content

        self._is_initialized = True

    def get_trace(self, trace_id: str) -> Optional[str]:
        """Retrieve the history for a specific trace ID."""
        self._initialize_cache()
        return self._history_cache.get(trace_id)

# Tool definitions
@tool
def describe_dataframe() -> str:
    """
    Extracts comprehensive DataFrame information including metadata and column details.

    Returns:
        str: A structured overview of the DataFrame containing:
             - DataFrame Metadata (shape, memory usage, data types summary)
             - Column-wise Information (types, ranges, samples, null info)

    Raises:
        ValueError: If DataFrame analysis encounters any errors

    Examples:
        Assuming a DataFrame 'df' exists with sales data:
        >>> df = pd.DataFrame({
        ...     'date': ['2024-01-01', '2024-01-02'],
        ...     'sales': [100, 200],
        ...     'category': ['A', 'B']
        ... })
        >>> description = describe_dataframe()
        >>> print(description)
        DataFrame Metadata:
        - Dimensions: 2 rows × 3 columns
        - Memory Usage: 1.2 KB
        - Data Types Summary: numeric (1), categorical (1), datetime (1)
        ...
    """
    try:
        df = DataFrameManager.get_df()
        if df.empty:
            return "ERROR: DataFrame is empty"

        metadata = ["DataFrame Metadata:"]

        # Basic DataFrame metadata
        rows, cols = df.shape
        metadata.append(f"- Dimensions: {rows:,} rows × {cols} columns")

        # Memory usage
        memory_usage = df.memory_usage(deep=True).sum()
        memory_str = f"{memory_usage/1024:.1f} KB" if memory_usage < 1024**2 else f"{memory_usage/1024**2:.1f} MB"
        metadata.append(f"- Memory Usage: {memory_str}")

                # Column-wise information
        metadata.append("\nColumn Information:")

        for col in df.columns:
            col_memory = df[col].memory_usage(deep=True)
            col_memory_str = f"{col_memory/1024:.1f} KB" if col_memory < 1024**2 else f"{col_memory/1024**2:.1f} MB"
            non_null_pct = (df[col].count() / len(df)) * 100

            # Handle numeric columns
            if df[col].dtype in ['int64', 'float64']:
                if df[col].count() > 0:
                    min_val = df[col].min()
                    max_val = df[col].max()
                    metadata.append(
                        f"- {col} (numeric):\n"
                        f"  range: {min_val} to {max_val}\n"
                        f"  non-null: {non_null_pct:.1f}%\n"
                        f"  memory: {col_memory_str}\n"
                        f"  dtype: {df[col].dtype}"
                    )
                else:
                    metadata.append(
                        f"- {col} (numeric):\n"
                        f"  range: no non-null values\n"
                        f"  non-null: 0%\n"
                        f"  memory: {col_memory_str}\n"
                        f"  dtype: {df[col].dtype}"
                    )

            # Handle datetime columns
            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                if df[col].count() > 0:
                    min_date = df[col].min()
                    max_date = df[col].max()
                    metadata.append(
                        f"- {col} (datetime):\n"
                        f"  range: {min_date.date()} to {max_date.date()}\n"
                        f"  non-null: {non_null_pct:.1f}%\n"
                        f"  memory: {col_memory_str}\n"
                        f"  dtype: {df[col].dtype}"
                    )

            # Handle categorical/text columns
            else:
                unique_vals = df[col].dropna().unique()[:5]
                sample_values = [f"'{str(val)}'" for val in unique_vals]
                total_unique = df[col].nunique()

                if len(sample_values) < total_unique:
                    sample_values.append(f"... ({total_unique} total unique values)")

                metadata.append(
                    f"- {col} ({df[col].dtype}):\n"
                    f"  distinct values: {', '.join(sample_values)}\n"
                    f"  non-null: {non_null_pct:.1f}%\n"
                    f"  memory: {col_memory_str}\n"
                    f"  dtype: {df[col].dtype}"
                )

        return "\n".join(metadata)

    except Exception as e:
        return f"ERROR: Error analyzing DataFrame: {str(e)}"

@tool
def query_dataframe(query: str, columns: List[str] = None) -> str:
    """
    Filters a DataFrame using a query and extracts specified columns as a comma-separated string.

    Args:
        query (str): A pandas query string to filter the DataFrame.
                     Example: "age > 25 and city == 'New York'"
        columns (List[str], optional): List of column names to extract from the filtered DataFrame.
                                     Must be existing columns in the DataFrame.
                                     If None, all columns will be used.
                                     Example: ["name", "email", "phone"]

    Returns:
        str: A comma-separated string containing the values from the specified columns
             of the filtered DataFrame.
             Example: "John Doe, john@email.com, 123-456-7890"

    Returns:
        str: A multi-line string containing the values from the specified columns,
             with columns separated by commas and rows by newlines.
             First row contains column names.
             Example:
             "name, email, phone
              John Doe, john@email.com, 123-456-7890
              Jane Smith, jane@email.com, 987-654-3210"

    Note:
        - The query must follow pandas query syntax (https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.query.html)
        - All specified columns must exist in the DataFrame before extraction
        - Empty results will return an empty string
    """
    try:
        df = DataFrameManager.get_df()
        columns = columns if columns is not None else df.columns.tolist()

        # Validate columns
        missing_cols = [col for col in columns if col not in df.columns]
        if missing_cols:
            return f"ERROR: Following columns do not exist in DataFrame: {', '.join(missing_cols)}"

        # Execute query
        try:
            filtered_df = df.query(query)
        except Exception as e:
            return f"ERROR: Invalid query syntax: {str(e)}"

        # Format results
        result_df = filtered_df[columns]
        result_strings = [', '.join(columns)]
        for _, row in result_df.iterrows():
            row_values = [str(val) if pd.notna(val) else '' for val in row]
            result_strings.append(', '.join(row_values))

        return '\n'.join(result_strings)

    except Exception as e:
        return f"ERROR: Error processing query: {str(e)}"

@tool
def retrieve_trace(folder_name: str) -> str:
    """
    Retrieve the execution trace stored in a given folder.

    This function returns a structured record of actions and decisions taken
    during a specific execution.

    Args:
        folder_name (str): Name of the folder containing the trace.
                           Example format: {timestamp}_DemoAgentArgs_on_workarena.servicenow.{task}_{id}.

    Returns:
        Optional[str]: A formatted string representing the trace if found.
                       Returns None if the trace is unavailable or invalid.

    Example Output:
        #### PastAction000
        ##### Applied Reasoning
        ...

    Notes:
        The function will return None if:
        - The specified trace does not exist.
        - The execution was unsuccessful.
        - The trace data is missing.
    """
    try:
        if not hasattr(retrieve_trace, '_manager'):
            retrieve_trace._manager = HistoryManager()

        result = retrieve_trace._manager.get_trace(folder_name)
        if result is None:
            return "ERROR: Trace not found or invalid"
        return result

    except Exception as e:
        return f"ERROR: Error retrieving trace: {str(e)}"

def create_workflow_agent(base_path: Path) -> StateGraph:
    """Create and configure the workflow generation agent."""

    # Initialize components
    DataFrameManager.initialize(base_path)
    llm = ChatAnthropic(model="claude-3-7-sonnet-20241022")
    tools = [describe_dataframe, query_dataframe, retrieve_trace]
    tools_by_name = {tool.name: tool for tool in tools}
    llm_with_tools = llm.bind_tools(tools)

    # Define node functions
    def llm_call(state: MessagesState):
        return {
            "messages": [
                llm_with_tools.invoke(
                    [SystemMessage(content=SYSTEM_MESSAGE)] + state["messages"]
                )
            ]
        }

    def tool_node(state: dict):
        result = []
        for tool_call in state["messages"][-1].tool_calls:
            tool = tools_by_name[tool_call["name"]]
            observation = tool.invoke(tool_call["args"])
            result.append(ToolMessage(content=observation, tool_call_id=tool_call["id"]))
        return {"messages": result}

    def should_continue(state: MessagesState) -> Literal["environment", END]:
        messages = state["messages"]
        return "Action" if messages[-1].tool_calls else END

    # Build workflow
    agent_builder = StateGraph(MessagesState)
    agent_builder.add_node("llm_call", llm_call)
    agent_builder.add_node("environment", tool_node)
    agent_builder.add_edge(START, "llm_call")
    agent_builder.add_conditional_edges(
        "llm_call",
        should_continue,
        {
            "Action": "environment",
            END: END,
        },
    )
    agent_builder.add_edge("environment", "llm_call")

    return agent_builder.compile()

def main(task_name: str = "order-ipad-mini", reference_task: str = None):
    """Main entry point for the workflow generator.

    Args:
        task_name: Name of the task to generate workflow for
        reference_task: Name of the task to use as reference workflow template
                       If None, defaults to order-ipad-mini
    """
    # Set up environment
    if not os.environ.get("ANTHROPIC_API_KEY"):
        os.environ["ANTHROPIC_API_KEY"] = getpass.getpass("Enter ANTHROPIC_API_KEY: ")

    # Initialize the workflow agent
    base_path = Path(TRACES_PATH)
    agent = create_workflow_agent(base_path)

    # # DEBUG: Preview DataFrame contents
    # df = DataFrameManager.get_df()
    # print("\n=== DataFrame Preview ===")
    # print("\nFirst 5 rows:")
    # print(df.head())
    # print("\nDataFrame Info:")
    # print(df.info())
    # print("\nColumn Names:")
    # print(df.columns.tolist())
    # print("=====================\n")

    # Load reference workflow
    reference_task = reference_task or "order-ipad-mini"
    current_file_dir = Path(__file__).parent
    workflow_path = current_file_dir / "resources" / reference_task / "workflow.txt"

    try:
        with open(workflow_path, 'r') as f:
            sample_workflow = f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"Reference workflow not found at {workflow_path}")

    # Generate workflow
    user_message = f"""Generate a workflow for the following task: {task_name}.
You are provided with a sample workflow:
{sample_workflow}"""

    # Invoke the agent
    messages = [HumanMessage(content=user_message)]
    result = agent.invoke({"messages": messages})

    # Print results
    for message in result["messages"]:
        message.pretty_print()

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Generate workflow for a specified task')
    parser.add_argument('--task-name', type=str, default="order-ipad-mini",
                      help='Name of the task to generate workflow for')
    parser.add_argument('--reference-task', type=str,
                      help='Name of the task to use as reference workflow template')

    args = parser.parse_args()
    main(task_name=args.task_name, reference_task=args.reference_task)
