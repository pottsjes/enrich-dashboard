import os
import csv
import io

import pandas as pd
import requests
import streamlit as st

def download_data(fromDate, toDate, lastModified, filterOption):
    params = {
        "apikey": "enrich1234",
        "from": fromDate,
        "to": toDate,
        "lastModified": lastModified,
    }
    apiUrl = "https://api.equisourceholdings.com/api/reservations"

    with st.spinner("Fetching reservations..."):
        try:
            response = requests.get(apiUrl, params=params, timeout=60)
            response.raise_for_status()
        except requests.exceptions.RequestException as exc:
            st.error(f"Error fetching data: {exc}")
        else:
            try:
                payload = response.json()
            except ValueError:
                st.error("The API response was not valid JSON.")
            else:
                st.subheader("API Response")
                if payload:
                    if filterOption:
                        payload = [r for r in payload if r["marketingSource"] == "legacybeachhomes.com"]

                    fieldnames = list(payload[0].keys())
                    csv_buffer = io.StringIO()
                    writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(payload)
                    return csv_buffer.getvalue()
                else:
                    st.error("The API response did not contain expected data.")
        return ""

def render_api_page():
    st.title("API Page")
    
    fromDate = st.text_input(
        "From Date",
        value="2023-11-10",
        placeholder="Enter beginning date for the report (YYYY-MM-DD)",
    )
    toDate = st.text_input(
        "To Date",
        value=(pd.Timestamp.today() + pd.Timedelta(365, 'days')).strftime("%Y-%m-%d"),
        placeholder="Enter ending date for the report (YYYY-MM-DD)",
    )
    lastModified = st.text_input(
        "Last Modified",
        value="2000-01-01T00:00:00.0000000Z",
        placeholder="Enter last modified date for the report (YYYY-MM-DDTHH:MM:SS.SSSSSSSSZ)",
    )
    filterOption = st.checkbox(
        "Filter For LegacyBeachHomes only",
        value=True,
        help="Check this box to filter results to only include LegacyBeachHomes bookings.",
    )

    if download_link(fromDate, toDate, lastModified, filterOption):
        st.success("Report downloaded successfully.")
        

@st.fragment
def download_link(fromDate, toDate, lastModified, filterOption):
    st.download_button(
    label="Download",
    data=download_data(fromDate, toDate, lastModified, filterOption),
    file_name="reservations.csv",
    mime="text/csv",
)