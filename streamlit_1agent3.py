import streamlit as st
import os
from dotenv import load_dotenv
from autogen import ConversableAgent
import re
import json  

load_dotenv(override=True)

MODEL_OPTIONS = ["gpt-4o-mini", "gpt-4o"]
LANG_OPTIONS = ["English", "繁體中文"]
USER_NAME = "Angela"
USER_IMAGE = "https://www.w3schools.com/howto/img_avatar.png"

def get_llm_config_map():
    api_key = os.getenv("OPENAI_API_KEY")
    assert api_key and api_key.startswith("sk-"), f"Invalid or missing OpenAI API key: {api_key}"
    return {
        model: {
            "config_list": [{"model": model, "api_key": api_key}],
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
        "profile_list": ["KA助理", "職歷顯細", "日常聊天", "跨領域諮詢室"],
        "chat_stage": "init",
        "json_response": None
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)
    for profile in st.session_state["profile_list"]:
        st.session_state.setdefault(f"messages_{profile}", [])
        st.session_state.setdefault(f"agent_{profile}", None)

def init_agent(profile, lang, model):
    if st.session_state.get(f"agent_{profile}"):
        return
    llm_config = get_llm_config_map()[model]
    if profile == "跨領域諮詢室":
        system_prompt = f"""
You are a cross-disciplinary study planning advisor. Your task is to provide structured academic and career suggestions.

The user will provide:
- their current major (e.g. economics, psychology)
- their desired future field (e.g. software product manager)

🧠 If both `current_major` and `desired_field` are already provided (even implicitly), DO NOT ask any clarifying questions. Proceed to generate the JSON response immediately.

If either value is missing or vague, then and only then ask clarifying questions.

When responding with final suggestions, use this JSON schema:
{{
  "current_major": "...",
  "desired_field": "...",
  "recommended_courses": [{{ "course_name": "...", "description": "..." }}],
  "possible_projects": [{{ "project_name": "...", "description": "..." }}],
  "suitable_internship_directions": ["..."],
  "networking_strategies": ["..."],
  "timeline_advice": {{ "year_1": "...", "year_2": "...", "year_3": "...", "year_4": "..." }}
}}

Do not include markdown (like ```json).
Respond in the selected language (e.g., Traditional Chinese).
"""
    else:
        system_prompt = f"""
You are a helpful teacher answering user's questions directly.
Respond clearly and professionally in {lang}.
If the question is ambiguous, ask clarifying questions first.
"""
    agent = ConversableAgent(
        name="TeacherAgent",
        system_message=system_prompt,
        llm_config=llm_config,
        human_input_mode="NEVER",
    )
    st.session_state[f"agent_{profile}"] = agent

def render_study_plan(data):
    return f"""
<h3 style='margin-top: 0.5em;'>🧭 <b>主修 ➜ 目標</b></h3>
<b>主修 (Current Major):</b> {data.get("current_major", "")}<br>
<b>目標 (Desired Field):</b> {data.get("desired_field", "")}

### 📚 推薦課程 (Recommended Courses)
{chr(10).join([f"- **{c['course_name']}**：{c['description']}" for c in data.get("recommended_courses", [])])}

### 🛠️ 建議專案 (Possible Projects)
{chr(10).join([f"- **{p['project_name']}**：{p['description']}" for p in data.get("possible_projects", [])])}

### 👩‍💻 適合的實習方向 (Internship Directions)
{chr(10).join([f"- {i}" for i in data.get("suitable_internship_directions", [])])}

### 🤝 人脈拓展策略 (Networking Strategies)
{chr(10).join([f"- {n}" for n in data.get("networking_strategies", [])])}

### 🗓️ 建議時程 (Timeline Advice)
{chr(10).join([f"- **{y}**：{t}" for y, t in data.get("timeline_advice", {}).items()])}
"""

def chat(prompt):
    profile = st.session_state["current_profile"]
    model = st.session_state["model_setting"]
    lang = st.session_state["lang_setting"]
    key = f"messages_{profile}"

    init_agent(profile, lang, model)
    agent = st.session_state[f"agent_{profile}"]
    st.session_state[key].append({"role": "user", "content": prompt})

    with st.spinner("💬 AI 回覆中..."):
        reply = agent.generate_reply(messages=st.session_state[key])
        content = str(getattr(reply, 'content', reply)).strip()
        try:
            parsed = json.loads(re.sub(r"```json|```", "", content))
            markdown = render_study_plan(parsed)
            st.session_state[key].append({"role": "assistant", "content": markdown})
        except:
            st.session_state[key].append({"role": "assistant", "content": content})
    st.rerun()


def render_message(msg):
    role, content = msg.get("role"), msg.get("content")
    if role == "user":
        align = "right"
        color = "#FFF7EE"
        icon = "🙋"
        margin = "margin-left: auto; margin-right: 0;"
    else:
        align = "left"
        color = "#F1F0F0"
        icon = "👩‍🏫"
        margin = "margin-left: 0; margin-right: auto;"

    st.markdown(
        f"<div style='text-align: {align}; background-color: {color}; padding: 8px; border-radius: 10px; {margin} max-width: 90%;'>{icon} {content}</div>",
        unsafe_allow_html=True
    )

def main():
    init_session_state()
    st.set_page_config(page_title='K-Assistant 1 Agent Version', layout='wide')
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
                st.rerun()

    key = f"messages_{st.session_state['current_profile']}"
    for msg in st.session_state[key]:
        render_message(msg)

    if prompt := st.chat_input(placeholder="💡請描述你的主修與想發展/跨領域的目標，例如：「我主修心理學，想做產品經理，有哪些選課與人脈建議？」"):
        chat(prompt)

if __name__ == "__main__":
    main()
