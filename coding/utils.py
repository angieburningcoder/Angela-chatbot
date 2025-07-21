import streamlit as st
from typing import List, Dict, Any, Optional
import json
import os
from datetime import datetime

def paging():
    st.page_link("streamlit_app.py", label="Home", icon="🏠")
    st.page_link("pages/one_agent.py", label="Teacher Agents' Talk", icon="👩‍💼")
    st.page_link("pages/two_agents.py", label="Two Agents' Talk", icon="🧑‍🤝‍🧑")
    st.page_link("pages/group_agents.py", label="Group Agents' Talk", icon="💭")

def custom_navigation():
    """Custom navigation that works with any entry point"""
    st.markdown("### 🧭 Navigation")
    
    # Get the current script path to determine navigation
    import sys
    current_script = sys.argv[0] if len(sys.argv) > 0 else ""
    
    # Determine if we're in pages directory
    is_in_pages = "pages/" in current_script or "pages\\" in current_script
    
    if st.button("🏠 Home", key="nav_home"):
        if is_in_pages:
            st.switch_page("../streamlit_app_one_agent_fixed.py")
        else:
            st.switch_page("streamlit_app_one_agent_fixed.py")
    
    if st.button("👩‍💼 Teacher Agents' Talk", key="nav_one_agent"):
        if is_in_pages:
            st.switch_page("one_agent.py")
        else:
            st.switch_page("pages/one_agent.py")
    
    if st.button("🧑‍🤝‍🧑 Two Agents' Talk", key="nav_two_agents"):
        if is_in_pages:
            st.switch_page("two_agents.py")
        else:
            st.switch_page("pages/two_agents.py")
    
    if st.button("💭 Group Agents' Talk", key="nav_group_agents"):
        if is_in_pages:
            st.switch_page("group_agents.py")
        else:
            st.switch_page("pages/group_agents.py")
    
    st.markdown("---")

def display_session_msg(container_obj, user_image: Optional[str] = None):
    # Initialize messages list if not present
    messages = st.session_state.setdefault("messages", [])

    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        avatar = None

        # Determine avatar to use
        if role == "assistant":
            avatar = user_image
        elif role not in ["user", "assistant"]:
            avatar = msg.get("image", None)

        # Display message
        if avatar:
            container_obj.chat_message(role, avatar=avatar).markdown(content)
        else:
            container_obj.chat_message("ai").markdown(content)

def show_chat_history(container_obj, chat_history: List[Dict[str, Any]], user_image=None) -> str:
    """
    Processes a list of chat history entries by:
      1. Skipping any entries whose role is 'tool'
      2. Skipping entries with null or empty content
      3. Stripping out the "ALL DONE" token
    Displays each valid message via Streamlit and returns the processed messages
    as a JSON-formatted string.
    """
    if 'messages' not in st.session_state:
        st.session_state.messages = []

    processed = []

    for entry in chat_history:
        if entry.get('role') == 'tool':
            continue

        content = entry.get('content')

        if content is None:
            continue
        if isinstance(content, str):
            content = content.replace("##ALL DONE##", "")
            content = content.replace("ALL DONE", "")
            if not content.strip():
                continue
        else:

            continue

        # role = entry.get('role', 'user')
        # message = {"role": role, "content": content}
        # processed.append(message)

        # Append to session history
        # st.session_state.messages.append(message)

        # Display according to role
        # if role == 'assistant':
        #     container_obj.chat_message("assistant", avatar=user_image).write(content)
        # else:
        #     container_obj.chat_message("ai").write(content)

    # Return the processed messages as a JSON string
    return json.dumps(processed, ensure_ascii=False, indent=2)

def save_messages_to_json(
    messages: List[Dict[str, Any]],
    output_dir: str = "."
) -> str:
    """
    Save a list of chat messages (each a dict with 'role' and 'content')
    to a JSON file named with the current timestamp in "YYYY-MM-DD HH-MM.json" format.

    Args:
        messages: The processed messages to save.
        output_dir: Directory where the file will be saved. Defaults to current directory.

    Returns:
        The full path of the JSON file that was written.
    """
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Generate filename based on current local time
    timestamp = datetime.now().strftime("%Y-%m-%d %H-%M")
    filename = f"{timestamp}.json"
    filepath = os.path.join(output_dir, filename)

    # Write messages to the file
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)

    return filepath
