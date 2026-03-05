import pandas as pd
import streamlit as st
from pathlib import Path
import html
import plotly.express as px

st.set_page_config(
    page_title="AI Apps Hub",
    page_icon="🤖",
    layout="wide",
)

DATA_FILE = Path("Asset Detail.xlsx")
HEADER_ROW_INDEX = 1
FIRST_DATA_ROW_INDEX = 3


def apply_theme() -> None:
    st.markdown(
        """
        <style>
            :root {
                --bg: #f5fbf7;
                --surface: #ffffff;
                --text: #1f2937;
                --muted: #4b5563;
                --green-700: #15803d;
                --green-600: #16a34a;
                --green-100: #dcfce7;
                --line: #d1e7d8;
            }

            .stApp {
                background: radial-gradient(circle at top right, #e9f9ef 0%, var(--bg) 45%, #f9fdfb 100%);
                color: var(--text);
            }

            .block-container { padding-top: 1.5rem; }
            h1, h2, h3 { color: var(--green-700) !important; }
            p, label, .stCaption { color: var(--muted) !important; }

            header[data-testid="stHeader"] {
                background: linear-gradient(90deg, #14532d 0%, #15803d 45%, #16a34a 100%) !important;
                border-bottom: 1px solid #166534;
                box-shadow: 0 6px 16px rgba(20, 83, 45, 0.28);
            }
            header[data-testid="stHeader"] * {
                color: #ecfdf5 !important;
            }
            button[kind="header"] {
                background: rgba(236, 253, 245, 0.16) !important;
                border: 1px solid rgba(236, 253, 245, 0.35) !important;
                border-radius: 8px !important;
            }
            button[kind="header"]:hover {
                background: rgba(236, 253, 245, 0.28) !important;
            }
            .company-banner {
                background: linear-gradient(90deg, #166534 0%, #16a34a 100%);
                color: #ffffff;
                border-radius: 14px;
                padding: 18px 22px;
                margin-bottom: 1rem;
                box-shadow: 0 6px 18px rgba(21, 128, 61, 0.2);
            }
            .company-banner h2 {
                color: #ffffff !important;
                margin: 0;
                font-size: 1.5rem;
                letter-spacing: 0.3px;
            }
            .company-banner p {
                color: #ecfdf5 !important;
                margin: 0.35rem 0 0 0;
                font-size: 0.95rem;
            }

            div[data-testid="stMetric"] {
                background: var(--surface);
                border: 1px solid var(--line);
                border-radius: 12px;
                padding: 0.75rem;
                box-shadow: 0 2px 10px rgba(21, 128, 61, 0.06);
            }

            div[data-testid="stMetricLabel"] { color: var(--green-700); font-weight: 600; }
            div[data-testid="stMetricValue"] { color: var(--green-700) !important; }
            div[data-testid="stMetricValue"] > div { color: var(--green-700) !important; }

            .stButton button {
                background: var(--green-600);
                color: #fff;
                border: 1px solid var(--green-600);
                border-radius: 8px;
                font-weight: 600;
            }
            .stButton button:hover {
                background: #15803d;
                border-color: #15803d;
            }

            .stTextInput input {
                background: var(--surface);
                border: 1px solid var(--line);
                border-radius: 8px;
            }

            .asset-table table {
                width: 100%;
                border-collapse: collapse;
                background: var(--surface);
                border: 1px solid var(--line);
                border-radius: 10px;
                overflow: hidden;
            }
            .asset-table thead th {
                background: var(--green-100);
                color: var(--green-700);
                border-bottom: 1px solid var(--line);
                text-align: left;
                font-weight: 700;
                padding: 10px 12px;
            }
            .asset-table td {
                border-bottom: 1px solid #e7f3eb;
                color: var(--text);
                padding: 10px 12px;
                vertical-align: top;
            }
            .asset-table tr:hover td {
                background: #f0fbf4;
            }
            .asset-table a {
                color: var(--green-700);
                text-decoration: none;
                font-weight: 600;
            }
            .asset-table a:hover { text-decoration: underline; }

            div[data-testid="stPlotlyChart"],
            .stPlotlyChart {
                background: #ffffff;
                border: 2px solid #1f2937 !important;
                border-radius: 10px;
                padding: 0.5rem;
                box-sizing: border-box;
                overflow: hidden;
            }
            div[data-testid="stPlotlyChart"] > div,
            .stPlotlyChart > div {
                border-radius: 8px;
                overflow: hidden;
            }

            .detail-card {
                background: var(--surface);
                border: 1px solid var(--line);
                border-radius: 10px;
                padding: 0.85rem 1rem;
                margin-bottom: 0.8rem;
                box-shadow: 0 2px 10px rgba(21, 128, 61, 0.04);
            }
            .detail-card h4 {
                color: var(--green-700);
                margin: 0 0 0.35rem 0;
                font-size: 0.98rem;
            }
            .detail-card p {
                margin: 0;
                color: var(--text);
                line-height: 1.45;
            }

            .section-title {
                margin-top: 1.1rem;
                margin-bottom: 0.45rem;
                color: var(--green-700);
                font-weight: 700;
                font-size: 1.05rem;
            }

            .newsletter-hero {
                background: linear-gradient(120deg, #ecfdf3 0%, #d1fae5 45%, #bbf7d0 100%);
                border: 1px solid #a7f3d0;
                border-radius: 14px;
                padding: 1rem 1.1rem;
                box-shadow: 0 6px 16px rgba(21, 128, 61, 0.08);
            }
            .newsletter-kicker {
                margin: 0 0 0.25rem 0;
                color: #166534 !important;
                font-weight: 700;
                font-size: 0.78rem;
                text-transform: uppercase;
                letter-spacing: 0.08em;
            }
            .newsletter-headline {
                margin: 0;
                color: #14532d !important;
                font-size: 1.65rem;
                line-height: 1.2;
            }
            .newsletter-dek {
                margin: 0.5rem 0 0 0;
                color: #14532d !important;
                line-height: 1.5;
            }
            .newsletter-section {
                background: #ffffff;
                border: 1px solid var(--line);
                border-radius: 12px;
                padding: 0.9rem 1rem;
                margin: 0.8rem 0;
            }
            .newsletter-section h3 {
                margin: 0 0 0.4rem 0;
                color: var(--green-700) !important;
                font-size: 1.05rem;
            }
            .newsletter-facts {
                background: #f0fdf4;
                border: 1px solid #bbf7d0;
                border-radius: 12px;
                padding: 0.8rem 0.9rem;
                margin-top: 0.75rem;
            }
            .newsletter-facts p {
                margin: 0.3rem 0;
                color: #14532d !important;
                font-size: 0.95rem;
            }
            .newsletter-link {
                display: inline-block;
                margin-top: 0.55rem;
                background: #16a34a;
                color: #ffffff !important;
                text-decoration: none;
                padding: 0.45rem 0.75rem;
                border-radius: 8px;
                font-weight: 600;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def load_assets() -> pd.DataFrame:
    if not DATA_FILE.exists():
        return pd.DataFrame()

    df = pd.read_excel(
        DATA_FILE,
        sheet_name="External Asset Details",
        header=HEADER_ROW_INDEX,
    )
    df = df.iloc[FIRST_DATA_ROW_INDEX - (HEADER_ROW_INDEX + 1) :].copy()
    df = df.dropna(how="all")
    df.columns = [str(c).strip() for c in df.columns]

    if "Sr. No." not in df.columns:
        df.insert(0, "Sr. No.", range(1, len(df) + 1))
    if "Asset Name" not in df.columns:
        df["Asset Name"] = [f"AI Asset {i}" for i in range(1, len(df) + 1)]

    if len(df) < 6:
        start = len(df) + 1
        dummy_rows = []
        for i in range(start, 7):
            dummy_rows.append(
                {
                    "Sr. No.": i,
                    "Asset Name": f"Demo Assistant {i}",
                    "AI Capabilities": "GenAI, RAG",
                    "Category": "Productivity",
                    "Type of Use": "Internal",
                    "L1 Offering": "Conversational AI",
                    "L2 Offering": "Knowledge Assistant",
                    "L3 Offering": "Search + Summarize",
                    "Short Summary": "AI assistant for business workflows.",
                    "Detailed Description": "Provides document Q&A, summaries, and workflow automation.",
                    "Key Features": "Role-based access, citation support, analytics dashboard",
                    "Additional Information": "Pilot-ready solution",
                    "Demo Link": "https://example.com",
                    "Primary Geo Owner": "US",
                    "Developed By": "AI Platform Team",
                    "Funded/Sponsored By": "Innovation Office",
                }
            )
        if dummy_rows:
            df = pd.concat([df, pd.DataFrame(dummy_rows)], ignore_index=True)

    df["Asset Name"] = df["Asset Name"].fillna("").astype(str).str.strip()
    df["Sr. No."] = (
        pd.to_numeric(df["Sr. No."], errors="coerce")
        .fillna(pd.Series(range(1, len(df) + 1)))
        .astype(int)
    )
    df = df[df["Asset Name"] != ""]
    return df.reset_index(drop=True)


def asset_row_link(row: pd.Series) -> str:
    asset_id = int(row.name)
    return f"/?asset={asset_id}"


def build_distribution(df: pd.DataFrame, column: str, split_csv: bool = False) -> pd.DataFrame:
    if column not in df.columns:
        return pd.DataFrame(columns=["label", "count"])

    series = df[column].fillna("").astype(str).str.strip()
    series = series[series != ""]
    if series.empty:
        return pd.DataFrame(columns=["label", "count"])

    if split_csv:
        series = series.str.split(",").explode().str.strip()
        series = series[series != ""]

    counts = series.value_counts().head(8).reset_index()
    counts.columns = ["label", "count"]
    return counts


def draw_pie_chart(data: pd.DataFrame, title: str) -> None:
    if data.empty:
        st.info(f"No data for {title.lower()}.")
        return

    fig = px.pie(
        data_frame=data,
        names="label",
        values="count",
        hole=0.45,
        color="label",
        color_discrete_sequence=[
            "#166534",
            "#15803d",
            "#16a34a",
            "#22c55e",
            "#4ade80",
            "#86efac",
            "#bbf7d0",
            "#dcfce7",
        ],
    )
    fig.update_layout(
        height=280,
        margin=dict(l=8, r=8, t=8, b=8),
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        autosize = True,
        legend=dict(
            title=dict(text=title, font=dict(color="#000000")),
            font=dict(color="#000000"),
        ),
        font=dict(color="#000000"),
    )
    fig.update_traces(
                        textinfo="percent",
                        textfont=dict(color="#000000"),
                        domain = dict(x=[0.0,1], y=[0.1,1]),)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def render_analytics(df: pd.DataFrame) -> None:
    st.markdown('<div class="section-title">Portfolio Analytics</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)

    with c1:
        st.caption("AI Capability Mix")
        draw_pie_chart(build_distribution(df, "AI Capabilities", split_csv=True), "Capability")
    with c2:
        st.caption("Type of Use")
        draw_pie_chart(build_distribution(df, "Type of Use"), "Type of Use")
    with c3:
        st.caption("Category Spread")
        draw_pie_chart(build_distribution(df, "Category"), "Category")


def render_home(df: pd.DataFrame) -> None:
    apply_theme()
    st.markdown(
        """
        <div class="company-banner">
            <h2>XYZ</h2>
            <p>Enterprise AI Apps Portfolio Dashboard</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.title("AI Apps Hub")
    st.caption("Centralized catalog of AI products and capabilities")

    search = st.text_input("Search assets", placeholder="Type name, capability, or category...")
    view_df = df.copy()
    if search.strip():
        mask = view_df.astype(str).apply(
            lambda col: col.str.contains(search, case=False, na=False)
        ).any(axis=1)
        view_df = view_df[mask]

    if view_df.empty:
        st.info("No assets found for the current filter.")
        return

    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Total Assets", len(df))
    with m2:
        st.metric("Showing", len(view_df))
    with m3:
        st.metric("Categories", view_df["Category"].nunique() if "Category" in view_df.columns else 0)

    render_analytics(view_df)

    st.markdown('<div class="section-title">Asset Directory</div>', unsafe_allow_html=True)
    ordered_cols = [
        c
        for c in [
            "Sr. No.",
            "Asset Name",
            "AI Capabilities",
            "Category",
            "Type of Use",
            "L1 Offering",
            "L2 Offering",
            "L3 Offering",
            "Key Features",
            "Developed By",
        ]
        if c in view_df.columns
    ]

    table_df = view_df[ordered_cols].copy().fillna("")
    table_df["Asset Name"] = view_df.apply(
        lambda row: f'<a href="{asset_row_link(row)}">{row["Asset Name"]}</a>', axis=1
    )

    st.markdown(
        f'<div class="asset-table">{table_df.to_html(index=False, escape=False)}</div>',
        unsafe_allow_html=True,
    )


def render_asset_detail(df: pd.DataFrame, asset_id: int) -> None:
    apply_theme()
    if asset_id < 0 or asset_id >= len(df):
        st.error("Asset not found.")
        if st.button("Back to homepage"):
            st.query_params.clear()
        return

    row = df.iloc[asset_id]
    asset_name = str(row.get("Asset Name", "Asset Detail"))
    st.title(asset_name)
    st.caption("Newsletter profile")

    if st.button("Back to homepage", type="secondary"):
        st.query_params.clear()
        st.rerun()

    def val(field: str) -> str:
        if field not in df.columns:
            return ""
        raw = row.get(field, "")
        if pd.isna(raw):
            return ""
        return str(raw).strip()

    short_summary = val("Short Summary")
    detailed = val("Detailed Description")
    capabilities = val("AI Capabilities")
    category = val("Category")
    use_type = val("Type of Use")
    l1 = val("L1 Offering")
    l2 = val("L2 Offering")
    l3 = val("L3 Offering")
    features = val("Key Features")
    additional = val("Additional Information")
    geo = val("Primary Geo Owner")
    developed_by = val("Developed By")
    funded_by = val("Funded/Sponsored By")
    demo_link = val("Demo Link")

    hero_image = f"https://picsum.photos/1200/420?random={100 + asset_id}"
    inline_image_1 = f"https://picsum.photos/1000/330?random={200 + asset_id}"
    inline_image_2 = f"https://picsum.photos/1000/330?random={300 + asset_id}"

    hero_left, hero_right = st.columns([1.45, 1], vertical_alignment="top")
    with hero_left:
        st.markdown(
            f"""
            <div class="newsletter-hero">
                <p class="newsletter-kicker">AI Portfolio Newsletter</p>
                <h2 class="newsletter-headline">{html.escape(asset_name)}</h2>
                <p class="newsletter-dek">{html.escape(short_summary or "A featured enterprise AI product delivering measurable business value.")}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            f"""
            <div class="newsletter-facts">
                <p><b>Category:</b> {html.escape(category or "Not specified")}</p>
                <p><b>Type of Use:</b> {html.escape(use_type or "Not specified")}</p>
                <p><b>Primary Geo Owner:</b> {html.escape(geo or "Not specified")}</p>
                <p><b>Developed By:</b> {html.escape(developed_by or "Not specified")}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with hero_right:
        st.image(hero_image, caption="Featured newsletter visual", use_container_width=True)

    st.image(inline_image_1, caption="Inside look", use_container_width=True)

    main_col, side_col = st.columns([1.8, 1], vertical_alignment="top")
    with main_col:
        st.markdown(
            f"""
            <div class="newsletter-section">
                <h3>Executive Summary</h3>
                <p>{html.escape(detailed or short_summary or "Detailed description is not available yet.")}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            f"""
            <div class="newsletter-section">
                <h3>Capability Spotlight</h3>
                <p><b>AI Capabilities:</b> {html.escape(capabilities or "Not specified")}</p>
                <p><b>Offering Stack:</b> {html.escape(", ".join([x for x in [l1, l2, l3] if x]) or "Not specified")}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with side_col:
        feature_items = [item.strip() for item in features.split(",") if item.strip()]
        if feature_items:
            feature_list = "".join(f"<li>{html.escape(item)}</li>" for item in feature_items[:7])
            st.markdown(
                f"""
                <div class="newsletter-section">
                    <h3>Key Features</h3>
                    <ul>{feature_list}</ul>
                </div>
                """,
                unsafe_allow_html=True,
            )
        if additional:
            st.markdown(
                f"""
                <div class="newsletter-section">
                    <h3>Additional Notes</h3>
                    <p>{html.escape(additional)}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        if funded_by:
            st.markdown(
                f"""
                <div class="newsletter-section">
                    <h3>Sponsorship</h3>
                    <p>{html.escape(funded_by)}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.image(inline_image_2, caption="Innovation snapshot", use_container_width=True)

    if demo_link:
        st.markdown(
            f"""
            <div class="newsletter-section">
                <h3>Try the Demo</h3>
                <p>Explore the live experience and product flow.</p>
                <a class="newsletter-link" href="{html.escape(demo_link)}" target="_blank">Open Demo Link</a>
            </div>
            """,
            unsafe_allow_html=True,
        )


def main() -> None:
    df = load_assets()
    if df.empty:
        st.error("No data available. Please check Asset Detail.xlsx")
        return

    asset_param = st.query_params.get("asset")
    if asset_param is not None:
        try:
            render_asset_detail(df, int(asset_param))
        except ValueError:
            st.error("Invalid asset selected.")
    else:
        render_home(df)


if __name__ == "__main__":
    main()
