import streamlit as st
import pandas as pd
import os
import base64
from jinja2 import Template
import plotly.graph_objects as go
import glob
from constants.constants import (
    KEY_LISTING_NAME,
    KEY_REVPAR_INDEX,
    KEY_REVPAR_INDEX_STLY,
    KEY_REVPAR_STLY,
    KEY_MARKET_REVPAR_STLY,
    KEY_MARKET_PEN,
    KEY_MARKET_PEN_STLY,
    KEY_PAID_OCCUPANCY_STLY,
    KEY_MARKET_OCCUPANCY_STLY,
    KEY_ADR_INDEX_STLY,
    KEY_ADR_STLY,
    KEY_MARKET_ADR_STLY,
    KEY_LABELS,
    KEY_REVPAR_INDEX,
    KEY_MARKET_PEN,
    KEY_REVPAR_INDEX_STLY,
    KEY_MARKET_PEN_STLY,
    KEY_ADR_INDEX_STLY,
    KEY_ADR_STLY,
    KEY_MARKET_ADR_STLY,
    KEY_MARKET_REVPAR_STLY,
    KEY_PAID_OCCUPANCY_STLY,
    KEY_MARKET_OCCUPANCY_STLY,
    KEY_ADR_STLY,
    customers
)


def get_diff_percent_bar(df: pd.DataFrame, x: str, y: str, title: str, yaxis_title: str, base: int):
    df = df.sort_values(by=[y], ignore_index=True)
    x_vals = df[x]
    y_vals = df[y] - base  # offset from base
    base_vals = [1] * len(df)

    # Build the custom bar chart
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=x_vals,
        y=y_vals,
        base=base_vals,
        marker_color=["green" if y > 0 else ("red" if y > -1 else "gray") for y in y_vals],
        hovertext=df[KEY_LISTING_NAME],
        hoverinfo="text+y"
    ))

    fig.update_layout(
        yaxis_title=yaxis_title,
        yaxis=dict(
            zeroline=False,
            showgrid=True
        ),
        title=title,
        shapes=[
            dict(
                type="line",
                x0=-0.5,
                x1=len(df) - 0.5,
                y0=base,
                y1=base,
                line=dict(color="black", dash="dash", width=1)
            )
        ],
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white")
    )
    return fig

