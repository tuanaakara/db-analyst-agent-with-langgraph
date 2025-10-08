"""
Gradio Frontend for the DB Analyst Agent.

This module creates the user interface for the application. It does not contain
any core agent logic. Instead, it communicates with a separate FastAPI backend
service to perform analyses and stream results back to the user.
"""
import os
import time
import json
import requests
import gradio as gr
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# --- Configuration ---
# The address of the backend service. "http://backend:8000" is used when
# running inside Docker Compose. For local development, it might be
# "http://127.0.0.1:8000".
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")
API_ENDPOINT = f"{BACKEND_URL}/analyze"
ASSISTANT_AVATAR_URL = os.getenv("ASSISTANT_AVATAR_URL", "https://i.imgur.com/B9BJEBv.png")

# --- UI State Management Functions ---
# These functions manage the chat history dictionary and do not interact
# with the backend. They are pure frontend logic.

def generate_chat_title(user_prompt: str) -> str:
    """Generates a short chat title from the user's first prompt."""
    return user_prompt[:45] + "..." if len(user_prompt) > 45 else user_prompt

def start_new_chat(chat_history: dict):
    """Starts a new chat, updates the state, and resets the UI."""
    chat_id = f"chat_{int(time.time())}"
    chat_history[chat_id] = {
        "title": "New Analysis...",
        "messages": []
    }
    initial_message = "Hello! I am your Analysis Assistant. What would you like to know about your database?"
    return (
        chat_history,
        chat_id,
        [(None, initial_message)],
        gr.Radio(choices=[(v["title"], k) for k, v in reversed(list(chat_history.items()))], value=chat_id, label="Chat History"),
        "",
        gr.update(visible=False)
    )

def set_active_chat(chat_id: str, chat_history: dict):
    """Activates the selected chat and updates the UI."""
    if not chat_id or chat_id not in chat_history:
        return None, "", gr.update(visible=False)
    
    messages = chat_history[chat_id]["messages"]
    if not messages:
        messages = [(None, "Hello! I am your Analysis Assistant. What would you like to know about your database?")]
    
    chat_title = chat_history[chat_id]["title"]
    return messages, chat_title, gr.update(visible=True)

def delete_chat(chat_id: str, chat_history: dict):
    """Deletes the selected chat and switches to the most recent one."""
    if chat_id in chat_history:
        del chat_history[chat_id]

    if not chat_history:
        return {}, None, [], gr.Radio(choices=[], label="Chat History"), "", gr.update(visible=False)

    new_active_id = list(chat_history.keys())[-1]
    new_messages = chat_history[new_active_id]["messages"]
    return (
        chat_history,
        new_active_id,
        new_messages,
        gr.Radio(choices=[(v["title"], k) for k, v in reversed(list(chat_history.items()))], value=new_active_id, label="Chat History")
    )

def rename_chat(chat_id: str, new_title: str, chat_history: dict):
    """Updates the title of the active chat."""
    if chat_id in chat_history and new_title:
        chat_history[chat_id]["title"] = new_title
    
    return chat_history, gr.Radio(choices=[(v["title"], k) for k, v in reversed(list(chat_history.items()))], value=chat_id, label="Chat History")

# --- Backend Communication and Response Handling ---

def format_stream_update(update: dict, plan_steps: list) -> str:
    """Formats a JSON update from the backend into a Markdown string."""
    update_type = update.get("type")
    content = update.get("content")
    
    if update_type == "plan":
        plan_steps.clear()
        plan_steps.extend(content)
        if len(plan_steps) > 1:
            plan_md = "\n".join([f"**{i+1}.** {step}" for i, step in enumerate(plan_steps)])
            return f"### 🤔 Analysis Plan\n{plan_md}\n\n---\n"
    
    elif update_type == "step_start":
        step_index = update.get("step", 0)
        return f"#### 🚀 Step {step_index + 1}/{len(plan_steps)}: {content}\n"

    elif update_type == "sql_query":
        return f"**🔍 Generated SQL Query:**\n```sql\n{content}\n```\n"

    elif update_type == "tool_result":
        return f"**📊 Result:** {content}\n\n"

    elif update_type == "tool_error":
        return f"<p style='color: #ff4b4b;'><strong>⚠️ Tool Error:</strong> {content}</p>\n\n"
    
    elif update_type == "error":
        return f"<p style='color: #ff4b4b;'><strong>❌ System Error:</strong> {content}</p>\n\n"
   
    elif update_type == "info":
        return f"ℹ️ *{content}*\n"
    
    elif update_type == "final_result":
        return f"---\n### ✅ Analysis Result\n{content}"
        
    return ""

