import base64
from io import BytesIO
import streamlit as st
import pandas as pd
import os
import plotly.graph_objects as go
import plotly.io as pio
from fpdf import FPDF
import glob
from constants.constants import (
    KEY_LISTING_NAME,
    KEY_REVPAR_INDEX,
    KEY_REVPAR_INDEX_STLY,
    KEY_TOTAL_REVPAR,
    KEY_TOTAL_REVPAR_STLY,
    KEY_MARKET_REVPAR,
    KEY_MARKET_REVPAR_STLY,
    KEY_MARKET_PEN,
    KEY_MARKET_PEN_STLY,
    KEY_PAID_OCCUPANCY,
    KEY_PAID_OCCUPANCY_STLY,
    KEY_OCCUPANCY,
    KEY_OCCUPANCY_STLY,
    KEY_MARKET_OCCUPANCY,
    KEY_MARKET_OCCUPANCY_STLY,
    KEY_ADR_INDEX_STLY,
    KEY_TOTAL_ADR,
    KEY_TOTAL_ADR_STLY,
    KEY_MARKET_ADR,
    KEY_MARKET_ADR_STLY,
    KEY_TOTAL_REVENUE,
    KEY_TOTAL_REVENUE_STLY,
    KEY_BOOKED_NIGHTS_PICKUP,
    KEY_LABELS,
    REPORT_HEIGHT,
    REPORT_WIDTH,
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
        xaxis=dict(
            tickangle=45,
            showticklabels=True
        ),
        title=title,
        title_font_size=30,
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
        font=dict(color="black")
    )
    return fig

def listing_metric_table(df, metric_current, metric_stly, title, base=1.0):
    #sort values in reverse
    df = df.sort_values(by=[metric_current], ignore_index=True, ascending=False)
    df = df[(df[metric_current] != 0.0) | (df[metric_stly] != 0.0)].reset_index(drop=True)
    font_size = 20 * min(20/ len(df), 1)
    
    fig = go.Figure()
    for i, row in df.iterrows():
        y = -i * 2
        name = row["Listing Name"]
        curr_val = row[metric_current]
        stly_val = row[metric_stly]

        # Listing name on left
        fig.add_shape(
            type="rect",
            x0=0,
            x1=7,
            y0=y - 1,
            y1=y + 1,
            fillcolor="rgba(100,155,200,0.15)" if (i%2) == 0 else "white",
            line=dict(width=0),
            layer="below",
        )
        fig.add_trace(go.Scatter(
            x=[3],
            y=[y],
            text=[name],
            mode="text",
            textfont=dict(size=font_size, color="black"),
            textposition="middle left",
            showlegend=False
        ))

        def add_bar(value, y_offset, period_label):
            bar_len = value - base
            value_offset = (bar_len / abs(bar_len)) * 0.1 if bar_len != 0 else 0
            color = "lightgray" if bar_len == -1 else "lightgreen" if bar_len > 0 else "pink"
            x = 5
            # Bar shape
            fig.add_shape(
                type="rect",
                x0=x,
                x1=x + bar_len,
                y0=y + y_offset - 0.3,
                y1=y + y_offset + 0.3,
                fillcolor=color,
                line=dict(width=0),
                layer="below",
            )
            # Bar value label
            fig.add_trace(go.Scatter(
                x=[x + (bar_len + value_offset)],
                y=[y + y_offset],
                text=[f"{value:.2f}" if value != 0.0 else ""],
                mode="text",
                textfont=dict(size=font_size),
                showlegend=False
            ))
            # Period label
            fig.add_trace(go.Scatter(
                x=[x-1.8],
                y=[y + y_offset],
                text=[period_label],
                mode="text",
                textfont=dict(size=font_size),
                textposition="middle right",
                showlegend=False
            ))

        add_bar(curr_val, 0.3, "Current")     # Current metric
        add_bar(stly_val, -0.3, "STLY")   # STLY metric

    fig.update_layout(
        title=dict(text=title, x=0.5),
        title_font_size=50,
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False, range=[0, 7]),
        yaxis=dict(showgrid=False, showticklabels=False, zeroline=False, range=[-len(df)*2 + 1, 1]),
        height=1600,
        width=2400
    )

    return fig


