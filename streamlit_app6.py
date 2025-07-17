import streamlit as st
from openai import OpenAI
import time

placeholderstr = "Please input your command"
user_name = "Angela"
user_image = "https://www.w3schools.com/howto/img_avatar.png"
LANG_OPTIONS = ["English", "繁體中文"]

TRANSLATIONS = {
    "繁體中文": {
        "saved_topics": "📅 已存記錄主題",
        "new_topic": "新增主題名稱",
        "add_topic": "➕ 新增主題",
        "edit_topic": "編輯新主題名稱",
        "confirm_rename": "🔄 確認修改",
        "delete_only_one": "無法刪除唯一主題",
        "topic_exists": "主題名稱已存在",
        "invalid_name": "主題名稱無效或已存在"
    },
    "English": {
        "saved_topics": "📅 Saved Topics",
        "new_topic": "New Topic Name",
        "add_topic": "➕ Add Topic",
        "edit_topic": "Edit Topic Name",
        "confirm_rename": "🔄 Confirm Rename",
        "delete_only_one": "Cannot delete the only topic",
        "topic_exists": "Topic already exists",
        "invalid_name": "Invalid or duplicated topic name"
    }
}

def stream_data(text):
    for word in text.split():
        yield word + " "
        time.sleep(0.15)

def init_session_state():
    default_profiles = ["KA助理", "職涯顧問", "日常聊天"]
    defaults = {
        "messages": [],
        "lang_setting": "繁體中文",
        "user_name": user_name,
        "current_profile": "KA助理",
        "profile_list": default_profiles,
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)
    for p in st.session_state["profile_list"]:
        st.session_state.setdefault(f"messages_{p}", [])

def update_language():
    st.session_state["lang_setting"] = st.session_state["selected_lang"]

def add_new_profile():
    new = st.session_state["new_profile_input"].strip()
    if new and new not in st.session_state["profile_list"]:
        st.session_state["profile_list"].append(new)
        st.session_state[f"messages_{new}"] = []
        st.session_state["current_profile"] = new
    elif new in st.session_state["profile_list"]:
        st.warning(T["topic_exists"])

def render_message(msg, container, avatar=None):
    role, content = msg.get("role", "user"), msg.get("content", "")
    avatar = avatar if role == "user" else msg.get("image", None)
    container.chat_message(role, avatar=avatar).markdown(content)

def main():
    init_session_state()
    st.set_page_config(
        page_title='K-Assistant - The Residemy Agent', layout='wide', initial_sidebar_state='auto', page_icon="img/favicon.ico"
    )
    st.title(f"💬 {user_name}'s Chatbot")

    lang = st.session_state.get("lang_setting", "繁體中文")
    global T
    T = TRANSLATIONS[lang]

    with st.sidebar:
        st.selectbox("Language", LANG_OPTIONS, index=LANG_OPTIONS.index(lang),
                     key="selected_lang", on_change=update_language)
        st.markdown(f"---\n### {T['saved_topics']}")

        for i, p in enumerate(st.session_state["profile_list"]):
            cols = st.columns([6, 1, 1])
            with cols[0]:
                if p == st.session_state["current_profile"]:
                    st.markdown(f"**👉 {p}**")
                elif st.button(p, key=f"select_{i}"):
                    st.session_state["current_profile"] = p
            with cols[1]:
                if st.button("✏️", key=f"edit_{i}"):
                    st.session_state["edit_target"] = p
            with cols[2]:
                if st.button("🔚", key=f"delete_{i}"):
                    if len(st.session_state["profile_list"]) == 1:
                        st.warning(T["delete_only_one"])
                    else:
                        st.session_state["profile_list"].remove(p)
                        del st.session_state[f"messages_{p}"]
                        if st.session_state["current_profile"] == p:
                            st.session_state["current_profile"] = st.session_state["profile_list"][0]

        if "edit_target" in st.session_state:
            new_name = st.text_input(T["edit_topic"], key="rename_input")
            if st.button(T["confirm_rename"]):
                old = st.session_state["edit_target"]
                if new_name and new_name not in st.session_state["profile_list"]:
                    idx = st.session_state["profile_list"].index(old)
                    st.session_state["profile_list"][idx] = new_name
                    st.session_state[f"messages_{new_name}"] = st.session_state.pop(f"messages_{old}")
                    if st.session_state["current_profile"] == old:
                        st.session_state["current_profile"] = new_name
                    del st.session_state["edit_target"]
                else:
                    st.warning(T["invalid_name"])

        st.text_input(T["new_topic"], key="new_profile_input")
        st.button(T["add_topic"], on_click=add_new_profile)
        st.image(user_image)

    st_c_chat = st.container(border=True)
    key = f"messages_{st.session_state['current_profile']}"
    for msg in st.session_state[key]:
        render_message(msg, st_c_chat, avatar=user_image)

    def chat(prompt):
        st_c_chat.chat_message("user", avatar=user_image).write(prompt)
        st.session_state[key].append({"role": "user", "content": prompt})
        response = f"You type: {prompt}"
        st.session_state[key].append({"role": "assistant", "content": response})
        st_c_chat.chat_message("assistant").write_stream(stream_data(response))

    prompt = st.chat_input(placeholder=placeholderstr, key="chat_bot")
    if prompt:
        chat(prompt)

if __name__ == "__main__":
    main()