def user_submit_fn(user_input, chatbot_messages, active_chat_id, chat_history):
    """
    Handles user submission by sending a request to the backend and streaming the response.
    """
    # 1. Update UI immediately with user's message
    chat_history[active_chat_id]["messages"].append((user_input, None))
    chatbot_messages.append((user_input, None))
    yield chatbot_messages, chat_history, ""

    # 2. Handle first message to set chat title
    is_first_message = chat_history[active_chat_id]["title"] == "New Analysis..."
    if is_first_message:
        title = generate_chat_title(user_input)
        chat_history[active_chat_id]["title"] = title
    
    # 3. Prepare for streaming response
    bot_response_full = ""
    chatbot_messages.append((None, "")) # Add a placeholder for the bot's response

    try:
        # 4. Send request to the backend
        payload = {"user_query": user_input}
        response = requests.post(API_ENDPOINT, json=payload, stream=True)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

        plan_steps_for_formatting = []
        
        # 5. Process the streaming response
        for chunk in response.iter_lines():
            if chunk:
                update_data = json.loads(chunk.decode('utf-8'))
                formatted_update = format_stream_update(update_data, plan_steps_for_formatting)
                
                if formatted_update:
                    bot_response_full += formatted_update
                    chatbot_messages[-1] = (None, bot_response_full)
                    yield chatbot_messages, chat_history, gr.update()
    
    except requests.exceptions.RequestException as e:
        error_message = f"❌ **Connection Error:** Could not connect to the backend service at `{BACKEND_URL}`. Please ensure the backend is running. \n\n**Details:**\n`{str(e)}`"
        chatbot_messages[-1] = (None, error_message)
    except Exception as e:
        error_message = f"❌ **An unexpected error occurred:** {str(e)}"
        chatbot_messages[-1] = (None, error_message)

    # 6. Save the final complete response to the history
    if bot_response_full:
        chat_history[active_chat_id]["messages"][-1] = (None, bot_response_full)

    # 7. Update the chat list to show the new title if it was the first message
    if is_first_message:
        yield chatbot_messages, chat_history, gr.Radio(choices=[(v["title"], k) for k, v in reversed(list(chat_history.items()))], value=active_chat_id, label="Chat History")
    else:
        yield chatbot_messages, chat_history, gr.update()


# --- Gradio UI Definition ---

with gr.Blocks(theme=gr.themes.Soft(primary_hue="sky"), css="""
    #chatbot { min-height: 600px; }
    #sidebar { min-width: 250px; max-width: 350px; }
""") as demo:
    
    chat_history = gr.State({})
    active_chat_id = gr.State(None)

    gr.Markdown("# 🤖 DB Analyst Agent\nAsk questions about your data in natural language.")
    
    with gr.Row(equal_height=False):
        with gr.Column(scale=1, elem_id="sidebar"):
            new_chat_btn = gr.Button("＋ New Chat", variant="primary")
            chat_history_display = gr.Radio(label="Chat History", choices=[], interactive=True, container=False)
            with gr.Group(visible=False) as manage_chat_group:
                rename_input = gr.Textbox(label="Rename Chat", placeholder="Enter new title...")
                with gr.Row():
                    rename_btn = gr.Button("Save")
                    delete_btn = gr.Button("Delete Chat", variant="stop")

        with gr.Column(scale=4):
            chatbot = gr.Chatbot(
                [], 
                elem_id="chatbot", 
                bubble_full_width=False, 
                avatar_images=(None, ASSISTANT_AVATAR_URL),
                render_markdown=True,
                show_label=False
            )
            user_input = gr.Textbox(placeholder="Type your question here...", show_label=False, scale=4)

    # --- Event Handlers ---
    
    def on_load(chat_history_state):
        if not chat_history_state:
            return start_new_chat({})
        
        active_id = list(chat_history_state.keys())[-1]
        active_chat = chat_history_state[active_id]
        
        return (
            chat_history_state, 
            active_id, 
            active_chat['messages'], 
            gr.Radio(choices=[(v["title"], k) for k, v in reversed(list(chat_history_state.items()))], value=active_id, label="Chat History"), 
            active_chat['title'], 
            True
        )

    demo.load(
        fn=on_load,
        inputs=[chat_history],
        outputs=[chat_history, active_chat_id, chatbot, chat_history_display, rename_input, manage_chat_group]
    )

    user_input.submit(
        fn=user_submit_fn,
        inputs=[user_input, chatbot, active_chat_id, chat_history],
        outputs=[chatbot, chat_history, chat_history_display]
    ).then(lambda: "", inputs=None, outputs=[user_input])

    new_chat_btn.click(
        fn=start_new_chat,
        inputs=[chat_history],
        outputs=[chat_history, active_chat_id, chatbot, chat_history_display, rename_input, manage_chat_group]
    )

    chat_history_display.select(
        fn=set_active_chat,
        inputs=[chat_history_display, chat_history],
        outputs=[chatbot, rename_input, manage_chat_group]
    ).then(lambda chat_id: chat_id, inputs=[chat_history_display], outputs=[active_chat_id])

    delete_btn.click(
        fn=delete_chat,
        inputs=[active_chat_id, chat_history],
        outputs=[chat_history, active_chat_id, chatbot, chat_history_display]
    )

    rename_btn.click(
        fn=rename_chat,
        inputs=[active_chat_id, rename_input, chat_history],
        outputs=[chat_history, chat_history_display]
    )

if __name__ == "__main__":
    # Check if backend is available on startup
    try:
        # A simple GET request to the root of the backend to check for a connection.
        response = requests.get(f"{BACKEND_URL}/")
        response.raise_for_status()
        print("✅ Backend service is available.")
    except requests.exceptions.RequestException as e:
        print("---------------------------------------------------------------")
        print(f"❌ CRITICAL: Could not connect to backend service at {BACKEND_URL}")
        print("Please ensure the backend container is running and accessible.")
        print(f"Error details: {e}")
        print("---------------------------------------------------------------")

    # Launch the Gradio app
    demo.launch(server_name="0.0.0.0", server_port=7860)