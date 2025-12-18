import streamlit as st

def apply_custom_styles():
    st.set_page_config(
        page_title="Strict PDF Extractor",
        page_icon="🎯",
        layout="wide"
    )

    st.markdown("""
        <style>
        .main {
            background-color: #f8f9fa;
        }
        .stButton>button {
            width: 100%;
            background-color: #007bff;
            color: white;
            border-radius: 8px;
            height: 50px;
            font-weight: bold;
            transition: all 0.3s ease;
        }
        .stButton>button:hover {
            background-color: #0056b3;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,123,255,0.3);
        }
        h1 {
            color: #1e1e2e;
            font-family: 'Helvetica Neue', sans-serif;
            font-weight: 800;
        }
        .stDataFrame {
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        }
        /* Progress bar color */
        .stProgress > div > div > div > div {
            background-color: #007bff;
        }
        </style>
    """, unsafe_allow_html=True)