def render_upload_page():
    # Set the title that appears at the top of the page.
    st.image("images/enrich_logo.png")
    '''
    # :earth_americas: Enrich Revenue Dashboard
    '''

    # Add some spacing
    ''
    ''
    # Add a form for customer selection and file upload
    with st.form(key="customer_file_form"):
        selected_customer = st.selectbox(
            'Which customer is this report for?',
            customers,
            help="Select a customer from the dropdown."
        )
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
        uploaded_file = st.file_uploader(
            "Upload a file", 
            type=["csv", "xlsx"], 
            help="Upload a CSV or Excel file."
        )
        submit_button = st.form_submit_button(label="Generate Report", help="Click to generate the report.")

    # Ensure both fields are filled before proceeding
    if submit_button:
        if not selected_customer:
            st.error("Please select a customer.")
        elif not uploaded_file:
            st.error("Please upload a file.")
        else:
            # Process the uploaded file
            try:
                df = pd.read_csv(uploaded_file)
            except:
                df = pd.read_excel(uploaded_file)

            if df is not None:
                ''
                ''
                
                header1, header2 = st.columns([0.2, 0.7], vertical_alignment="center")
                logo_paths = glob.glob(os.path.join("customer_logos", selected_customer + ".*"))
                logo_path = logo_paths[0]
                header1.image(logo_path)
                header2.write(f"""
                    # Monthly Revenue Report
                    ### {selected_customer} - {month} {year}
                    """
                )

                # Calculations
                df[KEY_REVPAR_INDEX] = df[KEY_REVPAR_INDEX] / 100
                df[KEY_MARKET_PEN] = df[KEY_MARKET_PEN] / 100
                df[KEY_REVPAR_INDEX_STLY] = df[KEY_REVPAR_STLY] / df[KEY_MARKET_REVPAR_STLY]
                df[KEY_MARKET_PEN_STLY] = df[KEY_PAID_OCCUPANCY_STLY] / df[KEY_MARKET_OCCUPANCY_STLY]
                df[KEY_ADR_INDEX_STLY] = df[KEY_ADR_STLY] / df[KEY_MARKET_ADR_STLY]

                # Create Charts
                first1, first2 = st.columns(2)
                df[KEY_LABELS] = df[KEY_LISTING_NAME].str[:20] + "..."
                rpi_thisPeriod = get_diff_percent_bar(df, KEY_LABELS, KEY_REVPAR_INDEX, "RevPAR Index this Period", "RevPAR Index", 1)
                first1.plotly_chart(rpi_thisPeriod, use_container_width=True)
                rpi_stly = get_diff_percent_bar(df, KEY_LABELS, KEY_REVPAR_INDEX_STLY, "RevPar Index STLY", "RevPar Index", 1)
                first2.plotly_chart(rpi_stly, use_container_width=True)

                second1, second2 = st.columns(2)
                mpi_thisPeriod = get_diff_percent_bar(df, KEY_LABELS, KEY_MARKET_PEN, "Market Penetration Index", "MPI", 1)
                second1.plotly_chart(mpi_thisPeriod, use_container_width=True)
                mpi_stly = get_diff_percent_bar(df, KEY_LABELS, KEY_MARKET_PEN_STLY, "Market Penetration Index STLY", "MPI", 1)
                second2.plotly_chart(mpi_stly, use_container_width=True)

                # HTML template with placeholders
                html_template = """
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <title>Monthly Revenue Report</title>
                    <style>
                        body {
                            font-family: Arial, sans-serif;
                            padding: 40px;
                            color: white;
                        }

                        .header {
                            display: flex;
                            align-items: center;
                            margin-bottom: 40px;
                        }

                        .logo {
                            height: 120px;
                            margin-right: 30px;
                        }

                        .title-text h1 {
                            margin: 0;
                            font-size: 2.5em;
                        }

                        .title-text h2 {
                            margin: 0;
                            font-weight: normal;
                            font-size: 1.2em;
                        }

                        .chart-row {
                            display: flex;
                            justify-content: space-between;
                            gap: 20px;
                        }

                        .chart {
                            width: 48%;
                        }
                    </style>
                </head>
                <body>
                    <div class="header">
                        <img class="logo" src="{{ logo_url }}">
                        <div class="title-text">
                            <h1>Monthly Revenue Report</h1>
                            <h2>{{ customer }} - {{month}} {{year}}</h2>
                        </div>
                    </div>
                    <div class="chart-row">
                        <div class="chart">{{ chart1 | safe }}</div>
                        <div class="chart">{{ chart2 | safe }}</div>
                    </div>
                    <div class="chart-row">
                        <div class="chart">{{ chart3 | safe }}</div>
                        <div class="chart">{{ chart4 | safe }}</div>
                    </div>
                </body>
                </html>
                """
                with open(logo_path, "rb") as f:
                    logo_b64 = base64.b64encode(f.read()).decode()
                logo_url = f"data:image/png;base64,{logo_b64}"
                # Render the HTML
                template = Template(html_template)
                rendered_html = template.render(
                    logo_url=logo_url,
                    customer=selected_customer,
                    month=month,
                    year=year,
                    chart1=rpi_thisPeriod.to_html(include_plotlyjs="cdn", full_html=False),
                    chart2=rpi_stly.to_html(include_plotlyjs="cdn", full_html=False),
                    chart3=mpi_thisPeriod.to_html(include_plotlyjs="cdn", full_html=False),
                    chart4=mpi_stly.to_html(include_plotlyjs="cdn", full_html=False)
                )
                ''
                ''

                @st.fragment
                def export_report():
                    # Add a button for exporting the report
                    if st.button("Export Report"):
                        # Ensure the "reports" folder exists
                        reports_folder = "reports"
                        os.makedirs(reports_folder, exist_ok=True)

                        # Save the HTML file to the "reports" folder
                        first_name, last_name = selected_customer.split()
                        file_name = f"{first_name.lower()}_{last_name.lower()}_{pd.Timestamp(month + ' 1, ' + year).strftime('%m%Y')}.html"
                        file_path = os.path.join(reports_folder, file_name)

                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(rendered_html)

                        # Redirect the user to the new page with the report
                        st.query_params.page = "report"
                        st.query_params.file_path = file_path
                        st.success(f"Report saved successfully to {file_path}. Redirecting...")
                        st.rerun()

                export_report()