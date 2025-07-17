import streamlit as st
import os
from dotenv import load_dotenv
from autogen import ConversableAgent, LLMConfig
from autogen.code_utils import content_str

load_dotenv(override=True)

MODEL_OPTIONS = ["gpt-4o-mini", "gpt-4o"]
LANG_OPTIONS = ["English", "繁體中文"]

LLM_CONFIG_MAP = {
    model: LLMConfig(api_type="openai", model=model, api_key=os.getenv("OPENAI_API_KEY"))
    for model in MODEL_OPTIONS
}

TRANSLATIONS = {
    "繁體中文": {
        "saved_topics": "已存記錄主題", "new_topic": "新增主題名稱", "add_topic": "新增主題",
        "edit_topic": "編輯新主題名稱", "confirm_rename": "確認修改", "delete_only_one": "無法刪除唯一主題",
        "topic_exists": "主題名稱已存在", "invalid_name": "主題名稱無效或已存在"
    },
    "English": {
        "saved_topics": "Saved Topics", "new_topic": "New Topic Name", "add_topic": "Add Topic",
        "edit_topic": "Edit Topic Name", "confirm_rename": "Confirm Rename",
        "delete_only_one": "Cannot delete the only topic", "topic_exists": "Topic already exists",
        "invalid_name": "Invalid or duplicated topic name"
    }
}

USER_NAME = "Angela"
USER_IMAGE = "https://www.w3schools.com/howto/img_avatar.png"

def init_session_state():
    defaults = {
        "lang_setting": "繁體中文",
        "model_setting": "gpt-4o-mini",
        "user_name": USER_NAME,
        "current_profile": "KA助理",
        "profile_list": ["KA助理", "職涯顧問", "日常聊天"]
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)
    for profile in st.session_state["profile_list"]:
        for suffix in ["messages", "student_agent", "teacher_agent"]:
            st.session_state.setdefault(f"{suffix}_{profile}", [] if suffix == "messages" else None)

def init_agents(profile, lang, model):
    if st.session_state.get(f"student_agent_{profile}"):
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
        is_termination_msg=lambda x: "ALL DONE" in content_str(x.get("content", "")),
        human_input_mode="NEVER"
    )

    st.session_state[f"student_agent_{profile}"] = student
    st.session_state[f"teacher_agent_{profile}"] = teacher

def render_message(msg, container):
    role, content = msg.get("role", "user"), msg.get("content", "")
    styles = {
        "user": ("right", "#DCF8C6", "🙋"),
        "student": ("left", "#E0F7FA", "🧑‍🎓"),
        "assistant": ("left", "#F1F0F0", "👩‍🏫")
    }
    align, color, icon = styles.get(role, ("left", "#fff", ""))
    container.markdown(
        f"<div style='text-align: {align}; background-color: {color}; padding: 8px; border-radius: 10px; margin: 4px 0;'>{icon} {content}</div>",
        unsafe_allow_html=True
    )

def chat(prompt):
    profile, lang, model = st.session_state["current_profile"], st.session_state["lang_setting"], st.session_state["model_setting"]
    key = f"messages_{profile}"
    init_agents(profile, lang, model)

    student = st.session_state[f"student_agent_{profile}"]
    teacher = st.session_state[f"teacher_agent_{profile}"]

    st.session_state[key].append({"role": "user", "content": prompt})
    st.chat_message("user").markdown(f"🙋 {prompt}")

    with st.spinner("💬 Agent thinking..."):
        result = student.initiate_chat(
            teacher,
            message=prompt,
            summary_method=None,
            n_round=1
        )

    for msg in result.chat_history:
        role = "student" if msg["name"] == "Student_Agent" else "assistant"
        content = msg["content"].strip()
        st.session_state[key].append({"role": role, "content": content})
        st.chat_message(role).markdown(f"{'🧑‍🎓' if role == 'student' else '👩‍🏫'} {content}")

def sidebar_ui(T):
    st.selectbox("Language", LANG_OPTIONS, index=LANG_OPTIONS.index(st.session_state["lang_setting"]),
                 key="selected_lang", on_change=lambda: st.session_state.update({"lang_setting": st.session_state["selected_lang"]}))
    st.selectbox("Model", MODEL_OPTIONS, index=MODEL_OPTIONS.index(st.session_state["model_setting"]),
                 key="selected_model", on_change=lambda: st.session_state.update({"model_setting": st.session_state["selected_model"]}))

    st.markdown(f"---\n### {T['saved_topics']}")
    for i, p in enumerate(st.session_state["profile_list"]):
        cols = st.columns([6, 1, 1])
        with cols[0]:
            if p == st.session_state["current_profile"]:
                st.markdown(f"**☛ {p}**")
            elif st.button(p, key=f"select_{i}"):
                st.session_state["current_profile"] = p
        with cols[1]:
            if st.button("✏️", key=f"edit_{i}"):
                st.session_state["edit_target"] = p
        with cols[2]:
            if st.button("🗑️", key=f"delete_{i}"):
                if len(st.session_state["profile_list"]) == 1:
                    st.warning(T["delete_only_one"])
                else:
                    st.session_state["profile_list"].remove(p)
                    for k in ["messages", "student_agent", "teacher_agent"]:
                        st.session_state.pop(f"{k}_{p}", None)
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
                    st.session_state[f"{k}_{new_name}"] = st.session_state.pop(f"{k}_{old}", None)
                if st.session_state["current_profile"] == old:
                    st.session_state["current_profile"] = new_name
                del st.session_state["edit_target"]
            else:
                st.warning(T["invalid_name"])

    st.text_input(T["new_topic"], key="new_profile_input")
    if st.button(T["add_topic"]):
        new = st.session_state["new_profile_input"].strip()
        if not new or new in st.session_state["profile_list"]:
            st.warning(T["topic_exists"])
        else:
            st.session_state["profile_list"].append(new)
            for k in ["messages", "student_agent", "teacher_agent"]:
                st.session_state[f"{k}_{new}"] = [] if k == "messages" else None
            st.session_state["current_profile"] = new

    st.image(USER_IMAGE)

def main():
    init_session_state()
    st.set_page_config(page_title='K-Assistant - The Residemy Agent', layout='wide', page_icon="img/favicon.ico")
    st.title(f"💬 {USER_NAME}'s Chatbot")
    T = TRANSLATIONS[st.session_state["lang_setting"]]

    with st.sidebar:
        sidebar_ui(T)

    key = f"messages_{st.session_state['current_profile']}"
    for msg in st.session_state[key]:
        render_message(msg, st)

    if prompt := st.chat_input("Please input your command", key="chat_bot"):
        chat(prompt)

if __name__ == "__main__":
    main()
