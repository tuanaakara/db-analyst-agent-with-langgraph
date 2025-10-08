import sqlparse
import re
from langchain_core.tools import tool
from pydantic.v1 import BaseModel, Field
from typing import List, Dict, Any, Optional
from utils import get_db_connection
import logging
import config
import pandas as pd

logger = logging.getLogger(__name__)

class SQLToolOutput(BaseModel):
    """A structured model for the output of the execute_sql tool."""
    success: bool
    data: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None

# Tool argument schemas
class SingleQueryArgs(BaseModel):
    sql_query: str = Field(description="The SQL query to be processed.")

class ValidateDataArgs(BaseModel):
    query_result: dict = Field(description="The data returned after executing SQL to be validated.")


# JOIN relations
JOIN_RELATIONS = {
    "message_into": [
        "message_into.chat_session_id → chat_session.chat_session_id",
        "message_into.user_id → user.user_id"
    ],
    "user": [
        "user.unit_id → unit.unit_id"
    ],
    "use_llm_service": [
        "use_llm_service.chat_session_id → chat_session.chat_session_id",
        "use_llm_service.llm_id → llm_providers.llm_id"
    ]
}

# Table descriptions / purposes
TABLE_PURPOSES = {
    "unit": "Defines organizational units",
    "user": "Contains user information",
    "message_into": "Represents each individual message",
    "llm_providers": "Lists available LLM models",
    "use_llm_service": "Shows which LLM is used in which session",
    "chat_session" : "Represents each chat session. To find users participating in a session, join this table with the 'message_into' table. The 'num_of_mess' column contains the TOTAL NUMBER OF MESSAGES in that session. Use SUM(num_of_mess) to measure overall usage intensity.",
}

def get_database_schema(db_path: str) -> str:
    """
    Enriches the schema with contextual information
    """
    #provides a detailed "map" for the artificial intelligence (LLM) to understand the database.
    schema_parts = []
 
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            for table_name in tables:
                table_name = table_name[0]
                
                # CREATE TABLE
                cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}';")
                create_sql = cursor.fetchone()[0]
                
                # Record count
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                
                # First few records (data samples)
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
                columns = [desc[0] for desc in cursor.description]
                sample_data = cursor.fetchall()

                # Table description
                if table_name in TABLE_PURPOSES:
                    schema_parts.append(f"-- PURPOSE: {TABLE_PURPOSES[table_name]}")

                # JOIN relations
                if table_name in JOIN_RELATIONS:
                    schema_parts.append("-- JOIN RELATIONS:")
                    for relation in JOIN_RELATIONS[table_name]:
                        schema_parts.append(f"-- {relation}")

                # Enriched schema
                schema_parts.append(f"""
-- TABLE: {table_name} ({count} records)
{create_sql};

-- SAMPLE DATA:
-- Columns: {', '.join(columns)}""")
                
                for i, row in enumerate(sample_data, 1):
                    row_str = ', '.join([str(val) if val is not None else 'NULL' for val in row])
                    schema_parts.append(f"-- Sample {i}: {row_str}")
                
                # Table-specific notes
                if table_name == 'chat_session':
                    schema_parts.append("-- PURPOSE: Record for each chat session (num_of_mess = total number of messages in that session)")
                    schema_parts.append("-- IMPORTANT: Use SUM(num_of_mess) to calculate the total number of messages!")
                elif table_name == 'use_llm_service':
                    schema_parts.append("-- PURPOSE: Shows which LLM is used in which session")
                    schema_parts.append("-- IMPORTANT: To find the actual usage of the LLM model, join this table with the chat_session table and use SUM(chat_session.num_of_mess).")
                elif table_name == 'message_into':
                    schema_parts.append("-- PURPOSE: Record for each individual message")  
                    schema_parts.append("-- FOR MESSAGE COUNT: Use COUNT(*) from this table or SUM(num_of_mess) from chat_session")

                schema_parts.append("") 
                
    except Exception as e:
        return f"Error: Could not read schema - {e}"
    
    return "\n".join(schema_parts)

# LANGCHAIN tools (@tool) 

@tool(args_schema=SingleQueryArgs)
def execute_sql(sql_query: str) -> SQLToolOutput:
    """
    First validates an SQL query for security and syntax, then executes it.
    Only SELECT queries are allowed.
    """
    logger.debug("Gelen SQL sorgusu: %s", sql_query)
    
    # --- Security & Syntax Check ---
    if not sql_query:
        return SQLToolOutput(success=False, error="Hata: SQL sorgusu boş.")
    
    pattern = r"\b(drop|delete|update|insert|alter|create|truncate|replace)\b"
    if re.search(pattern, sql_query, flags=re.IGNORECASE):
        error_msg = "Güvenlik ihlali. Sadece SELECT sorgularına izin verilir."
        logger.warning("Engellenen sorgu (Güvenlik): %s", sql_query)
        return SQLToolOutput(success=False, error=error_msg)
        
    try:
        parsed = sqlparse.parse(sql_query)
        if not parsed or parsed[0].get_type() != 'SELECT':
            error_msg = f"Hata: Sadece SELECT sorgularına izin verilir, '{parsed[0].get_type()}' tespit edildi."
            logger.warning("Engellenen sorgu (Tip): %s", sql_query)
            return SQLToolOutput(success=False, error=error_msg)
    except Exception as e:
        error_msg = f"Hata: SQL ayrıştırılamadı - {str(e)}"
        logger.warning("Ayrıştırılamayan sorgu: %s", sql_query)
        return SQLToolOutput(success=False, error=error_msg)
    
    logger.info("✅ Güvenlik ve sözdizimi kontrolü geçti.")

    # --- Execute Query ---
    try:
        # DB path is now read from the central config file
        with get_db_connection(config.DB_PATH) as conn:
            df = pd.read_sql_query(sql_query, conn)
        logger.info("✅ Sorgu başarıyla çalıştırıldı, %d sonuç bulundu.", len(df))
        return SQLToolOutput(success=True, data=df.to_dict(orient="records"))
    except Exception as e:
        logger.error("❌ Sorgu çalıştırılırken hata: %s", e, exc_info=True)
        return SQLToolOutput(success=False, error=str(e))
