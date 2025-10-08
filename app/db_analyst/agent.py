"""
The core AI Analyst agent class.

This module defines the AIAnalyst class, which orchestrates the entire analysis
process by managing the LangGraph state machine, services, and tools.
"""
import logging
from datetime import datetime
from langgraph.checkpoint.memory import MemorySaver

# Import from our refactored modules
from . import config
from .llm_service import GeminiService
from .schemas import AnalystState
from .exceptions import InitializationError, DatabaseConnectionError
from .tools import get_database_schema, execute_sql
from .graph import create_worker_graph, create_manager_graph
# We will create this file in the next step
# from .graph import create_worker_graph, create_manager_graph

logger = logging.getLogger(__name__)


class AIAnalyst:
    """
    The main class for the DB Analyst Agent.
    It initializes all components and runs the analysis stream.
    """

    def __init__(self, llm_service: GeminiService):
        """
        Initializes the AIAnalyst agent.

        Args:
            llm_service (GeminiService): An instance of the Gemini service.
        """
        logger.info("Initializing AIAnalyst...")
        if not llm_service:
            raise InitializationError("A GeminiService instance must be provided.")
        
        self.llm_service = llm_service
        self.db_path = config.DB_PATH
        self.db_schema = None
        self.tool_list = [execute_sql]
        self.llm_with_tools = None
        self.graph = None # This will hold the worker graph
        self.main_graph = None # This will hold the manager graph
        self.memory = MemorySaver()

        # Call the private initializer to set up components
        self._initialize()
        logger.info("✅ AIAnalyst başarıyla başlatıldı.")

    def _initialize(self):
        """
        Private initializer to set up database schema, tools, and graphs.
        This method delegates complex tasks to other modules.

        """
        logger.info("Veritabanı şeması yükleniyor...")
        # Note: In a real app, db_path would come from a config file
        self.db_schema = get_database_schema(self.db_path)
        if not self.db_schema or self.db_schema.startswith("Error:"):
            raise DatabaseConnectionError(f"Veritabanı şeması okunamadı: {self.db_path}")
        logger.info("Şema başarıyla yüklendi.")

        logger.info("Araçlar LLM'e bağlanıyor...")
        raw_llm = self.gemini_service.get_llm_instance()
        self.llm_with_tools = raw_llm.bind_tools(self.tool_list)
        logger.info("Araçlar başarıyla bağlandı.")
        
        logger.info("LangGraph iş akışları (workflow) oluşturuluyor...")
        self.graph = create_worker_graph(self)
        self.main_graph = create_manager_graph(self)
        logger.info("✅ İş akışları başarıyla oluşturuldu.")

    def analyze_streaming(self, user_query: str):
        """
        Receives a user query and streams the analysis process live.
        This is the main entry point for the agent's functionality.

        Args:
            user_query (str): The user's question in natural language.
        
        Yields:
            dict: A dictionary representing a single update from the analysis stream.
        """
        if not user_query.strip():
            logger.warning("Empty user query received.")
            yield {"type": "error", "content": "Soru boş olamaz."}
            return

        initial_state = {
            "messages": [],
            "user_query": user_query,
            "db_schema": self.db_schema,
            "log_messages": []
        }

        thread_id = f"main_analysis_stream_{datetime.now().timestamp()}"
        config = {"configurable": {"thread_id": thread_id}}
        
        logger.info("Yeni analiz akışı başlatılıyor. Thread ID: %s", thread_id)
        
        if not self.main_graph:
            logger.error("Ana grafik başlatılmamış. Analiz başlatılamıyor.")
            yield {"type": "error", "content": "Agent'in ana grafiği başlatılmamış. Analiz başlatılamıyor."}
            return

        sent_logs_tracker = set()
        last_log_count = 0

        try:
            for update in self.main_graph.stream(initial_state, config=config):
                
                if "planner" in update:
                    plan = update["planner"].get("plan", [])
                    if plan:
                        plan_tuple = ("plan", tuple(plan))
                        if plan_tuple not in sent_logs_tracker:
                            yield {"type": "plan", "content": plan}
                            sent_logs_tracker.add(plan_tuple)

                if "executor" in update:
                    all_logs = update["executor"].get("log_messages", [])
                    new_logs = all_logs[last_log_count:]
                    last_log_count = len(all_logs)
                
                    for log_entry in new_logs:
                        log_tuple = (
                            log_entry.get("type"),
                            log_entry.get("step"),
                            log_entry.get("content")
                        )
                        if log_tuple not in sent_logs_tracker:
                            yield log_entry
                            sent_logs_tracker.add(log_tuple)

                if "synthesizer" in update:
                    messages = update["synthesizer"].get("messages", [])
                    if messages:
                        final_content = messages[-1].content
                        final_tuple = ("final_result", final_content)
                        if final_tuple not in sent_logs_tracker:
                            yield {"type": "final_result", "content": final_content}
                            sent_logs_tracker.add(final_tuple)

        except Exception as e:
            logger.error("Analiz akışı sırasında kritik bir hata oluştu: %s", e, exc_info=True)
            yield {"type": "error", "content": f"Analiz akışı sırasında kritik bir hata oluştu: {str(e)}"}
