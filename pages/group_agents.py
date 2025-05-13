import streamlit as st

import time
import json
from dotenv import load_dotenv
import os

# Import ConversableAgent class
import autogen
from autogen import ConversableAgent, LLMConfig, Agent
from autogen import AssistantAgent, UserProxyAgent, LLMConfig, register_function
from autogen.code_utils import content_str
from autogen.agentchat import initiate_group_chat
from autogen.agentchat.group.patterns import AutoPattern

from coding.constant import JOB_DEFINITION, RESPONSE_FORMAT
from coding.utils import show_chat_history, display_session_msg, save_messages_to_json, paging
from coding.agenttools import AG_search_expert, AG_search_news, AG_search_textbook, get_time

# Load environment variables from .env file
load_dotenv(override=True)

# https://ai.google.dev/gemini-api/docs/pricing
# URL configurations
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', None)
OPEN_API_KEY = os.getenv('OPEN_API_KEY', None)

placeholderstr = "Please input your command"
user_name = "Gild"
user_image = "https://www.w3schools.com/howto/img_avatar.png"

seed = 42

llm_config_gemini = LLMConfig(
    api_type = "google", 
    model="gemini-2.0-flash", # The specific model
    api_key=GEMINI_API_KEY,   # Authentication
)

llm_config_openai = LLMConfig(
    api_type = "openai", 
    model="gpt-4o-mini",    # The specific model
    api_key=OPEN_API_KEY,   # Authentication
)

def stream_data(stream_str):
    for word in stream_str.split(" "):
        yield word + " "
        time.sleep(0.05)

def save_lang():
    st.session_state['lang_setting'] = st.session_state.get("language_select")

