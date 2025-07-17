import streamlit as st
import time
import os
from dotenv import load_dotenv
from autogen import ConversableAgent, LLMConfig
from autogen.code_utils import content_str

load_dotenv(override=True)

LANG_OPTIONS = ["English", "繁體中文"]
MODEL_OPTIONS = ["gpt-4o-mini (OpenAI)", "gemini-2.0-flash-lite (Google)"]

TRANSLATIONS = {
    "繁體中文": {
        "saved_topics": "已存記錄主題",
        "new_topic": "新增主題名稱",
        "add_topic": "新增主題",
        "edit_topic": "編輯新主題名稱",
        "confirm_rename": "確認修改",
        "delete_only_one": "無法刪除唯一主題",
        "topic_exists": "主題名稱已存在",
        "invalid_name": "主題名稱無效或已存在"
    },
    "English": {
        "saved_topics": "Saved Topics",
        "new_topic": "New Topic Name",
        "add_topic": "Add Topic",
        "edit_topic": "Edit Topic Name",
        "confirm_rename": "Confirm Rename",
        "delete_only_one": "Cannot delete the only topic",
        "topic_exists": "Topic already exists",
        "invalid_name": "Invalid or duplicated topic name"
    }
}

user_name = "Angela"
user_image = "https://www.w3schools.com/howto/img_avatar.png"

API_KEYS = {
    "openai": os.getenv("OPENAI_API_KEY"),
    "google": os.getenv("GEMINI_API_KEY")
}

LLM_CONFIG_MAP = {
    "gpt-4o-mini (OpenAI)": LLMConfig(api_type="openai", model="gpt-4o-mini", api_key=API_KEYS["openai"]),
    "gemini-2.0-flash-lite (Google)": LLMConfig(api_type="google", model="gemini-2.0-flash-lite", api_key=API_KEYS["google"])
}

def stream_data(text):
    for word in text.split():
        yield word + " "
        time.sleep(0.15)

def init_session_state():
    defaults = {
        "lang_setting": "繁體中文",
        "model_setting": MODEL_OPTIONS[0],
        "user_name": user_name,
        "current_profile": "KA助理",
        "profile_list": ["KA助理", "職涯顧問", "日常聊天"]
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)
    for p in st.session_state["profile_list"]:
        st.session_state.setdefault(f"messages_{p}", [])
        st.session_state.setdefault(f"student_agent_{p}", None)
        st.session_state.setdefault(f"teacher_agent_{p}", None)

def init_agents(profile, lang, model):
    if st.session_state[f"student_agent_{profile}"]:
        return
    llm_config = LLM_CONFIG_MAP[model]
    student = ConversableAgent(
        name="Student_Agent",
        system_message=f"You are a student willing to learn. After your result, say 'ALL DONE'. Please output in {lang}",
        llm_config=llm_config
    )
    teacher = ConversableAgent(
        name="Teacher_Agent",
        system_message=f"You are a teacher. Please answer student's question. Please output in {lang}",
        llm_config=llm_config,
        is_termination_msg=lambda x: content_str(x.get("content", "")).find("ALL DONE") >= 0,
        human_input_mode="NEVER"
    )
    st.session_state[f"student_agent_{profile}"] = student
    st.session_state[f"teacher_agent_{profile}"] = teacher

def render_message(msg, container, avatar=None):
    role = msg.get("role", "user")
    avatar = avatar if role == "user" else msg.get("image", None)
    container.chat_message(role, avatar=avatar).markdown(msg.get("content", ""))

def update_language():
    st.session_state["lang_setting"] = st.session_state["selected_lang"]

def update_model():
    st.session_state["model_setting"] = st.session_state["selected_model"]

def add_new_profile():
    new = st.session_state["new_profile_input"].strip()
    if not new or new in st.session_state["profile_list"]:
        st.warning(T["topic_exists"])
        return
    st.session_state["profile_list"].append(new)
    for key in ["messages", "student_agent", "teacher_agent"]:
        st.session_state[f"{key}_{new}"] = None if "agent" in key else []
    st.session_state["current_profile"] = new

def chat(prompt):
    profile = st.session_state["current_profile"]
    lang = st.session_state["lang_setting"]
    model = st.session_state["model_setting"]
    key = f"messages_{profile}"
    chat_box = st.container(border=True)

    chat_box.chat_message("user", avatar=user_image).write(prompt)
    st.session_state[key].append({"role": "user", "content": prompt})

    init_agents(profile, lang, model)
    student = st.session_state[f"student_agent_{profile}"]
    teacher = st.session_state[f"teacher_agent_{profile}"]

    result = student.initiate_chat(teacher, message=prompt, summary_method="reflection_with_llm")
    for m in result.chat_history:
        render_message(m, chat_box, avatar=user_image)
        st.session_state[key].append(m)

def main():
    init_session_state()
    st.set_page_config(page_title='K-Assistant - The Residemy Agent', layout='wide', initial_sidebar_state='auto', page_icon="img/favicon.ico")
    st.title(f"💬 {user_name}'s Chatbot")

    lang = st.session_state["lang_setting"]
    global T
    T = TRANSLATIONS[lang]

    with st.sidebar:
        st.selectbox("Language", LANG_OPTIONS, index=LANG_OPTIONS.index(lang), key="selected_lang", on_change=update_language)
        st.selectbox("Model", MODEL_OPTIONS, index=MODEL_OPTIONS.index(st.session_state["model_setting"]), key="selected_model", on_change=update_model)
        st.markdown(f"---\n### {T['saved_topics']}")

        for i, p in enumerate(st.session_state["profile_list"]):
            cols = st.columns([6, 1, 1])
            with cols[0]:
                if p == st.session_state["current_profile"]:
                    st.markdown(f"**\u261b {p}**")
                elif st.button(p, key=f"select_{i}"):
                    st.session_state["current_profile"] = p
            with cols[1]:
                if st.button("\u270f\ufe0f", key=f"edit_{i}"):
                    st.session_state["edit_target"] = p
            with cols[2]:
                if st.button("🗑️", key=f"delete_{i}"):
                    if len(st.session_state["profile_list"]) == 1:
                        st.warning(T["delete_only_one"])
                    else:
                        st.session_state["profile_list"].remove(p)
                        for k in ["messages", "student_agent", "teacher_agent"]:
                            del st.session_state[f"{k}_{p}"]
                        if st.session_state["current_profile"] == p:
                            st.session_state["current_profile"] = st.session_state["profile_list"][0]

        if "edit_target" in st.session_state:
            new_name = st.text_input(T["edit_topic"], key="rename_input")
            if st.button(T["confirm_rename"]):
                old = st.session_state["edit_target"]
                if new_name and new_name not in st.session_state["profile_list"]:
                    idx = st.session_state["profile_list"].index(old)
                    st.session_state["profile_list"][idx] = new_name
                    for k in ["messages", "student_agent", "teacher_agent"]:
                        st.session_state[f"{k}_{new_name}"] = st.session_state.pop(f"{k}_{old}")
                    if st.session_state["current_profile"] == old:
                        st.session_state["current_profile"] = new_name
                    del st.session_state["edit_target"]
                else:
                    st.warning(T["invalid_name"])

        st.text_input(T["new_topic"], key="new_profile_input")
        st.button(T["add_topic"], on_click=add_new_profile)
        st.image(user_image)

    prompt = st.chat_input(placeholder="Please input your command", key="chat_bot")
    if prompt:
        chat(prompt)

if __name__ == "__main__":
    main()
