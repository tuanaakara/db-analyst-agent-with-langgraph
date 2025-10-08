"""
Graph construction for the AI Analyst agent.

This module is responsible for building the LangGraph state machines
(graphs) that define the agent's control flow. It constructs both the
low-level worker graph and the high-level manager graph.
"""
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

# Import the state schema and the node functions
from .schemas import AnalystState
from . import nodes


def create_worker_graph(agent_instance) -> StateGraph:
    """
    Creates the worker sub-graph, which is a ReAct-style agent.
    This graph is responsible for executing a single task using tools.
    """
    worker_workflow = StateGraph(AnalystState)

    # The worker node is the core of the ReAct agent
    worker_workflow.add_node("agent", nodes.worker_node.__get__(agent_instance))
    
    # The ToolNode executes the tools called by the agent
    worker_workflow.add_node("tools", ToolNode(agent_instance.tool_list))

    # The worker graph starts with the agent node
    worker_workflow.set_entry_point("agent")

    # Define the conditional logic for the worker graph
    def should_continue(state: AnalystState) -> str:
        """
        Determines the next step for the worker agent.
        - If the agent called a tool, go to the 'tools' node.
        - Otherwise, the cycle is finished, so end.
        """
        messages = state['messages']
        last_message = messages[-1]
        if last_message.tool_calls:
            return "tools"
        return END

    # Add the conditional edges
    worker_workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            END: END
        }
    )

    # After tools are executed, the result is sent back to the agent
    worker_workflow.add_edge('tools', 'agent')
    
    return worker_workflow.compile()


def create_manager_graph(agent_instance) -> StateGraph:
    """
    Creates the high-level manager graph.
    This graph orchestrates the overall analysis process by calling the nodes
    in a sequence: planner -> executor -> synthesizer.
    """
    manager_workflow = StateGraph(AnalystState)

    # Add the nodes to the manager graph, binding them to the agent instance
    # `.__get__(agent_instance)` is used to correctly bind the `self` parameter
    manager_workflow.add_node("planner", nodes.planner_node.__get__(agent_instance))
    manager_workflow.add_node("executor", nodes.execution_node.__get__(agent_instance))
    manager_workflow.add_node("synthesizer", nodes.synthesizer_node.__get__(agent_instance))

    # Define the execution flow
    manager_workflow.set_entry_point("planner")
    manager_workflow.add_edge("planner", "executor")
    manager_workflow.add_edge("executor", "synthesizer")
    manager_workflow.add_edge("synthesizer", END)

    return manager_workflow.compile()
