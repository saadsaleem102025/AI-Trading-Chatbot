import streamlit as st
from openai import OpenAI

st.title("💯🚀🎯 AI Trading Chatbot ")

# Initialize the OpenAI client
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Input for user query
user_input = st.text_input("Ask about crypto, forex, or stocks:")

if user_input:
    # Send query to GPT
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful trading assistant."},
            {"role": "user", "content": user_input},
        ],
    )

    # Show the model's response
    st.write(response.choices[0].message.content)


