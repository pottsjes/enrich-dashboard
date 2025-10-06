import streamlit as st
from helpers.main import render_main_page

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
render_main_page()