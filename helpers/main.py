import streamlit as st
import os
import pandas as pd
from helpers.upload import render_upload_page
from helpers.api import render_api_page
from helpers.agent_page import render_agent_page
from dotenv import load_dotenv

load_dotenv()

def render_main_page():
    # Set the title that appears at the top of the page.
    st.image("images/enrich_logo.png")
    '''
    # :earth_americas: Enrich Revenue Dashboard
    '''

    reportTab, agentTab, apiTab = st.tabs(["Report", "AI Analysis", "API"])
    with reportTab:
        render_upload_page()
    with agentTab:
        render_agent_page()
    with apiTab:
        render_api_page()