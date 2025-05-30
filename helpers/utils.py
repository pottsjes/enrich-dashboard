import streamlit as st
import pandas as pd
import os
import plotly.graph_objects as go
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
    REQUIRED_COLUMNS,
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
        make_comparison_chart("Total Occupancy", "Current", row[KEY_PAID_OCCUPANCY], "STLY", row[KEY_PAID_OCCUPANCY_STLY], percent=True),
        make_comparison_chart("Market Occupancy", "Current", row[KEY_MARKET_OCCUPANCY], "STLY", row[KEY_MARKET_OCCUPANCY_STLY], percent=True), 
        make_comparison_chart("Total Revenue", "Current", row[KEY_TOTAL_REVENUE], "STLY", row[KEY_TOTAL_REVENUE_STLY]),
        make_comparison_chart("RevPAR", "Current", row[KEY_RENTAL_REVPAR], "Market", row[KEY_MARKET_REVPAR])
    ]

@st.dialog("Data Validation")
def validate_data(df: pd.DataFrame) -> bool:
    if df.empty:
        st.write("DataFrame is empty. Please upload a valid file.")
        return False
    missing = get_missing_columns(df)
    if missing:
        st.markdown("**Missing required columns:**\n" + "\n".join(f"- `{col}`" for col in missing))
        return False
    if not all(df[col].dtype in [float, int] for col in REQUIRED_COLUMNS if col in df.columns):
        st.write("One or more required columns have incorrect data types.")
        return False
    return True

def get_missing_columns(df: pd.DataFrame) -> list:
    return set(REQUIRED_COLUMNS) - set(df.columns)
