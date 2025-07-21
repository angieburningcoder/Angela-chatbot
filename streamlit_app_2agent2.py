import streamlit as st
import os
from dotenv import load_dotenv
from autogen import ConversableAgent, UserProxyAgent
from autogen.code_utils import content_str
import re

load_dotenv(override=True)

MODEL_OPTIONS = ["gpt-4o-mini", "gpt-4o"]
LANG_OPTIONS = ["English", "繁體中文"]
USER_NAME = "Angela"
USER_IMAGE = "https://www.w3schools.com/howto/img_avatar.png"

LLM_CONFIG_MAP = {
    model: {
        "config_list": [{"model": model, "api_key": os.getenv("OPENAI_API_KEY")}],
        "temperature": 0.7
    }
    for model in MODEL_OPTIONS
}

TRANSLATIONS = {
    "繁體中文": {
        "saved_topics": "已存記錄主題", "new_topic": "新增主題名稱", "add_topic": "新增主題",
        "edit_topic": "編輯新主題名稱", "confirm_rename": "確認修改", "delete_only_one": "無法刪除唯一主題",
        "topic_exists": "主題名稱已存在", "invalid_name": "主題名稱無效或已存在", "upload_avatar": "上傳頭像", "reupload_avatar": "重新上傳頭像"
    },
    "English": {
        "saved_topics": "Saved Topics", "new_topic": "New Topic Name", "add_topic": "Add Topic",
        "edit_topic": "Edit Topic Name", "confirm_rename": "Confirm Rename",
        "delete_only_one": "Cannot delete the only topic", "topic_exists": "Topic already exists",
        "invalid_name": "Invalid or duplicated topic name", "upload_avatar": "Upload Avatar", "reupload_avatar": "Re-upload Avatar"
    }
}
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
        system_message=f"""
You are a curious student receiving a question from a user.

Your task is to:
1. Carefully read and interpret the user’s original prompt.
2. Summarize the user’s underlying intent or concern.
3. Rephrase that into a thoughtful and specific question to ask a teacher.

You MUST NOT directly repeat the user's original prompt.
Instead, output in the following format:

User's Original Prompt:
<copy original prompt>

🧠 Student's Understanding:
<your analysis and interpretation of what the user wants>

✅ Reformulated Question to Teacher:
<ask the teacher a clear question>

Respond only in {lang}.
""",
        llm_config=llm_config
    )

    teacher = ConversableAgent(
        name="Teacher_Agent",
        system_message=f"""
You are a helpful and experienced teacher.
You will receive questions from a student who reformulated the user's concern.
Please provide clear, constructive answers. If the question is unclear, ask clarifying questions.

Respond only in {lang}.
""",
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
        "student": ("left", "#E0F7FA", "🧑‍🏫"),
        "assistant": ("left", "#F1F0F0", "👩‍🏫")
    }
    align, color, icon = styles.get(role, ("left", "#fff", ""))
    container.markdown(
        f"<div style='text-align: {align}; background-color: {color}; padding: 8px; border-radius: 10px; margin: 4px 0;'>{icon} {content}</div>",
        unsafe_allow_html=True
    )

def safe_content(raw_content):
    content = raw_content.strip() if raw_content else ""
    if not content or content.lower() in [":student_agent", ":teacher_agent"]:
        return "⚠️ 沒有收到有效回覆，請稍後再試一次或修改問題。"
    return content

def safe_extract_content(reply):
    if isinstance(reply, dict):
        return safe_content(reply.get("content", ""))
    elif isinstance(reply, str):
        return safe_content(reply)
    return "⚠️ 回覆格式錯誤"

def extract_followups(raw):
    lines = raw.splitlines()
    questions = []
    for l in lines:
        l = re.sub(r"^[^\w一-鿿]*", "", l.strip())
        if 4 <= len(l) <= 50 and ("?" in l or "？" in l):
            questions.append(l)
    return list(dict.fromkeys(questions))[:3]

def chat(prompt):
    profile, lang, model = st.session_state["current_profile"], st.session_state["lang_setting"], st.session_state["model_setting"]
    key = f"messages_{profile}"
    init_agents(profile, lang, model)

    student = st.session_state[f"student_agent_{profile}"]
    teacher = st.session_state[f"teacher_agent_{profile}"]

    st.session_state[key].append({"role": "user", "content": prompt})
    st.chat_message("user").markdown(f"🙋 {prompt}")

    with st.spinner("🧠 Student 正在分析問題..."):
        student_msg = safe_extract_content(student.generate_reply(messages=[{"role": "user", "content": prompt}]))
        st.session_state[key].append({"role": "student", "content": student_msg})
        st.chat_message("student").markdown(f"🗣️ {student_msg}")

    with st.spinner("👩‍🏫 Teacher 回覆中..."):
        teacher_msg = safe_extract_content(teacher.generate_reply(messages=[{"role": "user", "content": student_msg}]))
        st.session_state[key].append({"role": "assistant", "content": teacher_msg})
        st.chat_message("assistant").markdown(f"👩‍🏫 {teacher_msg}")

    with st.spinner("💡 正在根據老師的回答推薦下一步問題..."):
        followup_prompt = f"""
Please rewrite 3 follow-up questions that are:
- short (less than 20 words)
- directly askable to the teacher
- concrete and deep
Avoid any explanation, format, or labels.
Content:
{teacher_msg}
"""
        followup_raw = safe_extract_content(student.generate_reply(messages=[{"role": "user", "content": followup_prompt}]))
        followup_questions = extract_followups(followup_raw)

    if followup_questions:
        st.markdown("### 🔍 想要更深入了解嗎？試試以下問題：")
        for q in followup_questions:
            st.markdown(
                f"<div style='padding: 6px 12px; margin: 4px 0; background-color: #f0f0f0; border-radius: 10px;'>👉 {q}</div>",
                unsafe_allow_html=True
            )

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
                st.markdown(f"**☚ {p}**")
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

    T = TRANSLATIONS[st.session_state["lang_setting"]]  

    user_img = st.session_state.get("user_image", None)
    if user_img is None:
        uploaded_file = st.file_uploader(T["upload_avatar"], type=["png", "jpg", "jpeg"])
        if uploaded_file is not None:
            st.session_state["user_image"] = uploaded_file
            st.image(uploaded_file, width=120)
    else:
        st.image(user_img, width=120)
        if st.button(T["reupload_avatar"]):
            del st.session_state["user_image"]
            st.rerun()

def main():
    init_session_state()

    if "auto_followup_prompt" in st.session_state:
        followup = st.session_state.pop("auto_followup_prompt")
        chat(followup)
        st.rerun()

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
    