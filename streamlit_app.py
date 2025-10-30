import streamlit as st
import openai
st.title("💹 AI Trading Chatbot MVP")

# Initialize client
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Input box for user query
user_input = st.text_input("Ask about crypto, forex, or stocks:")

if user_input:
    # Call GPT model
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful trading assistant."},
            {"role": "user", "content": user_input},
        ],
    )

    # Display response
    st.write(response.choices[0].message.content)

