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
        "topic_exists": "主題名稱已存在", "invalid_name": "主題名稱無效或已存在",
    },
    "English": {
        "saved_topics": "Saved Topics", "new_topic": "New Topic Name", "add_topic": "Add Topic",
        "edit_topic": "Edit Topic Name", "confirm_rename": "Confirm Rename",
        "delete_only_one": "Cannot delete the only topic", "topic_exists": "Topic already exists",
        "invalid_name": "Invalid or duplicated topic name"
    }
}

def init_session_state():
    defaults = {
        "lang_setting": "繁體中文",
        "model_setting": "gpt-4o-mini",
        "user_name": USER_NAME,
        "current_profile": "KA助理",
        "profile_list": ["KA助理", "職歷顯細", "日常聊天"],
        "chat_stage": "init"
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)
    for profile in st.session_state["profile_list"]:
        st.session_state.setdefault(f"messages_{profile}", [])
        st.session_state.setdefault(f"agent_{profile}", None)

def init_agent(profile, lang, model):
    if st.session_state.get(f"agent_{profile}"):
        return
    llm_config = LLM_CONFIG_MAP[model]
    agent = ConversableAgent(
        name="TeacherAgent",
        system_message=f"""
You are a helpful teacher answering user's questions directly.
Respond clearly and professionally in {lang}.
If the question is ambiguous, ask clarifying questions first.
""",
        llm_config=llm_config,
        human_input_mode="NEVER",
    )
    st.session_state[f"agent_{profile}"] = agent

def render_message(msg, container):
    role, content = msg.get("role", "user"), msg.get("content", "")
    styles = {
        "user": ("right", "#DCF8C6", "🙋"),
        "assistant": ("left", "#F1F0F0", "👩‍🏫")
    }
    align, color, icon = styles.get(role, ("left", "#fff", ""))
    container.markdown(
        f"<div style='text-align: {align}; background-color: {color}; padding: 8px; border-radius: 10px; margin: 4px 0;'>{icon} {content}</div>",
        unsafe_allow_html=True
    )

def safe_extract_content(reply):
    if isinstance(reply, dict):
        return reply.get("content", "")
    elif isinstance(reply, str):
        return reply
    elif hasattr(reply, 'content'):
        return reply.content
    elif hasattr(reply, '__str__'):
        return str(reply)
    return "(No valid reply)"

def chat(prompt):
    profile = st.session_state["current_profile"]
    model = st.session_state["model_setting"]
    lang = st.session_state["lang_setting"]
    key = f"messages_{profile}"

    init_agent(profile, lang, model)
    agent = st.session_state[f"agent_{profile}"]
    proxy = UserProxyAgent("proxy", human_input_mode="NEVER")

    st.session_state[key].append({"role": "user", "content": prompt})

    with st.spinner("👩‍🏫 Teacher 回覆中..."):
        try:
            if st.session_state["chat_stage"] == "init":
                reply1 = agent.generate_reply(messages=[{"role": "user", "content": prompt}])
                content1 = safe_extract_content(reply1)
                st.session_state[key].append({"role": "assistant", "content": content1})

                reply2 = agent.generate_reply(messages=[{"role": "user", "content": prompt}, {"role": "assistant", "content": content1},
                                                    {"role": "user", "content": "請根據以上回答，提出一個延伸問題。"}])
                content2 = safe_extract_content(reply2)
                st.session_state[key].append({"role": "assistant", "content": content2})

                st.session_state["chat_stage"] = "followup"

            elif st.session_state["chat_stage"] == "followup":
                if any(kw in prompt.lower() for kw in ["沒有問題", "沒問題", "no", "nope", "none"]):
                    st.session_state[key].append({"role": "assistant", "content": "好的，今天的問題解答就到這裡，如果還有問題，歡迎再次詢問！👩‍🏫"})
                    st.session_state["chat_stage"] = "init"
                else:
                    reply = agent.generate_reply(messages=[{"role": "user", "content": prompt}])
                    content = safe_extract_content(reply)
                    st.session_state[key].append({"role": "assistant", "content": content})
        except Exception as e:
            st.error(f"聊天錯誤: {str(e)}")
            st.session_state[key].append({"role": "assistant", "content": "抱歉，發生錯誤，請稍後再試。"})

def main():
    init_session_state()
    st.set_page_config(page_title='K-Assistant 1 Agent Version', layout='wide')
    st.title(f"💬 {USER_NAME}'s 1-Agent Chatbot")
    T = TRANSLATIONS[st.session_state["lang_setting"]]

    with st.sidebar:
        st.selectbox("Language", LANG_OPTIONS, index=LANG_OPTIONS.index(st.session_state["lang_setting"]),
                     key="selected_lang", on_change=lambda: st.session_state.update({"lang_setting": st.session_state["selected_lang"]}))
        st.selectbox("Model", MODEL_OPTIONS, index=MODEL_OPTIONS.index(st.session_state["model_setting"]),
                     key="selected_model", on_change=lambda: st.session_state.update({"model_setting": st.session_state["selected_model"]}))
        st.markdown(f"---\n### {T['saved_topics']}")
        for i, p in enumerate(st.session_state["profile_list"]):
            if st.button(p, key=f"select_{i}"):
                st.session_state["current_profile"] = p

    key = f"messages_{st.session_state['current_profile']}"
    for msg in st.session_state[key]:
        render_message(msg, st)

    if prompt := st.chat_input("請輸入您的問題："):
        chat(prompt)
        st.rerun()

if __name__ == "__main__":
    main()