def charts_for_listing(row):
    def make_comparison_chart(title, left_key, left_val, right_key, right_val, percent=False):
        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=[left_val],
            name=left_key,
            marker_color="lightgray",
            text=[f"{left_val:.0f}%" if percent else f"${left_val:.0f}"],
            textposition="auto",
            textfont=dict(size=20)
        ))
        fig.add_trace(go.Bar(
            y=[right_val],
            name=right_key,
            marker_color="black",
            text=[f"{right_val:.0f}%" if percent else f"${right_val:.0f}"],
            textposition="auto",
            textfont=dict(size=20)
        ))
        fig.update_layout(
            title=dict(
                text=title,
                font=dict(size=30),
                x=0.5,  # Center title
                xanchor='center'
            ),
            barmode="group",
            xaxis=dict(showticklabels=False),  # Removes x-axis labels
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=0.96,
                xanchor="right",
                x=1
            ),
            font=dict(color="black"),
            title_font_size=30,
            margin=dict(t=50)
        )
        return fig

    return [
        make_comparison_chart("Total Occupancy", "Current", row[KEY_OCCUPANCY], "STLY", row[KEY_OCCUPANCY_STLY], percent=True),
        make_comparison_chart("Marlet Occupancy", "Current", row[KEY_MARKET_OCCUPANCY], "STLY", row[KEY_MARKET_OCCUPANCY_STLY], percent=True), 
        make_comparison_chart("Total Revenue", "Current", row[KEY_TOTAL_REVENUE], "STLY", row[KEY_TOTAL_REVENUE_STLY]),
        make_comparison_chart("RevPAR", "Current", row[KEY_TOTAL_REVPAR], "Market", row[KEY_MARKET_REVPAR])
    ]


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
        uploaded_file = "data/new_data.xlsx"  # For testing purposes
        submit_button = st.form_submit_button(label="Generate Report", help="Click to generate the report.")

    # Ensure both fields are filled before proceeding
    if uploaded_file:
        if not selected_customer:
            st.error("Please select a customer.")
        elif not uploaded_file:
            st.error("Please upload a file.")
        else:
            #Process the uploaded file
            try:
                df = pd.read_csv(uploaded_file)
            except:
                df = pd.read_excel(uploaded_file)

            if df is not None:
                logo_paths = glob.glob(os.path.join("customer_logos", selected_customer + ".*"))
                logo_path = logo_paths[0]

                # Calculations
                df[KEY_REVPAR_INDEX] = df[KEY_REVPAR_INDEX] / 100
                df[KEY_MARKET_PEN] = df[KEY_MARKET_PEN] / 100
                df[KEY_REVPAR_INDEX_STLY] = df[KEY_TOTAL_REVPAR_STLY] / df[KEY_MARKET_REVPAR_STLY]
                df[KEY_MARKET_PEN_STLY] = df[KEY_PAID_OCCUPANCY_STLY] / df[KEY_MARKET_OCCUPANCY_STLY]
                df[KEY_ADR_INDEX_STLY] = df[KEY_TOTAL_ADR_STLY] / df[KEY_MARKET_ADR_STLY]

                # Create Charts
                df[KEY_LABELS] = df[KEY_LISTING_NAME].str[:20] + "..."
                rpi_thisPeriod = get_diff_percent_bar(df, KEY_LABELS, KEY_REVPAR_INDEX, "RevPAR Index this Period", "RevPAR Index", 1)
                rpi_stly = get_diff_percent_bar(df, KEY_LABELS, KEY_REVPAR_INDEX_STLY, "RevPar Index STLY", "RevPar Index", 1)
                mpi_thisPeriod = get_diff_percent_bar(df, KEY_LABELS, KEY_MARKET_PEN, "Market Penetration Index", "MPI", 1)
                mpi_stly = get_diff_percent_bar(df, KEY_LABELS, KEY_MARKET_PEN_STLY, "Market Penetration Index STLY", "MPI", 1)
    
                def add_img(pdf, chart, x, y, w = None, h = None):
                    buffer = BytesIO(pio.to_image(chart, format='png'))
                    buffer.name = f"{chart['layout']['title']['text']}.png".replace(" ", "_")
                    buffer.seek(0)
                    if w:
                        pdf.image(buffer, x=x, y=y, w=w)
                    elif h:
                        pdf.image(buffer, x=x, y=y, h=h)

                charts = [rpi_thisPeriod, rpi_stly, mpi_thisPeriod, mpi_stly]
                # Create a PDF document
                pdf = FPDF(orientation="L")
                pdf.set_auto_page_break(auto=True, margin=15)
                # Create header page
                def create_table_page(current_metric, stly_metric, title):
                    pdf.add_page()
                    pdf.set_fill_color(200, 190, 180)  # muted beige background
                    pdf.rect(0, 0, REPORT_WIDTH, 35, style='F')
                    pdf.set_font("Arial", size=30)
                    pdf.set_xy(15, 8)
                    pdf.cell(267, 20, txt=f"Monthly Revenue Report - {selected_customer} ", ln=True, align="C")
                    pdf.image(logo_path, x=15, y=5, w=25)
                    table = listing_metric_table(df, current_metric, stly_metric, title)
                    add_img(pdf, table, x=25, y=40, h=165)

                # Testing
                create_table_page(KEY_REVPAR_INDEX, KEY_REVPAR_INDEX_STLY, "RevPAR Index")
                create_table_page(KEY_MARKET_PEN, KEY_MARKET_PEN_STLY, "Market Penetration Index")
                
                # Create individual listing pages
                for i, row in df.iterrows():
                    # if i > 3:
                    #     break
                    listing_name = row[KEY_LISTING_NAME]
                    pdf.add_page()
                    # Header
                    pdf.set_fill_color(200, 190, 180)  # muted beige background
                    pdf.rect(0, 0, REPORT_WIDTH, 35, style='F')
                    pdf.set_xy(15, 8)
                    title_font_size = 20 * min(1, (65/len(listing_name)))
                    pdf.set_font("Arial", "B", title_font_size)
                    pdf.set_text_color(0, 0, 0)
                    pdf.cell(240, 10, listing_name, ln=True)
                    pdf.set_xy(15, 18)
                    pdf.set_font("Arial", "", 12)
                    print(f"{i + 1}")
                    pdf.cell(0, 10, f"{month} {year} Report", ln=False)
                    # Logo
                    pdf.image(logo_path, x=257, y=5, w=25)
                    # KPI Boxes
                    pdf.set_font("Arial", "B", 12)
                    pdf.set_text_color(0, 0, 0)
                    box_width = 60
                    box_height = 15
                    box_margin = 15
                    kpi_box_start_y = 57
                    kpi_box_x = 30
                    def draw_kpi(label, value, y, label_font_size):
                        pdf.set_xy(kpi_box_x, y)
                        pdf.set_font("Arial", "", label_font_size)
                        pdf.cell(box_width, box_height, txt=label, ln=True, border=1, align="C")
                        pdf.set_xy(kpi_box_x, y + box_height)
                        pdf.set_font("Arial", "", 16)
                        if not value or value == "0%":
                            value = ''
                        pdf.cell(box_width, box_height, txt=str(value), ln=True, border=1, align="C")

                    draw_kpi(KEY_MARKET_PEN, f"{row[KEY_MARKET_PEN]:.0%}", kpi_box_start_y, 13)
                    draw_kpi(KEY_BOOKED_NIGHTS_PICKUP, row[KEY_BOOKED_NIGHTS_PICKUP], kpi_box_start_y + (box_height*2) + box_margin, 11)
                    draw_kpi(KEY_REVPAR_INDEX, f"{row[KEY_REVPAR_INDEX]:.0%}", kpi_box_start_y + 2*((box_height*2) + box_margin), 15)
                    # Charts
                    chart_y_start = 60
                    chart_x_spacing = 90
                    chart_y_spacing = 60

                    for i, fig in enumerate(charts_for_listing(row)):  # You'd define this to generate or return 4 Plotly charts
                        x = 108 + (i % 2) * chart_x_spacing
                        y = chart_y_start + (i // 2) * chart_y_spacing
                        add_img(pdf, fig, x=x, y=y, w=80)

                # Save the PDF to a BytesIO object
                pdf_output = BytesIO(pdf.output(dest="S"))

                # display pdf in streamlit
                # st.write("### Report Preview")
                # base64_pdf = base64.b64encode(pdf.output(dest="S")).decode("utf-8")
                # pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="700" height="900" type="application/pdf"></iframe>'
                # st.components.v1.html(pdf_display, height=900, width=720)
                
                @st.fragment
                def download_link(object_to_download):
                    st.download_button(
                    label="Download Report",
                    data=pdf_output,
                    file_name="report.pdf",
                    mime="application/pdf",
                )

                if download_link(pdf_output):
                    st.success("Report downloaded successfully.")