def main():
    st.set_page_config(
        page_title='K-Assistant - The Residemy Agent',
        layout='wide',
        initial_sidebar_state='auto',
        menu_items={
            'Get Help': 'https://streamlit.io/',
            'Report a bug': 'https://github.com',
            'About': 'About your application: **Hello world**'
            },
        page_icon="img/favicon.ico"
    )

    # Show title and description.
    st.title(f"💬 {user_name}'s Group Chatbot")

    with st.sidebar:
        paging()

        selected_lang = st.selectbox("Language", ["English", "繁體中文"], index=0, on_change=save_lang, key="language_select")
        if 'lang_setting' in st.session_state:
            lang_setting = st.session_state['lang_setting']
        else:
            lang_setting = selected_lang
            st.session_state['lang_setting'] = lang_setting

        st_c_1 = st.container(border=True)
        with st_c_1:
            st.image("https://www.w3schools.com/howto/img_avatar.png")

    st_c_chat = st.container(border=True)
    
    display_session_msg(st_c_chat, user_image)

    student_persona = f"""You are a student willing to learn. After your result, say 'ALL DONE'. Please output in {lang_setting}"""

    teacher_persona = f"""You are a teacher. Please try to use tools to answer student's question according to the following rules:
    1. Check current time: use `get_time` tool to retrieve current date and time.
    2. Search news by `AG_search_news` according to user's question, try to distill student's question within 1~2 words and facilitate it as query string. Also you may search by sections,  e.g. ['Taiwan News', 'World News', 'Sports', 'Front Page', 'Features', 'Editorials', 'Business','Bilingual Pages'], if you cannot distill it, use None instead. 
    3. From the return news, randomly pick one news. Classify the news to the following <DISCIPLINE>:
    <DISCIPLINE>
        "Digital Sociology"
        "Information Systems Strategy"
        "Technology and Society"
        "Empathetic and research-driven"
        "Computational Social Science"
    </DISCIPLINE>
    4. Use `AG_search_expert` to select expert by <DISCIPLINE>, also Use `AG_search_textbook` to select a textbook by <DISCIPLINE>.
    5. Explain to student a interesting essay within 500 words about the news using expert and textbook. Please remember to mention about the expert and textbook you cite.
    6. After explanation, ask Tech_Agent and General_Agentt about their opinions.
    7. Please output in {lang_setting}

    """
    with llm_config_openai:
    # with llm_config_gemini:
        student_agent = ConversableAgent(
            name="Student_Agent",
            system_message=student_persona,
            is_termination_msg=lambda x: content_str(x.get("content")).find("ALL DONE") >= 0,
        )

        teacher_agent = ConversableAgent(
            name="Teacher_Agent",
            system_message=teacher_persona,
            functions=[AG_search_news, AG_search_textbook, AG_search_expert],
        )

        tech_agent = ConversableAgent(
            name="Tech_Agent",
            system_message="""You solve technical problems like software bugs
            and hardware issues."""
        )

        general_agent = ConversableAgent(
            name="General_Agent",
            system_message="You handle general, non-technical support questions."
        )

    user = ConversableAgent(
        name="user", 
        human_input_mode="ALWAYS",
        is_termination_msg=lambda x: content_str(x.get("content")).find("ALL DONE") >= 0,
        )

    pattern = AutoPattern(
        initial_agent=teacher_agent,  # Agent that starts the conversation
        agents=[teacher_agent, tech_agent, general_agent, student_agent],
        user_agent=user,
        group_manager_args={"llm_config": llm_config_openai}
    )

    register_function(
        AG_search_expert,
        caller=teacher_agent,
        executor=student_agent,
        description="Search EXPERTS_LIST by name, discipline, or interest.",
    )

    register_function(
        AG_search_textbook,
        caller=teacher_agent,
        executor=student_agent,
        description="Search TEXTBOOK_LIST by title, discipline, or related_expert.",
    )

    register_function(
        AG_search_news,
        caller=teacher_agent,
        executor=student_agent,
        description="Search a pre-fetched news DataFrame by keywords, sections, and date range.",
    )

    register_function(
        get_time,
        caller=teacher_agent,
        executor=student_agent,
        description="Get the current date & time.",
    )

    def st_reply_function(recipient, messages, sender, config):
        messages_content = messages[-1]['content']
        messages_role = messages[-1]['role']
        
        if messages_content and len(messages_content) > 0:
            if messages_role != 'tool':
                st_c_chat.chat_message("Student").write(messages_content)

                message = {"role": "Student", "content": messages_content}
                # Append to session history
                st.session_state.messages.append(message)

            elif messages_role == 'tool':
                st_c_chat.badge("Using tool...", icon="🛠️")

        return False, None

    def ta_reply_function(recipient, messages, sender, config):
        messages_content = messages[-1]['content']
        messages_role = messages[-1]['role']

        if messages_content and len(messages_content) > 0:
            if messages_role != 'tool':
                st_c_chat.chat_message("assistant", avatar=user_image).write(messages_content)
                message = {"role": messages_role, "content": messages_content}
                # Append to session history
                st.session_state.messages.append(message)
            elif messages_role == 'tool':
                st_c_chat.chat_message("assistant", avatar=user_image).write("Try to use tool.")
                st_c_chat.badge("tea - Using tool...", icon="🛠️")

        return False, None

    def gen_reply_function(recipient, messages, sender, config):
        messages_content = messages[-1]['content']
        messages_role = messages[-1]['role']

        if messages_content and len(messages_content) > 0:
            if messages_role != 'tool':
                st_c_chat.chat_message("General").write(messages_content)

                message = {"role": "General", "content": messages_content}
                # Append to session history
                st.session_state.messages.append(message)

            elif messages_role == 'tool':
                st_c_chat.badge("gen-Using tool...", icon="🛠️")

        return False, None

    def tech_reply_function(recipient, messages, sender, config):
        messages_content = messages[-1]['content']
        messages_role = messages[-1]['role']
        messages_name = messages[-1]['name']

        if messages_content and len(messages_content) > 0:
            if messages_role != 'tool':
                st_c_chat.chat_message("Tech").write(messages_content)
                message = {"role": "Tech", "content": messages_content}
                # Append to session history
                st.session_state.messages.append(message)

            elif messages_role == 'tool':
                st_c_chat.badge("tech-Using tool...", icon="🛠️")


        return False, None
        # return True, messages

    student_agent.register_reply(
        [Agent, None],
        reply_func=st_reply_function, 
        config={"callback": None},
    ) 

    teacher_agent.register_reply(
        [Agent, None],
        reply_func=ta_reply_function, 
        config={"callback": None},
    ) 

    tech_agent.register_reply(
        [Agent, None],
        reply_func=tech_reply_function, 
        config={"callback": None},
    ) 

    general_agent.register_reply(
        [Agent, None],
        reply_func=gen_reply_function, 
        config={"callback": None},
    ) 

    def generate_response(prompt):
        chat_result, _, _ = initiate_group_chat(
            pattern=pattern,
            messages=prompt,
            max_rounds=12
        )
        response = chat_result.chat_history
        # st.write(response)
        return response

    def chat(prompt: str):
        response = generate_response(prompt)
        conv_res = show_chat_history(st_c_chat, response, user_image)
        messages = json.loads(conv_res)
        file_path = save_messages_to_json(messages, output_dir="chat_logs")
        st.write(f"Saved chat history to `{file_path}`")
        st_c_chat.chat_message("assistant").write("Any question?")
    if prompt := st.chat_input(placeholder=placeholderstr, key="chat_bot"):
        chat(prompt)

if __name__ == "__main__":
    main()
