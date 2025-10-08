"""
Node functions for the AI Analyst LangGraph workflow.

Each function in this module represents a node in the state graph, defining a
specific part of the agent's logic, such as planning, execution, or synthesis.
"""
import json
import re
import logging
from typing import Dict, Any
from . import config
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

# Import schemas and prompts from our new modules
from .schemas import AnalystState
from . import prompts

logger = logging.getLogger(__name__)


def planner_node(self, state: AnalystState) -> Dict[str, Any]:
    """
    Analyzes the user query and creates a step-by-step plan.
    This node is the entry point for the manager graph.
    """
    logger.info("--- Executing Planner Node ---")
    
    prompt = prompts.PLANNER_PROMPT_TEMPLATE.format(
        user_query=state['user_query'],
        db_schema=state['db_schema']
    )
    try:
            logger.info("Sorgu planlaması için LLM Servisine istek gönderiliyor: '{user_query}'")
            response_text = self.llm_service.get_response(prompt)
            logger.debug("LLM Servisinden plan yanıtı alındı:\n%s", response_text)            
            # Safely extract JSON from the LLM's response
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response_text, re.DOTALL)
            if match:
                json_str = match.group(1)
            else:
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    raise json.JSONDecodeError("Yanıt içinde JSON nesnesi bulunamadı.", response_text, 0)
            
            logger.debug("Planner için Ayıklanan JSON: %s", json_str)
            plan_data = json.loads(json_str)
            plan = plan_data.get("plan", [])

            if not plan:
                raise ValueError("Oluşturulan planda adım bulunmuyor.")

            logger.info("📄 Plan %d adımla oluşturuldu: ",len(plan))
            
            for i, step in enumerate(plan, 1):
                logger.info("   %d. %s", i, step)

            return {"plan": plan}
        
    except Exception as e:

            # Log the full error with traceback for debugging purposes
            logger.error("❌ Planner Node'da Error: %s", e, exc_info=True)

            # In case of failure, create a simple fallback plan to continue the process
            logger.warning("Bir hata nedeniyle tek adımlı plana geçiliyor.")

            fallback_plan = [f"Kullanıcının sorusunu yanıtlamak için doğrudan bir SQL sorgusu oluştur: '{state['user_query']}'"]
            # The node's only job is to return a plan. The execution_node will handle logging for the UI.
            return {"plan": fallback_plan}


def execution_node(self, state: AnalystState) -> Dict[str, Any]:
    """
    Executes each step of the plan by invoking the worker sub-graph.
    It accumulates data and logs the process for streaming.
    """
    logger.info("--- Executing Execution Node ---")
    plan = state.get("plan", [])
    executed_steps = {}
    accumulated_data = {}
    logs = []

    for i, step in enumerate(plan):
        logger.info("  - Executing Step %d/%d: %s", i + 1, len(plan), step)
        logs.append({"type": "step_start", "step": i, "content": step})

        step_success = False
        step_error_history = []
        for attempt in range(config.MAX_RETRIES_PER_STEP):
            logger.info("    - Attempt %d/%d", attempt + 1, config.MAX_RETRIES_PER_STEP)
            
            context_data = f"\nCONTEXT FROM PREVIOUS STEPS (JSON): {json.dumps(accumulated_data)}" if accumulated_data else ""
            error_feedback = f"\nPREVIOUS ATTEMPT's ERROR: {step_error_history[-1]}\nPlease analyze this error, correct your SQL query, and try again." if step_error_history else ""

            # Prepare the prompt for the worker agent using the template
            worker_prompt_content = prompts.STEP_EXECUTION_PROMPT_TEMPLATE.format(
                user_query=state['user_query'],
                db_schema=state['db_schema'],
                context_data=context_data,
                error_feedback=error_feedback,
                step=step
            )

            worker_messages = [HumanMessage(content=worker_prompt_content)]
            worker_graph = self.graph 
            sub_task_config = {"configurable": {"thread_id": f"sub_task_{i}_attempt_{attempt}"}}
            
            try:
                # Stream the sub-graph's execution to capture intermediate tool calls and results
                for sub_update in worker_graph.stream(worker_messages, config=sub_task_config):
                    if "agent" in sub_update:
                        agent_response = sub_update["agent"]["messages"][-1]
                        if agent_response.tool_calls:
                            sql_query = agent_response.tool_calls[0]['args']['sql_query']
                            logs.append({"type": "sql_query", "step": i, "content": sql_query})

                    if "tools" in sub_update:
                        tool_msg = sub_update["tools"]["messages"][-1]
                        result_data = json.loads(tool_msg.content)
                        if result_data.get("success"):
                            data = result_data.get("data", [])
                            logs.append({"type": "tool_result", "step": i, "content": f"Success, {len(data)} rows found."})
                            step_success = True
                            executed_steps[f"step_{i+1}"] = {"description": step, "data": data}
                            accumulated_data[f"step_{i+1}_result"] = data
                        else:
                            error_msg = result_data.get("error", "Unknown tool error.")
                            logs.append({"type": "tool_error", "step": i, "content": error_msg})
                            step_error_history.append(error_msg)
                
                if step_success:
                    break
            
            except Exception as e:
                error_msg = f"Critical error during step execution: {str(e)}"
                logger.error("  - ❌ Critical worker error: %s", e, exc_info=True)
                logs.append({"type": "error", "step": i, "content": error_msg})
                step_error_history.append(error_msg)

        if not step_success:
            logger.warning("  - ⚠️ Step %d failed after all retries. Stopping analysis.", i + 1)
            logs.append({"type": "error", "content": f"Step {i+1} failed. Analysis stopped."})
            break
    
    logs.append({"type": "info", "content": "Synthesizing final results..."})
    return {"executed_steps": executed_steps, "accumulated_data": accumulated_data, "log_messages": logs}

