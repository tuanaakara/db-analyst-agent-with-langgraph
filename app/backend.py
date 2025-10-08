"""
Main entry point for the AI Analyst Backend Service using FastAPI.

This module sets up the FastAPI application, initializes the AI Analyst agent,
and defines the API endpoints for receiving analysis requests.
"""
import logging
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager

# Import our application-specific modules
from db_analyst.agent import AIAnalyst
from db_analyst.llm_service import GeminiService
from db_analyst.schemas import AnalyzeRequest, StreamUpdate

# --- Logging Configuration ---
# Set up basic logging to see INFO level messages in the console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Application State ---
# This dictionary will hold our "singleton" instances, like the agent
# The agent is heavy and should only be initialized once.
app_state = {}

# --- FastAPI Lifespan Events ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the application's lifespan. Code before `yield` runs on startup,
    code after `yield` runs on shutdown.
    """
    logger.info("Uygulama başlatılıyor...")
    logger.info("AI Analyst agent'ı hazırlanıyor...")
    
    # This is where Dependency Injection happens!
    # 1. Create the dependencies
    llm_service = GeminiService()
    
    # 2. Inject the dependency into our main class
    analyst_agent = AIAnalyst(llm_service==llm_service)

    # 3. Store the initialized agent in our application state
    app_state["agent"] = analyst_agent
    
    logger.info("✅ AI Analyst agent'ı başarıyla başlatıldı ve hazır.")
    yield
    # --- Cleanup on shutdown (if needed) ---
    logger.info("Uygulama kapatılıyor.")
    app_state.clear()

# --- FastAPI Application Instance ---
app = FastAPI(
    title="DB Analyst Agent Backend",
    description="Handles data analysis requests from the frontend.",
    version="1.0.0",
    lifespan=lifespan  # Connect the lifespan events to the app
)

# --- API Endpoints ---
@app.get("/")
def read_root():
    """A simple health check endpoint to confirm the server is running."""
    return {"message": "DB Analyst Backend is running."}


@app.post("/analyze")
async def analyze_query(request: AnalyzeRequest):
    """
    Receives a user query, processes it with the AI Analyst,
    and streams the results back.
    """
    logger.info("Yeni analiz isteği alındı: '%s'", request.user_query)
    agent = app_state.get("agent")
    
    if not agent:
        logger.error("Agent başlatılmamış! Uygulama başlangıcında bir hata oluşmuş olabilir.")
        raise HTTPException(status_code=500, detail="Agent is not available.")

    async def stream_generator():
        """A generator function that yields analysis updates."""
        try:
            # Call the agent's main streaming method
            for update in agent.analyze_streaming(request.user_query):
                # Wrap the update in our Pydantic schema and convert to JSON
                yield StreamUpdate(**update).model_dump_json() + "\n"
        except Exception as e:
            logger.error("Analiz akışı sırasında kritik bir hata oluştu: %s", e, exc_info=True)
            # Yield a final error message to the client
            error_update = StreamUpdate(
                type="error",
                content=f"Backend'de bir hata oluştu: {e}"
            )
            yield error_update.model_dump_json() + "\n"

    # Use FastAPI's StreamingResponse to send the generator's output
    return StreamingResponse(stream_generator(), media_type="application/x-ndjson")

# --- Direct Execution (for local testing without Docker) ---
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
