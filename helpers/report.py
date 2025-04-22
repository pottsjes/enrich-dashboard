import streamlit as st
import os
import streamlit.components.v1 as components

def render_report_page():
    file_path = st.query_params.file_path
    if file_path and os.path.exists(file_path):
        # Display the saved report
        with open(file_path, "r", encoding="utf-8") as f:
            report_html = f.read()
        components.html(report_html, height=1200, scrolling=True)
    else:
        st.error("Report file not found.")