def synthesizer_node(self, state: AnalystState) -> Dict[str, Any]:
    """
    Takes the data collected from all steps and synthesizes a final,
    human-readable answer.
    """
    logger.info("--- Synthesizer Düğümü Çalıştırılıyor ---")
    executed_steps = state.get("executed_steps", {})

    if not executed_steps:
        logger.warning("Synthesizer düğümü hiç tamamlanmış adım olmadan çağrıldı. Bir geri dönüş mesajı döndürülüyor.")
        final_response = "Maalesef sorgunuzla ilgili veri toplanamadı. Lütfen sorunuzu farklı bir şekilde ifade etmeyi deneyin veya backend loglarını kontrol edin."
    else:
        # Format the results in a readable way for the LLM
        # Using English keys for consistency in the prompt template
        formatted_results = json.dumps([
            {"step_description": step_data["description"], "data": step_data["data"]}
            for step_data in executed_steps.values()
        ], indent=2, ensure_ascii=False)

        prompt = prompts.SYNTHESIZER_PROMPT_TEMPLATE.format(
            user_query=state['user_query'],
            formatted_results=formatted_results
        )
        
        logger.info("Toplanan veriler nihai sentez için Gemini'ye gönderiliyor...")
        final_response = self.llm_service.get_response(prompt)

    logger.info("✅ Nihai yanıt sentezlendi.")
    
    # This node's only responsibility is to create the final message.
    # It does not modify the streaming logs.
    return {"messages": [AIMessage(content=final_response)]}

def worker_node(self, state: AnalystState) -> dict:
    """
    The low-level worker node that uses the ReAct pattern. Its only job is to
    analyze the current task and call the appropriate tool.
    """
    messages = state['messages']

    # This is the correct exit condition for the worker loop.
    # If the last message is a ToolMessage, it means the tool has run and its
    # result is in the state. The worker's job for this cycle is done.
    if isinstance(messages[-1], ToolMessage):
        return {"messages": [AIMessage(content="Araç çalıştırıldı, görev tamamlandı.")]}

    # Add a strong system prompt to guide the LLM's behavior
    system_prompt = prompts.REACT_WORKER_PROMPT.format(db_schema=self.db_schema)
    enhanced_messages = [SystemMessage(content=system_prompt)] + messages
    
    try:
        logger.info("   - Worker Düğümü: Araç kullanımı için Gemini'ye istek gönderiliyor...")
        response = self.llm_with_tools.invoke(enhanced_messages)
        
        # Log the response for debugging purposes. Using None is the correct practice.
        tool_calls = response.tool_calls if hasattr(response, 'tool_calls') else None
        logger.debug("   - Worker Düğümü: Gemini yanıtı alındı. Araç Çağrıları: %s", tool_calls)
        
        return {"messages": [response]}
        
    except Exception as e:
        logger.error("  - ❌ Worker Düğümü Hatası: %s", e, exc_info=True)
        # Return the error as a message to allow for self-correction by the agent
        return {"messages": [AIMessage(content=f"Araç çağrılırken hata oluştu: {e}")]}
    
    