import streamlit as st
import os
import pandas as pd
from helpers.upload import render_upload_page
from helpers.api import render_api_page

def render_main_page():
    # Set the title that appears at the top of the page.
    st.image("images/enrich_logo.png")
    '''
    # :earth_americas: Enrich Revenue Dashboard
    '''

    # Add some spacing
    ''
    ''
    reportTab, apiTab = st.tabs(["Report", "API"])
    with reportTab:
        render_upload_page()
    with apiTab:
        render_api_page()