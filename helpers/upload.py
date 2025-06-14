from io import BytesIO
import math
import streamlit as st
import pandas as pd
import plotly.io as pio
from PIL import Image
from fpdf import FPDF
from constants.constants import (
    KEY_LISTING_NAME,
    KEY_REVPAR_INDEX,
    KEY_REVPAR_INDEX_STLY,
    KEY_RENTAL_REVPAR,
    KEY_RENTAL_REVPAR_STLY,
    KEY_MARKET_REVPAR,
    KEY_MARKET_REVPAR_STLY,
    KEY_MARKET_PEN,
    KEY_MARKET_PEN_STLY,
    KEY_PAID_OCCUPANCY,
    KEY_PAID_OCCUPANCY_STLY,
    KEY_PAID_OCCUPANCY,
    KEY_PAID_OCCUPANCY_STLY,
    KEY_MARKET_OCCUPANCY,
    KEY_MARKET_OCCUPANCY_STLY,
    KEY_TOTAL_REVENUE,
    KEY_TOTAL_REVENUE_STLY,
    KEY_BOOKED_NIGHTS_PICKUP,
    KEY_LABELS,
    REPORT_HEIGHT,
    REPORT_WIDTH,
    customers
)
from helpers.utils import (
    charts_for_listing,
    get_diff_percent_bar,
    listing_metric_table,
    validate_data
)

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
        # selected_customer = st.selectbox(
        #     'Which customer is this report for?',
        #     customers,
        #     help="Select a customer from the dropdown."
        # )
        report_title = st.text_input(
            "Report Title",
            value="",
            placeholder="Enter title for the report",
            help="Enter a title for the report. This will be displayed at the top of the report."
        )
        # Dropdowns for selecting month and year
        month = st.selectbox(
            "Select Month",
            help="Select the month for the report.",
            options=[
                "January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December"
            ],
            index=pd.Timestamp.now().month - 1  # Default to current month
        )
        year = st.selectbox(
            "Select Year",
            help="Select the year for the report.",
            options=[str(y) for y in range(2020, pd.Timestamp.now().year + 1)],
            index=pd.Timestamp.now().year - 2020  # Default to current year
        )
        uploaded_file = st.file_uploader(
            "Upload a file", 
            type=["csv", "xlsx"], 
            help="Upload a CSV or Excel file."
        )
        uploaded_logo = st.file_uploader(
            "Upload a logo", 
            type=["png", "jpg", "jpeg"], 
            help="Upload a PNG or JPEG file."
        )
        selected_color = st.color_picker(
            "Select a color for the report header",
            value="#d4cfcf",  # Default muted beige color
            help="Choose a color for the report header background."
        )
        # uploaded_file = "data/new_data.xlsx"  # For testing purposes
        submit_button = st.form_submit_button(label="Generate Report", help="Click to generate the report.")

    if submit_button:
        if not uploaded_file:
            st.error("Please upload a file.")
        else:
            #Process the uploaded file
            try:
                df = pd.read_csv(uploaded_file)
            except:
                df = pd.read_excel(uploaded_file)

            df = pd.concat([df, df, df])
            print(f"DataFrame shape: {df.shape}")

            if validate_data(df):
                # Calculations
                if uploaded_logo:
                    logo_image = Image.open(uploaded_logo)
                    logo_width, logo_height = logo_image.size
                    logo_height = logo_height * (25 / logo_width)  # Scale height to fit in the header
                df[KEY_REVPAR_INDEX] = df[KEY_REVPAR_INDEX] / 100
                df[KEY_MARKET_PEN] = df[KEY_MARKET_PEN] / 100
                df[KEY_REVPAR_INDEX_STLY] = df[KEY_RENTAL_REVPAR_STLY] / df[KEY_MARKET_REVPAR_STLY]
                df[KEY_MARKET_PEN_STLY] = df[KEY_PAID_OCCUPANCY_STLY] / df[KEY_MARKET_OCCUPANCY_STLY]

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
                def create_table_page(current_metric, stly_metric, title, data_chunk):
                    pdf.add_page()
                    pdf.set_fill_color(selected_color)  # muted beige background
                    pdf.rect(0, 0, REPORT_WIDTH, 35, style='F')
                    pdf.set_font("Arial", size=30)
                    pdf.set_xy(15, 8)
                    pdf.cell(267, 20, txt=f"{month} {year} - {report_title}", ln=True, align="C")
                    if uploaded_logo:
                        pdf.image(uploaded_logo, x=15, y=5 + ((25 - logo_height)/2), w=25)
                    table = listing_metric_table(data_chunk, current_metric, stly_metric, title)
                    add_img(pdf, table, x=25, y=40, h=165)

                metrics = [
                    (KEY_REVPAR_INDEX, KEY_REVPAR_INDEX_STLY, "RevPAR Index"),
                    (KEY_MARKET_PEN, KEY_MARKET_PEN_STLY, "Market Penetration Index"),
                ]

                def chunk_df(df, max_chunk_size):
                    n = len(df)
                    # Number of chunks needed (never exceeding max_chunk_size per chunk)
                    num_chunks = math.ceil(n / max_chunk_size)
                    # Compute actual chunk size (may be less than max_chunk_size)
                    base_chunk_size = n // num_chunks
                    extras = n % num_chunks  # How many chunks will get an extra row

                    start = 0
                    for i in range(num_chunks):
                        # Distribute the remainder among the first 'extras' chunks
                        chunk_size = base_chunk_size + (1 if i < extras else 0)
                        yield df.iloc[start:start + chunk_size]
                        start += chunk_size

                for current_metric, stly_metric, title in metrics:
                    for chunk in chunk_df(df, 25):
                        create_table_page(current_metric, stly_metric, title, chunk)
                
                # Create individual listing pages
                for i, row in df.iterrows():
                    # if i > 3:
                    #     break
                    # print(f"{i + 1}")
                    listing_name = row[KEY_LISTING_NAME]
                    pdf.add_page()
                    # Header
                    pdf.set_fill_color(selected_color)  # muted beige background
                    pdf.rect(0, 0, REPORT_WIDTH, 35, style='F')
                    pdf.set_xy(15, 8)
                    title_font_size = 20 * min(1, (65/len(listing_name)))
                    pdf.set_font("Arial", "B", title_font_size)
                    pdf.set_text_color(0, 0, 0)
                    pdf.cell(240, 10, listing_name, ln=True)
                    pdf.set_xy(15, 18)
                    pdf.set_font("Arial", "", 12)
                    pdf.cell(0, 10, f"{month} {year} Report", ln=False)
                    # Logo
                    if uploaded_logo:
                        pdf.image(uploaded_logo, x=257, y=5 + ((25 - logo_height)/2), w=25)
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

                    for i, fig in enumerate(charts_for_listing(row)):
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