import base64
import uuid 
import dataclasses
import io
import logging
import os, getpass

import numpy as np
from PIL import Image
from IPython.display import display
from IPython.display import Image as IPythonImage
from typing import Dict, List, Optional

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_openai.chat_models.base import BaseChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import START, END, StateGraph, MessagesState
from langgraph.prebuilt import tools_condition, ToolNode

from browsergym.core.action.highlevel import HighLevelActionSet
from browsergym.experiments import AbstractAgentArgs, Agent
from browsergym.utils.obs import flatten_axtree_to_str, flatten_dom_to_str, prune_html

logger = logging.getLogger(__name__)

def _set_env(var: str):
    if not os.environ.get(var):
        os.environ[var] = getpass.getpass(f"{var}: ")

_set_env("OPENAI_API_KEY")
_set_env("LANGCHAIN_API_KEY")
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "browsergym"

def image_to_jpg_base64_url(image: np.ndarray | Image.Image):
    """Convert a numpy array to a base64 encoded image url."""

    if isinstance(image, np.ndarray):
        image = Image.fromarray(image)
    if image.mode in ("RGBA", "LA"):
        image = image.convert("RGB")

    with io.BytesIO() as buffer:
        image.save(buffer, format="JPEG")
        image_base64 = base64.b64encode(buffer.getvalue()).decode()

    return f"data:image/jpeg;base64,{image_base64}"

