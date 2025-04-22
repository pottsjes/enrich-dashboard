import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import glob
import os
import base64
from jinja2 import Template
import plotly.express as px
import plotly.graph_objects as go
from helpers.report import render_report_page
from helpers.home import render_home_page
from helpers.upload import render_upload_page

# Set the title and favicon that appear in the Browser's tab bar.
st.set_page_config(
    page_title='Enrich Revenue Dashboard',
    page_icon=':earth_americas:', # This is an emoji shortcode. Could be a URL too.
    layout='wide',
)
if not st.query_params.get_all("page"):
    st.query_params.page = "home"

# -----------------------------------------------------------------------------
# Declare some useful functions/constants.

# -----------------------------------------------------------------------------
# Draw the actual page
if st.query_params.page == "report":
    render_report_page()
elif st.query_params.page == "upload":
    render_upload_page()
else:
    render_home_page()