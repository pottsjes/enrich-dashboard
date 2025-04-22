import streamlit as st
import os
import pandas as pd

def render_home_page():
    st.image("images/enrich_logo.png")
    st.title("Welcome to the Enrich Revenue Dashboard")
    st.markdown("Please enter your details to access your report.")

    # Input fields for user details
    first_name = st.text_input("First Name", help="Enter your first name.")
    last_name = st.text_input("Last Name", help="Enter your last name.")

    # Dropdowns for selecting month and year
    month = st.selectbox(
        "Select Month",
        options=[
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]
    )
    year = st.selectbox(
        "Select Year",
        options=[str(y) for y in range(2020, pd.Timestamp.now().year + 1)]
    )
    
    st.fragment
    def export_report():
        # Add a button for exporting the report
        if st.button("Load Report"):
            if not first_name or not last_name:
                st.error("Please enter both your first and last name.")
            else:
                # Generate the expected file name
                formatted_month = pd.Timestamp(month + " 1, " + year).strftime("%m")
                file_name = f"{first_name.lower()}_{last_name.lower()}_{formatted_month}{year}.html"
                file_path = os.path.join("reports", file_name)

                # Check if the report exists
                if os.path.exists(file_path):
                    st.success(f"Report found: {file_name}. Redirecting...")
                    # Redirect the user to the new page with the report
                    st.query_params.page = "report"
                    st.query_params.file_path = file_path
                    st.success(f"Report saved successfully to {file_path}. Redirecting...")
                    st.rerun()
                else:
                    st.error(f"No report found for {first_name} {last_name} in {month} {year}.")

    export_report()