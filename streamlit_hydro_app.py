# streamlit_hydro_app.py
import streamlit as st
import os
import pandas as pd
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
import sqlite3

# Import our database tools
from database_tools import text_to_sql, init_database, get_database_info

# --- 1. Page Configuration and Title ---

st.set_page_config(page_title="Asisten Hidroponik AI 💧", page_icon="🌱")
st.title("Asisten Hidroponik AI 💧")
st.caption("Ngobrol santai tentang hobi menanam hidroponik. Tanya apa saja soal tanaman, perawatan, atau jadwal! 🌱")

# --- 2. Sidebar for Settings ---

with st.sidebar:
    st.subheader("Pengaturan")
    
    google_api_key = st.text_input("Google AI API Key", type="password", key="google_api_key")
    
    st.markdown("---")
    
    reset_chat_button = st.button("Mulai Percakapan Baru", help="Hapus semua pesan dan mulai dari awal.")
    if reset_chat_button:
        st.session_state.messages = []
        st.session_state.agent = None
    
    if st.button("Reset Database", help="Hapus database dan buat ulang dari file Excel."):
        init_database()
        st.session_state.agent = None
        st.success("Database berhasil di-reset! Silakan mulai percakapan baru.")
        
    st.markdown("---")

# --- 3. Main Chat Interface Logic ---

if "messages" not in st.session_state:
    st.session_state.messages = []
    
db_info = get_database_info()
db_schema_str = str(db_info)
SYSTEM_MESSAGE = SystemMessage(
    content=f"""
    Kamu adalah Asisten Hidroponik AI yang santai dan ramah.
    Gunakan bahasa yang sederhana dan mudah dimengerti. 
    Jawab pertanyaan pengguna tentang hidroponik, seperti jenis tanaman, 
    cara perawatan, jadwal penyiraman/pemupukan, atau pengetahuan umum.
    
    Kamu memiliki akses ke database yang berisi informasi berikut:
    {db_schema_str}
    
    Gunakan alat 'text_to_sql' untuk mendapatkan informasi dari database.
    Jika pertanyaan pengguna membutuhkan data, selalu gunakan alat ini.
    Jangan pernah membuat data atau jadwal palsu.
    Tawarkan rekomendasi atau tips berdasarkan data yang kamu miliki.
    
    Jika pengguna bertanya tentang hal yang tidak ada di databasemu, 
    jawab dengan jujur bahwa kamu tidak memiliki informasi tersebut, 
    dan tawarkan untuk mencari informasi lain yang mungkin relevan.
    """
)
    
# Initialize agent
if "agent" not in st.session_state or st.session_state.agent is None:
    if google_api_key:
        try:
            init_database()
            llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.2, google_api_key=google_api_key)
            tools = [text_to_sql]
            
            agent = create_react_agent(llm, tools)
            st.session_state.agent = agent

        except Exception as e:
            st.error(f"Error saat menginisialisasi agen: {e}. Pastikan Google AI API Key Anda benar dan sudah aktif.")
            st.session_state.agent = None
    else:
        st.info("Silakan masukkan Google AI API Key Anda di sidebar untuk memulai.")

# Display chat messages from history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Handle user input
if prompt := st.chat_input("Tanya tentang tanaman hidroponik Anda..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("user"):
        st.markdown(prompt)

    if not st.session_state.agent:
        with st.chat_message("assistant"):
            st.markdown("Silakan masukkan Google AI API Key Anda di sidebar untuk memulai.")
    else:
        with st.chat_message("assistant"):
            with st.spinner("Mencari jawaban..."):
                try:
                    messages_with_system = [SYSTEM_MESSAGE] + [HumanMessage(content=msg['content']) if msg['role'] == 'user' else AIMessage(content=msg['content']) for msg in st.session_state.messages]
                    
                    full_response_dict = st.session_state.agent.invoke(
                        {"messages": messages_with_system}
                    )
                    
                    full_response = ""
                    tool_code_to_display = ""
                    
                    if full_response_dict and full_response_dict.get("messages"):
                        final_message = full_response_dict["messages"][-1]
                        
                        if isinstance(final_message, AIMessage):
                            full_response = final_message.content
                            
                            if final_message.tool_calls:
                                for tool_call in final_message.tool_calls:
                                    if "sql_query" in tool_call.get("args", {}):
                                        tool_code_to_display = tool_call["args"]["sql_query"]
                        else:
                            full_response = str(final_message)
                    else:
                        full_response = "Maaf, ada masalah saat memproses respons dari AI."

                    if tool_code_to_display:
                        st.code(tool_code_to_display, language="sql")
                    
                    st.markdown(full_response)
                    
                    st.session_state.messages.append({"role": "assistant", "content": full_response})
                                    
                except Exception as e:
                    st.error(f"Maaf, ada masalah. Silakan coba lagi. Error: {e}")
                    st.session_state.messages.append({"role": "assistant", "content": f"Maaf, ada masalah. Error: {e}"})