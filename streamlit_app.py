import streamlit as st
import openai

st.title("💹 AI Trading Chatbot MVP")

user_input = st.text_input("Ask about crypto, forex, or stocks:")

if user_input:
    openai.api_key = st.secrets["OPENAI_API_KEY"]
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": user_input}]
    )
    st.write(response["choices"][0]["message"]["content"])
