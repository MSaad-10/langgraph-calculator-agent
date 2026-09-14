import os
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain.messages import SystemMessage, ToolMessage
from langgraph.graph import StateGraph, START, END, MessagesState
from .tools import add, multiply, divide, subtract, power, modulus, square_root


load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:12345678@localhost:5432/calculator_db"
)

# 1. Message State
class AgentState(MessagesState):
    llm_calls: int


# 2. Tools
tools = [add, multiply, divide, subtract, power, modulus, square_root]


# 3. Model
model = init_chat_model(
    "gemini-3.6-flash",
    model_provider="google_genai"
)

model_with_tools = model.bind_tools(tools)


tools_by_name = {tool.name: tool for tool in tools}


# 4. LLM Node
def llm_call(state: AgentState):
    """LLM decides whether to call a tool or not"""

    system_message = SystemMessage(
        content="""You are a calculator assistant.

Rules:
1. Always use the appropriate calculator tool for arithmetic.
2. Never perform arithmetic calculations yourself.
3. Explain the result clearly.
4. If the user asks something unrelated to arithmetic, politely say 
that you only handle calculations.
"""
    )

    response = model_with_tools.invoke([system_message] + state["messages"])    # type: ignore

    return {
        "messages": [response],
        "llm_calls": state.get("llm_calls", 0) + 1
    }


# 5. Tool Node
def tool_node(state: AgentState):
    """Performs the tool calls"""

    result = []
    last_message = state["messages"][-1]
    tool_calls = getattr(last_message, "tool_calls", []) or []

    for tool_call in tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]

        tool = tools_by_name[tool_name]
        observation = tool.invoke(tool_args)
        result.append(ToolMessage(content=observation, tool_call_id=tool_call["id"]))

    return {"messages": result}


# 6. Router
def should_continue(state: AgentState) -> str:
    """Decide if we should continue the loop or stop based upon whether the LLM made a tool call"""

    last_message = state["messages"][-1]

    # If the LLM makes a tool call, then perform an action
    if getattr(last_message, "tool_calls", None):
        return "tool_node"

    # Otherwise, we stop (reply to the user)
    return END


# 7. Build Graph
agent_builder = StateGraph(AgentState)  # type: ignore

agent_builder.add_node("llm_call", llm_call)
agent_builder.add_node("tool_node", tool_node)

agent_builder.add_edge(START, "llm_call")

agent_builder.add_conditional_edges(
    "llm_call",
    should_continue,
    ["tool_node", END]
)

agent_builder.add_edge("tool_node", "llm_call")