# TODO: rename the class to something more meaningful.
class DemoAgent(Agent):
    """A agent using langgraph to utilize BrowserGym's functionalities."""

    def obs_preprocessor(self, obs: dict) -> dict:

        return {
            "chat_messages": obs["chat_messages"],
            "screenshot": obs["screenshot"],
            "goal_object": obs["goal_object"],
            "last_action": obs["last_action"],
            "last_action_error": obs["last_action_error"],
            "open_pages_urls": obs["open_pages_urls"],
            "open_pages_titles": obs["open_pages_titles"],
            "active_page_index": obs["active_page_index"],
            "axtree_txt": flatten_axtree_to_str(obs["axtree_object"]),
            "pruned_html": prune_html(flatten_dom_to_str(obs["dom_object"])),
        }
    
    def __init__(
        self,
        model_name: str,
        model_provider: str,
        chat_mode: bool,
        demo_mode: str,
        use_html: bool,
        use_axtree: bool,
        use_screenshot: bool,
        task_name: str,
        system_message: str = """\
# Instructions

Review the current state of the page and all other information to find the best
possible next action to accomplish your goal. Your answer will be interpreted
and executed by a program, make sure to follow the formatting instructions.
"""
    ) -> None:
        super().__init__()
        self.model_name = model_name
        self.model_provider = model_provider
        self.chat_mode = chat_mode
        self.use_html = use_html
        self.use_axtree = use_axtree
        self.use_screenshot = use_screenshot
        self.system_message = system_message
        self.task_name = task_name

        self.model_info = {
            "model_info": {
                "model_name": model_name,
                "model_provider": model_provider,
                "temperature": 0.0,
            }
        }

        if not hasattr(self, 'trace_id'):
            self.trace_id = str(uuid.uuid4())

        if not (use_html or use_axtree):
            raise ValueError(f"Either use_html or use_axtree must be set to True.")
        
        self.action_set = HighLevelActionSet(
            subsets=["chat", "tab", "nav", "bid", "infeas"], # define a subset of action space
            # subsets=["chat", "bid", "coord", "infeas"], # allow the agent to also use x, y coordinates
            strict=False, # less strict on the parsing of the actions
            multiaction=False, # does not enable the agent to take multiple actions at once
            demo_mode=demo_mode, # add visual effects
        )

        self.action_history = [] 

    def _create_workflow(self):
        workflow = StateGraph(MessagesState)
        
        # define necessary nodes 
        workflow.add_node("predict", self._predict)

        # add edges connecting defined nodes and start/end nodes
        workflow.add_edge(START, "predict")
        workflow.add_edge("predict", END)

        # compile graph 
        graph = workflow.compile()

        return graph

    def _predict(self, state: MessagesState) -> MessagesState:
        if self.model_provider == "openai":
            # Set temperature=1 for all o-series models
            is_o_series = any(self.model_name.startswith(prefix) for prefix in ["o1", "o3"])
            temperature = 1.0 if is_o_series else 0.0
            llm = ChatOpenAI(model=self.model_name, temperature=temperature)
        elif self.model_provider == "anthropic":
            llm = ChatAnthropic(model=self.model_name, temperature=0.0)
        elif self.model_provider == "groq":
            llm = ChatGroq(
                model=self.model_name, 
                temperature=0.0,     
                max_tokens=None,
                timeout=None,
                max_retries=2,
            )
        elif self.model_provider == "google":
            llm = ChatGoogleGenerativeAI(
                model=self.model_name,
                temperature=0.0,
                convert_system_message_to_human=True
            )
        elif self.model_provider == "deepseek":
            llm = BaseChatOpenAI(
                model=self.model_name,
                openai_api_key=os.environ["DEEPSEEK_API_KEY"],
                openai_api_base='https://api.deepseek.com',
                temperature=0.0
            )
        elif self.model_provider == "ollama":
            llm = ChatOllama(model=self.model_name, temperature=0.0)
        else:
            raise ValueError(f"Unsupported model provider: {self.model_provider}")
        
        response = llm.invoke(state['messages'])
        return {'messages': [response]}

    def _load_workflow_guide(self) -> str:
        """
        Load the workflow guide for a specific task from resources.
        
        Returns:
            str: The workflow guide text if found, otherwise a default message
        """
        if not self.task_name or "workarena.servicenow." not in self.task_name:
            return "No specific workflow guide available for this task."
        
        # Extract the last part of the task name after workarena.servicenow.
        task_folder = self.task_name.split("workarena.servicenow.")[-1]
        
        # Construct path to workflow file
        workflow_path = os.path.join(
            os.path.dirname(__file__),
            "resources",
            task_folder,
            "workflow.txt"
        )
        
        try:
            if os.path.exists(workflow_path):
                with open(workflow_path, "r") as f:
                    return f.read()
        except Exception as e:
            logger.warning(f"Failed to load workflow guide from {workflow_path}: {str(e)}")
        
        return "No specific workflow guide available for this task."

    def _build_context(self, obs):
        
        system_msgs = []
        user_msgs = []

        if self.chat_mode:
            system_msgs.append(
                {
                    "type": "text",
                    "text": f"""\
# Instructions

You are a UI Assistant, your goal is to help the user perform tasks using a web browser. You can
communicate with the user via a chat, to which the user gives you instructions and to which you
can send back messages. You have access to a web browser that both you and the user can see,
and with which only you can interact via specific commands.

Review the instructions from the user, the current state of the page and all other information
to find the best possible next action to accomplish your goal. Your answer will be interpreted
and executed by a program, make sure to follow the formatting instructions.
""",
                }
            )
            # append chat messages
            user_msgs.append(
                {
                    "type": "text",
                    "text": f"""\
# Chat Messages
""",
                }
            )
            for msg in obs["chat_messages"]:
                if msg["role"] in ("user", "assistant", "infeasible"): # TODO: check what is `infeasible` (guess: is it the system message, e.g., instructions stating the task?)
                    user_msgs.append(
                        {
                            "type": "text",
                            "text": f"""\
- [{msg['role']}] {msg['message']}
""",
                        }
                    )
                elif msg["role"] == "user_image":
                    user_msgs.append({"type": "image_url", "image_url": msg["message"]})
                else:
                    raise ValueError(f"Unexpected chat message role {repr(msg['role'])}")

        else:
            assert obs["goal_object"], "The goal is missing."
            system_msgs.append(
                {
                    "type": "text",
                    "text": self.system_message,
                }
            )
            # append goal
            user_msgs.append(
                {
                    "type": "text",
                    "text": f"""\
# Goal
""",
                }
            )
            # goal_object is directly presented as a list of openai-style messages
            user_msgs.extend(obs["goal_object"])

        # append url of all open tabs
        user_msgs.append(
            {
                "type": "text",
                "text": f"""\
# Currently open tabs
""",
            }
        )
        for page_index, (page_url, page_title) in enumerate(
            zip(obs["open_pages_urls"], obs["open_pages_titles"])
        ):
            user_msgs.append(
                {
                    "type": "text",
                    "text": f"""\
Tab {page_index}{" (active tab)" if page_index == obs["active_page_index"] else ""}
  Title: {page_title}
  URL: {page_url}
""",
                }
            )

        # append page AXTree (if asked)
        if self.use_axtree:
            user_msgs.append(
                {
                    "type": "text",
                    "text": f"""\
# Current page Accessibility Tree

{obs["axtree_txt"]}

""",
                }
            )
        # append page HTML (if asked)
        if self.use_html:
            user_msgs.append(
                {
                    "type": "text",
                    "text": f"""\
# Current page DOM

{obs["pruned_html"]}

""",
                }
            )

        # append page screenshot (if asked)
        if self.use_screenshot:
            user_msgs.append(
                {
                    "type": "text",
                    "text": """\
# Current page Screenshot
""",
                }
            )
            user_msgs.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": image_to_jpg_base64_url(obs["screenshot"]),
                        "detail": "auto",
                    },  # Literal["low", "high", "auto"] = "auto"
                }
            )

        # append action space description
        user_msgs.append(
            {
                "type": "text",
                "text": f"""\
# Action Space

{self.action_set.describe(with_long_description=False, with_examples=True)}

Here are examples of actions with chain-of-thought reasoning:

I now need to click on the Submit button to send the form. I will use the click action on the button, which has bid 12.
```click("12")```

I found the information requested by the user, I will send it to the chat.
```send_msg_to_user("The price for a 15\\" laptop is 1499 USD.")```

""",
            }
        )

        # append past actions (and last error message) if any
        if self.action_history:
            user_msgs.append(
                {
                    "type": "text",
                    "text": f"""\
# History of past actions
""",
                }
            )
            user_msgs.extend(
                [
                    {
                        "type": "text",
                        "text": f"""\

{action}
""",
                    }
                    for action in self.action_history
                ]
            )

            if obs["last_action_error"]:
                user_msgs.append(
                    {
                        "type": "text",
                        "text": f"""\
# Error message from last action

{obs["last_action_error"]}

""",
                    }
                )

        # Load and add workflow guide
        workflow_guide = self._load_workflow_guide()
        user_msgs.append(
            {
                "type": "text",
                "text": f"""\
# Guide

{workflow_guide}
"""
            }
        )

        # ask for the next action
        user_msgs.append(
            {
                "type": "text",
                "text": f"""\
# Next action

You will now think step by step and produce your next best action. Reflect on your past actions, any resulting error message, and the current state of the page before deciding on your next action.
""",
            }
        )

        prompt_text_strings = []
        for message in system_msgs + user_msgs:
            match message["type"]:
                case "text":
                    prompt_text_strings.append(message["text"])
                case "image_url":
                    image_url = message["image_url"]
                    if isinstance(message["image_url"], dict):
                        image_url = image_url["url"]
                    if image_url.startswith("data:image"):
                        prompt_text_strings.append(
                            "image_url: " + image_url[:30] + "... (truncated)"
                        )
                    else:
                        prompt_text_strings.append("image_url: " + image_url)
                case _:
                    raise ValueError(
                        f"Unknown message type {repr(message['type'])} in the task goal."
                    )
        full_prompt_txt = "\n".join(prompt_text_strings)
        logger.info(full_prompt_txt)

        # For Groq models, we need to concatenate the content into a single string
        if self.model_provider == "groq":
            # Check for any image content and raise exception if found
            for msg in system_msgs + user_msgs:
                if isinstance(msg, dict) and "image_url" in msg:
                    raise ValueError("ChatGroq does not support image inputs. Please use a different model provider for image processing.")
            
            # Concatenate system messages
            system_content = "\n".join(
                msg["text"] if isinstance(msg, dict) and "text" in msg 
                else str(msg) for msg in system_msgs
            )
            
            # Concatenate user messages
            user_content = "\n".join(
                msg["text"] if isinstance(msg, dict) and "text" in msg 
                else str(msg) for msg in user_msgs
            )
            
            return [
                SystemMessage(content=system_content),
                HumanMessage(content=user_content)
            ]
        
        # For other models, return the original format
        return [SystemMessage(content=system_msgs), HumanMessage(content=user_msgs)]

    def get_action(self, obs: dict) -> tuple[str, dict]:

        # initialize BrowsergymState with obs 
        initial_state = MessagesState(messages=self._build_context(obs))

        # create and run the graph
        graph = self._create_workflow()
        display(IPythonImage(graph.get_graph().draw_mermaid_png()))
        response = graph.invoke(initial_state)

        # get the predicted action
        action = response["messages"][-1].content
        
        # update action history
        self.action_history.append(action)

        for message in response["messages"]:
            message.pretty_print()

        return action, {**self.model_info, "trace_id": self.trace_id}

@dataclasses.dataclass
class DemoAgentArgs(AbstractAgentArgs):
    """
    This class is meant to store the arguments that define the agent. 

    By isolating them in a dataclass, this ensures serialization without storing
    internal states of the agent.
    """

    model_name: str = "gpt-4o"
    model_provider: str = "openai"
    chat_mode: bool = False
    demo_mode: str = "off"
    use_html: bool = False
    use_axtree: bool = True
    use_screenshot: bool = False
    task_name: str = ""
    system_message: str = """\
# Instructions

Review the current state of the page and all other information to find the best
possible next action to accomplish your goal. Your answer will be interpreted
and executed by a program, make sure to follow the formatting instructions.
"""

    def make_agent(self):
        return DemoAgent(
            model_name=self.model_name,
            model_provider=self.model_provider,
            chat_mode=self.chat_mode,
            demo_mode=self.demo_mode,
            use_html=self.use_html,
            use_axtree=self.use_axtree,
            use_screenshot=self.use_screenshot,
            task_name=self.task_name,
            system_message=self.system_message
        )