import streamlit as st
import pandas as pd
import math
from pathlib import Path
import glob
import os
import base64
from jinja2 import Template
import plotly.express as px
import plotly.graph_objects as go

# Set the title and favicon that appear in the Browser's tab bar.
st.set_page_config(
    page_title='Enrich Revenue Dashboard',
    page_icon=':earth_americas:', # This is an emoji shortcode. Could be a URL too.
    layout='wide',
)

# -----------------------------------------------------------------------------
# Declare some useful functions/constants.

customers = ["Pierce Gainey", "Austin Whitaker"]
KEY_LISTING_NAME = "Listing Name"
KEY_REVPAR_INDEX = "RevPAR Index"
KEY_REVPAR_INDEX_STLY = "RevPAR Index STLY"
KEY_REVPAR_STLY = "RevPAR STLY"
KEY_MARKET_REVPAR_STLY = "Market RevPAR STLY"
KEY_MARKET_PEN = "Market Penetration Index %"
KEY_MARKET_PEN_STLY = "Market Penetration Index STLY"
KEY_PAID_OCCUPANCY_STLY = "Paid Occupancy % STLY"
KEY_MARKET_OCCUPANCY_STLY = "Market Occupancy % STLY"
KEY_REVPAR_STLY_YOY = "RevPAR STLY YoY %"
KEY_TOTAL_REV_YOY = "Total Revenue STLY YoY %"
KEY_OCC_STLY = "Occupancy STLY YoY Difference"
KEY_REVPAR_PICKUP = "RevPAR Pickup"
KEY_ADR_INDEX = "ADR Index"
KEY_ADR_STLY_YOY = "ADR STLY YoY %"
KEY_ADR_INDEX_STLY = "ADR Index STLY"
KEY_ADR_STLY = "ADR STLY"
KEY_MARKET_ADR_STLY = "Market ADR STLY"
KEY_LABELS = "Labels"

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
        ]
    )
    return fig

# -----------------------------------------------------------------------------
# Draw the actual page

# Set the title that appears at the top of the page.
st.image("images/enrich_logo.jpeg")
'''
# :earth_americas: Enrich Revenue Dashboard
'''

# Add some spacing
''
''
uploaded_file = st.file_uploader("Upload a file", type=["csv", "xlsx"])
df = None
if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file)
    except:
        df = pd.read_excel(uploaded_file)
else:
    DATA_FILENAME = Path(__file__).parent/'data/revpar_data.xlsx'
    df = pd.read_excel(DATA_FILENAME)

if df is not None:
    selected_customer = st.selectbox(
    'Which customer is this report for?',
    customers,
    # index=None,
    # placeholder="Select a customer..."
    )
    ''
    ''
    
    header1, header2 = st.columns([0.2, 0.7], vertical_alignment="center")
    logo_paths = glob.glob(os.path.join("customer_logos", selected_customer + ".*"))
    logo_path = logo_paths[0]
    header1.image(logo_path)
    header2.write(f"""
        # Monthly Revenue Report
        ### {selected_customer}
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
                <h2>{{ customer }} </h2>
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
        chart1=rpi_thisPeriod.to_html(include_plotlyjs="cdn", full_html=False),
        chart2=rpi_stly.to_html(include_plotlyjs="cdn", full_html=False),
        chart3=mpi_thisPeriod.to_html(include_plotlyjs="cdn", full_html=False),
        chart4=mpi_stly.to_html(include_plotlyjs="cdn", full_html=False)
    )
    ''
    ''
    download1, download2 = st.columns(2)
    download1.download_button(
        label="Download Report",
        data=rendered_html,
        file_name=selected_customer.replace(" ", "_") + "_revenue_report.html",
        mime="text/html",
        icon=":material/download:"
    )
