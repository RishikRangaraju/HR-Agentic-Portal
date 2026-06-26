# agent_graph.py
import os
import json
from dotenv import load_dotenv
from typing import Annotated, TypedDict, List, Union
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from app.tools import TOOL_MAP
load_dotenv()

# 1. Define the State
class AgentState(TypedDict):
    # add_messages ensures that new messages are appended to the history rather than overwriting it
    messages: Annotated[List, add_messages]

# 2. Setup the LLM (via Portkey)
llm = ChatOpenAI(
    model="@opal/meta-llama/Llama-3.3-70B-Instruct",
    openai_api_key=os.getenv("PORTKEY_API_KEY"),
    openai_api_base=os.getenv("PORTKEY_BASE_URL"),
    default_headers={
        "x-portkey-config": os.getenv("PORTKEY_CONFIG_ID"),
    }
)

# Bind the tools to the LLM (Using your existing JSON schema format)
# Note: LangChain prefers a specific Tool format, but we can bind your JSON tools
from agent import TOOLS # Import your existing TOOLS list from agent.py
llm_with_tools = llm.bind_tools(TOOLS)

def call_model(state: AgentState):
    """The LLM decides what to do next."""
    system_prompt = (
        "You are a precise and professional HR Assistant. "
        "Use tools to manage records. Before updating, you MUST call fetch_employee. "
        "If a tool requires missing info, ask the user. "
        "Do not explain your internal reasoning. Provide natural responses."
    )
    
    messages = state['messages']
    
    # Correct way to check for system message in LangGraph/LangChain
    has_system_message = any(
        (hasattr(m, 'type') and m.type == 'system') or 
        (isinstance(m, dict) and m.get("role") == "system") 
        for m in messages
    )
    
    if not has_system_message:
        from langchain_core.messages import SystemMessage
        messages = [SystemMessage(content=system_prompt)] + messages
        
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

def execute_tools(state: AgentState):
    """Executes the tool calls decided by the LLM."""
    messages = state['messages']
    last_message = messages[-1]
    
    tool_outputs = []
    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        args = tool_call["args"]
        
        print(f"Executing tool: {tool_name} with args: {args}")
        
        func = TOOL_MAP.get(tool_name)
        if func:
            try:
                # Call function with unpacked arguments
                result = func(**args) if args else func()
            except Exception as e:
                # CRITICAL: Catch the error and return it as a tool message
                # This allows the LLM to see the error and try to fix it
                print(f"Tool Error: {str(e)}")
                result = {"error": f"Tool execution failed: {str(e)}"}
        else:
            result = {"error": f"Tool {tool_name} not found."}
            
        from langchain_core.messages import ToolMessage
        tool_outputs.append(ToolMessage(
            content=json.dumps(result),
            tool_call_id=tool_call["id"]
        ))
    
    return {"messages": tool_outputs}

# 4. Define the Routing Logic
def should_continue(state: AgentState):
    """Determines if the agent should call a tool or finish."""
    last_message = state['messages'][-1]
    if last_message.tool_calls:
        return "tools"
    return END

# 5. Construct the Graph
workflow = StateGraph(AgentState)

workflow.add_node("agent", call_model)
workflow.add_node("tools", execute_tools)

workflow.set_entry_point("agent")

# Edge from agent -> tools (if tool_calls present) or END (if answer reached)
workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "tools": "tools",
        END: END
    }
)

# Edge from tools -> back to agent to process the result
workflow.add_edge("tools", "agent")

# Compile the graph
app_graph = workflow.compile()