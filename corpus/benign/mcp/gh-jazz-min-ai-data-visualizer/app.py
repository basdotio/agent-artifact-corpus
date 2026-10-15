import asyncio
import streamlit as st
import httpx, openai
import os
import sys
print("Python executable:", sys.executable)
print("OpenAI version:", openai.__version__)
print("HTTPX version:", httpx.__version__)
print("Current working directory:", os.getcwd())
from ai_visualizer import generate_visualization


st.set_page_config(page_title="AI Data Visualization Assistant", page_icon="📊")

st.title("📊 AI Data Visualization Assistant")
st.write("Upload a CSV and ask for a chart. The AI will decide the best type to generate!")

uploaded_file = st.file_uploader("Upload your CSV", type=["csv"])

if uploaded_file:
    file_path = "uploaded.csv"
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    st.success("✅ File uploaded successfully!")

    user_input = st.text_input("Ask a question (e.g., 'Show sales by region')")

    if st.button("Generate Chart"):
        with st.spinner("AI is analyzing and creating the chart..."):
            try:
                chart_path = asyncio.run(generate_visualization(file_path, user_input))
                st.image(chart_path, caption="Generated Chart", width='stretch')
            except Exception as e:
                st.error(f"Error: {e}")
