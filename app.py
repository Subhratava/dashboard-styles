import pandas as pd
import streamlit as st
from pathlib import Path
import html
import plotly.express as px
import plotly.graph_objects as go
import os
try:
    from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
    try:
        from st_aggrid import GridUpdateMode, DataReturnMode
    except ImportError:
        GridUpdateMode = None
        DataReturnMode = None
except ImportError:
    AgGrid = None
    GridOptionsBuilder = None
    JsCode = None
    GridUpdateMode = None
    DataReturnMode = None
try:
    from streamlit_plotly_events import plotly_events
except ImportError:
    plotly_events = None

st.set_page_config(
    page_title="AI Apps Hub",
    page_icon="🤖",
    layout="wide",
)

DATA_FILE = Path("Asset Detail.xlsx")
CSS_FILE = Path("styles.css")
HEADER_ROW_INDEX = 1
FIRST_DATA_ROW_INDEX = 3


def apply_theme() -> None:
    if CSS_FILE.exists():
        css_text = CSS_FILE.read_text(encoding="utf-8")
        st.markdown(f"<style>{css_text}</style>", unsafe_allow_html=True)


def load_assets(sheet_name: str) -> pd.DataFrame:
    if not DATA_FILE.exists():
        return pd.DataFrame()

    try:
        df = pd.read_excel(
            DATA_FILE,
            sheet_name=sheet_name,
            header=HEADER_ROW_INDEX,
        )
    except Exception:
        return pd.DataFrame()
    df = df.iloc[FIRST_DATA_ROW_INDEX - (HEADER_ROW_INDEX + 1) :].copy()
    df = df.dropna(how="all")
    df.columns = [str(c).strip() for c in df.columns]

    if "Sr. No." not in df.columns:
        df.insert(0, "Sr. No.", range(1, len(df) + 1))
    if "Asset Name" not in df.columns:
        df["Asset Name"] = [f"AI Asset {i}" for i in range(1, len(df) + 1)]

    df["Asset Name"] = df["Asset Name"].fillna("").astype(str).str.strip()
    df["Sr. No."] = (
        pd.to_numeric(df["Sr. No."], errors="coerce")
        .fillna(pd.Series(range(1, len(df) + 1)))
        .astype(int)
    )
    df = df[df["Asset Name"] != ""]
    return df.reset_index(drop=True)


def asset_row_link(row: pd.Series, sheet_name: str) -> str:
    asset_id = int(row.name)
    sheet_key = "internal" if str(sheet_name).strip().casefold().startswith("internal") else "external"
    return f"/?sheet={sheet_key}&asset={asset_id}"


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

    counts = series.value_counts().reset_index()
    counts.columns = ["label", "count"]
    return counts


def draw_count_plot(data: pd.DataFrame, title: str, height: int = 300) -> None:
    if data.empty:
        st.info(f"Data not available for {title.lower()}.")
        return

    fig = px.bar(
        data_frame=data.sort_values("count", ascending=False),
        x="label",
        y="count",
        text="count",
        labels={"label": title, "count": "Assets"},
        color="label",
        color_discrete_sequence=[
            "#1C3D26",
            "#046A38",
            "#26890D",
            "#0DF200",
            "#86BC25",
            "#000000",
            "#222222",
            "#F1F6E4",
        ],
    )
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=8, b=8),
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        autosize=True,
        showlegend=False,
        xaxis_title=title,
        yaxis_title="Assets",
        font=dict(color="#000000"),
    )
    fig.update_traces(
        textposition="outside",
        cliponaxis=False,
    )
    with st.container(border=True):
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def draw_offering_stacked_bar(df: pd.DataFrame, height: int = 600) -> set[object]:
    required_cols = ["L1 Offering", "L2 Offering", "L3 Offering"]
    available_cols = [col for col in required_cols if col in df.columns]
    if "L1 Offering" not in available_cols:
        st.info("Data not available for l1/l2/l3 offering chart.")
        return set()

    def clean_value(raw: object) -> str | None:
        if pd.isna(raw):
            return None
        value = str(raw).strip()
        if not value:
            return None
        if value.casefold() == "all":
            return "ALL"
        return value

    hierarchy_df = df[available_cols].copy()
    hierarchy_df["_row_id"] = df.index
    for col in available_cols:
        hierarchy_df[col] = hierarchy_df[col].apply(clean_value)

    asset_col = (
        df["Asset Name"].fillna("").astype(str).str.strip()
        if "Asset Name" in df.columns
        else pd.Series(["Unknown Asset"] * len(df), index=df.index)
    )
    hierarchy_df["Asset Name"] = asset_col
    hierarchy_df = hierarchy_df[hierarchy_df["Asset Name"] != ""]

    hierarchy_df = hierarchy_df[hierarchy_df["L1 Offering"].notna()].copy()
    if hierarchy_df.empty:
        st.info("Data not available for l1/l2/l3 offering chart.")
        return set()

    # Keep hierarchy valid: L3 should only exist under an L2 node.
    if "L2 Offering" in hierarchy_df.columns and "L3 Offering" in hierarchy_df.columns:
        hierarchy_df.loc[hierarchy_df["L2 Offering"].isna(), "L3 Offering"] = None

    for col in required_cols:
        if col not in hierarchy_df.columns:
            hierarchy_df[col] = None

    node_counts: dict[str, int] = {}
    node_row_ids: dict[str, set[object]] = {}
    node_assets: dict[str, set[str]] = {}
    node_labels: dict[str, str] = {}
    node_parents: dict[str, str] = {}
    node_levels: dict[str, int] = {}

    def upsert_node(
        node_id: str,
        label: str,
        parent_id: str,
        level: int,
        row_id: object,
        asset_name: str,
    ) -> None:
        node_labels[node_id] = label
        node_parents[node_id] = parent_id
        node_levels[node_id] = level
        node_counts[node_id] = node_counts.get(node_id, 0) + 1
        if node_id not in node_row_ids:
            node_row_ids[node_id] = set()
        node_row_ids[node_id].add(row_id)
        if node_id not in node_assets:
            node_assets[node_id] = set()
        node_assets[node_id].add(asset_name)

    for row in hierarchy_df.to_dict("records"):
        l1 = row.get("L1 Offering")
        l2 = row.get("L2 Offering")
        l3 = row.get("L3 Offering")
        row_id = row.get("_row_id")
        asset_name = row.get("Asset Name", "")

        l1_id = f"L1::{l1}"
        upsert_node(l1_id, l1, "", 1, row_id, asset_name)

        if l2:
            l2_id = f"L2::{l1}::{l2}"
            upsert_node(l2_id, l2, l1_id, 2, row_id, asset_name)
            if l3:
                l3_id = f"L3::{l1}::{l2}::{l3}"
                upsert_node(l3_id, l3, l2_id, 3, row_id, asset_name)

    if not node_counts:
        st.info("Data not available for l1/l2/l3 offering chart.")
        return set()

    def format_asset_list(names: set[str], max_items: int = 20) -> str:
        ordered = sorted(n for n in names if n)
        if not ordered:
            return "Not specified"
        shown = ordered[:max_items]
        text = "<br>".join(shown)
        remaining = len(ordered) - len(shown)
        if remaining > 0:
            text = f"{text}<br>... (+{remaining} more)"
        return text

    sorted_ids = sorted(
        node_counts.keys(),
        key=lambda nid: (node_levels[nid], node_labels[nid].casefold(), -node_counts[nid]),
    )

    chart_df = pd.DataFrame(
        {
            "id": sorted_ids,
            "label": [node_labels[nid] for nid in sorted_ids],
            "parent": [node_parents[nid] for nid in sorted_ids],
            "count": [node_counts[nid] for nid in sorted_ids],
            "node_id": sorted_ids,
            "assets_html": [format_asset_list(node_assets[nid]) for nid in sorted_ids],
        }
    )
    chart_df["hover_text"] = chart_df.apply(
        lambda row: f"<b>{row['label']}</b><br>Assets: {int(row['count'])}<br>Asset Names:<br>{row['assets_html']}",
        axis=1,
    )

    fig = go.Figure(
        go.Sunburst(
            ids=chart_df["id"],
            labels=chart_df["label"],
            parents=chart_df["parent"],
            values=chart_df["count"],
            customdata=chart_df[["node_id"]],
            hovertext=chart_df["hover_text"],
            branchvalues="total",
            marker=dict(
                colors=chart_df["count"],
                colorscale=[
                    [0.0, "#86BC25"],
                    [0.5, "#26890D"],
                    [1.0, "#1C3D26"],
                ],
            ),
            insidetextorientation="radial",
            hovertemplate="%{hovertext}<extra></extra>",
        )
    )
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=8, b=8),
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font=dict(color="#000000"),
        coloraxis_showscale=False,
    )
    selected_row_ids: set[object] = set(st.session_state.get("offering_selected_row_ids", []))
    if plotly_events is None:
        with st.container(border=True):
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.info("Install `streamlit-plotly-events` to enable click-to-filter on this chart.")
        return selected_row_ids

    chart_reset_key = int(st.session_state.get("offering_chart_reset_key", 0))
    with st.container(border=True):
        clicked_points = plotly_events(
            fig,
            click_event=True,
            select_event=False,
            hover_event=False,
            override_height=height,
            override_width="100%",
            key=f"offering_drilldown_chart_events_{chart_reset_key}",
        )
    if clicked_points:
        clicked_point = clicked_points[-1]
        node_id = None
        custom = clicked_point.get("customdata")
        if isinstance(custom, list) and custom:
            node_id = custom[0]
        elif isinstance(custom, str):
            node_id = custom
        if not node_id:
            point_number = clicked_point.get("pointNumber")
            if isinstance(point_number, int) and 0 <= point_number < len(sorted_ids):
                node_id = sorted_ids[point_number]
        if node_id in node_row_ids:
            selected_row_ids = set(node_row_ids[node_id])
            st.session_state["offering_selected_row_ids"] = list(selected_row_ids)
            st.session_state["offering_selected_label"] = node_labels.get(node_id, "")

    return selected_row_ids


def draw_access_status_chart(df: pd.DataFrame, height: int = 300) -> None:
    column = "Is X having access"
    if column not in df.columns:
        st.info("Data not available for access status chart.")
        return

    asset_series = (
        df["Asset Name"].fillna("").astype(str).str.strip()
        if "Asset Name" in df.columns
        else pd.Series(["Unknown Asset"] * len(df), index=df.index)
    )
    raw = df[column].fillna("").astype(str).str.strip()
    mapped = raw.str.casefold().map(
        {
            "yes": "Yes",
            "y": "Yes",
            "true": "Yes",
            "1": "Yes",
            "no": "No",
            "n": "No",
            "false": "No",
            "0": "No",
        }
    )
    status_df = pd.DataFrame(
        {
            "status": mapped.fillna(raw),
            "asset_name": asset_series,
        }
    )
    status_df["status"] = status_df["status"].fillna("").astype(str).str.strip()
    status_df["asset_name"] = status_df["asset_name"].replace("", "Unknown Asset")
    status_df = status_df[status_df["status"] != ""]
    if status_df.empty:
        st.info("Data not available for access status chart.")
        return

    counts = status_df.groupby("status", as_index=False).agg(
        count=("status", "size"),
        assets=("asset_name", lambda s: list(dict.fromkeys(s.tolist()))),
    )
    counts["asset_details"] = counts["assets"].apply(
        lambda items: "<br>".join(items[:15]) + (f"<br>... +{len(items) - 15} more" if len(items) > 15 else "")
    )
    counts["sort_key"] = counts["status"].map({"Yes": 0, "No": 1}).fillna(2)
    counts = counts.sort_values(["sort_key", "count"], ascending=[True, False]).drop(columns=["sort_key", "assets"])

    colors = [{"Yes": "#26890D", "No": "#046A38"}.get(s, "#0DF200") for s in counts["status"]]
    fig = go.Figure(
        data=[
            go.Bar(
                x=counts["status"],
                y=counts["count"],
                marker_color=colors,
                text=counts["count"],
                customdata=counts["asset_details"],
                hovertemplate=(
                    "Is X having access: %{x}<br>"
                    "Assets: %{y}<br>"
                    "Asset Names:<br>%{customdata}<extra></extra>"
                ),
            )
        ]
    )
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=8, b=8),
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        showlegend=False,
        xaxis_title="Is X having access",
        yaxis_title="Assets",
        font=dict(color="#000000"),
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    with st.container(border=True):
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def draw_country_geoplot(df: pd.DataFrame, height: int = 420) -> None:
    column = "Primary Geo Owner"
    if column not in df.columns:
        st.info("Data not available for country geoplot.")
        return

    country_df = pd.DataFrame(
        {
            "country_raw": df[column].fillna("").astype(str).str.strip(),
            "asset_name": (
                df["Asset Name"].fillna("").astype(str).str.strip()
                if "Asset Name" in df.columns
                else pd.Series(["Unknown Asset"] * len(df), index=df.index)
            ),
        }
    )
    country_df["asset_name"] = country_df["asset_name"].replace("", "Unknown Asset")
    country_df = country_df[country_df["country_raw"] != ""]
    if country_df.empty:
        st.info("Data not available for country geoplot.")
        return

    try:
        country_df["is_iso3"] = country_df["country_raw"].str.fullmatch(r"[A-Za-z]{3}", na=False)
        country_df["country_key"] = country_df["country_raw"].str.casefold().str.strip()
        country_df["country_display"] = country_df["country_raw"]

        summary = country_df.groupby(["country_key", "is_iso3"], as_index=False).agg(
            country_display=("country_display", lambda s: s.value_counts().idxmax()),
            count=("country_raw", "size"),
            assets=("asset_name", lambda s: list(dict.fromkeys(s.tolist()))),
        )
        summary["asset_details"] = summary["assets"].apply(
            lambda items: "<br>".join(items[:12]) + (f"<br>... +{len(items) - 12} more" if len(items) > 12 else "")
        )

        iso_df = summary[summary["is_iso3"]].copy()
        name_df = summary[~summary["is_iso3"]].copy()
        iso_df["location"] = iso_df["country_display"].str.upper().str.strip()
        name_df["location"] = name_df["country_display"].str.strip()

        if iso_df.empty and name_df.empty:
            st.info("Data not available for country geoplot.")
            return

        max_count = int(summary["count"].max()) if not summary.empty else 1
        sizeref = (2.0 * max_count) / (42**2) if max_count > 0 else 1

        fig = go.Figure()
        if not iso_df.empty:
            fig.add_trace(
                go.Scattergeo(
                    locations=iso_df["location"],
                    locationmode="ISO-3",
                    text=iso_df["country_display"],
                    customdata=iso_df[["count", "asset_details"]].to_numpy(),
                    mode="markers",
                    marker=dict(
                        size=iso_df["count"],
                        sizemode="area",
                        sizeref=sizeref,
                        sizemin=6,
                        color=iso_df["count"],
                        coloraxis="coloraxis",
                        line=dict(color="#86BC25", width=0.8),
                        opacity=0.85,
                    ),
                    hovertemplate=(
                        "Country: %{text}<br>"
                        "Assets: %{customdata[0]}<br>"
                        "Asset Names:<br>%{customdata[1]}<extra></extra>"
                    ),
                    showlegend=False,
                )
            )
        if not name_df.empty:
            fig.add_trace(
                go.Scattergeo(
                    locations=name_df["location"],
                    locationmode="country names",
                    text=name_df["country_display"],
                    customdata=name_df[["count", "asset_details"]].to_numpy(),
                    mode="markers",
                    marker=dict(
                        size=name_df["count"],
                        sizemode="area",
                        sizeref=sizeref,
                        sizemin=6,
                        color=name_df["count"],
                        coloraxis="coloraxis",
                        line=dict(color="#86BC25", width=0.8),
                        opacity=0.85,
                    ),
                    hovertemplate=(
                        "Country: %{text}<br>"
                        "Assets: %{customdata[0]}<br>"
                        "Asset Names:<br>%{customdata[1]}<extra></extra>"
                    ),
                    showlegend=False,
                )
            )

        fig.update_geos(
            showframe=False,
            showcoastlines=True,
            coastlinecolor="#86BC25",
            showland=True,
            landcolor="#F1F6E4",
            countrycolor="#86BC25",
        )
        fig.update_layout(
            height=height,
            margin=dict(l=8, r=8, t=8, b=8),
            paper_bgcolor="#ffffff",
            font=dict(color="#000000"),
            coloraxis=dict(
                colorscale=[
                    [0.0, "#26890D"],
                    [0.5, "#046A38"],
                    [1.0, "#1C3D26"],
                ],
                colorbar=dict(title="Assets"),
            ),
        )
        with st.container(border=True):
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    except Exception:
        st.info("Data not available for country geoplot.")


def render_home(
    df: pd.DataFrame,
    search_query: str,
    total_assets_count: int,
    internal_assets_count: int,
    external_assets_count: int,
    expand_charts: bool,
    selected_sheet: str,
) -> None:
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
    sheet_suffix = "Internal Assets" if str(selected_sheet).strip().casefold().startswith("internal") else "External Assets"
    st.title(f"AI Apps Hub - {sheet_suffix}")
    st.caption("Centralized catalog of AI products and capabilities")
    search_query = st.text_input(
        "Search assets",
        value=search_query,
        placeholder="Type name, capability, or category...",
        key="home_search_query",
    )

    view_df = df.copy()
    if search_query.strip():
        mask = view_df.astype(str).apply(
            lambda col: col.str.contains(search_query, case=False, na=False)
        ).any(axis=1)
        view_df = view_df[mask]

    if view_df.empty:
        st.info("No assets found for the current filter.")
        return

    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Total Assets", total_assets_count)
    with m2:
        st.metric("Internal Assets", internal_assets_count)
    with m3:
        st.metric("External Assets", external_assets_count)
    
    kpi_container = st.container()

    analytics_height = 560 if expand_charts else 400
    st.markdown('<div class="section-title">Portfolio Analytics</div>', unsafe_allow_html=True)
    chart_left = None
    chart_right = None
    analytics_cols = st.columns(3)
    with analytics_cols[0]:
        st.caption("Cross MF Usage Spread")
        chart_left = st.container()
    with analytics_cols[1]:
        st.caption("L1 / L2 / L3 Offering Drilldown")
        selected_row_ids = draw_offering_stacked_bar(view_df, height=analytics_height)
        if selected_row_ids:
            selected_label = str(st.session_state.get("offering_selected_label", "")).strip()
            sunburst_count = int(view_df.index.isin(selected_row_ids).sum())
            if selected_label:
                st.caption(f"Offering chart filter active ({selected_label}): {sunburst_count} asset(s) selected.")
            else:
                st.caption(f"Offering chart filter active: {sunburst_count} asset(s) selected.")
            if st.button("Clear offering filter", key="clear_offering_filter"):
                st.session_state.pop("offering_selected_row_ids", None)
                st.session_state.pop("offering_selected_label", None)
                reset_key = int(st.session_state.get("offering_chart_reset_key", 0)) + 1
                st.session_state["offering_chart_reset_key"] = reset_key
                st.session_state.pop(f"offering_drilldown_chart_events_{reset_key - 1}", None)
                st.rerun()
    with analytics_cols[2]:
        st.caption("Access Status")
        chart_right = st.container()

    sunburst_filtered_df = view_df[view_df.index.isin(selected_row_ids)] if selected_row_ids else view_df

    st.markdown('<div class="section-title">Asset Directory</div>', unsafe_allow_html=True)
    table_base_df = sunburst_filtered_df.loc[:, ~sunburst_filtered_df.columns.duplicated()].copy()
    if table_base_df.empty:
        st.info("No assets available after applying the offering filter.")
        return

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
        if c in table_base_df.columns
    ]
    display_cols = ordered_cols + [c for c in table_base_df.columns if c not in ordered_cols]
    table_df = table_base_df[display_cols].copy().fillna("")
    grid_filtered_df = table_base_df.copy()

    if AgGrid is None or GridOptionsBuilder is None or JsCode is None:
        st.warning("Install `streamlit-aggrid` to enable column-level filtering.")
        st.dataframe(table_df, use_container_width=True, hide_index=True)
    else:
        grid_df = table_df.copy().astype(str).fillna("")
        grid_df["__asset_id"] = table_base_df.index.astype(int)

        gb = GridOptionsBuilder.from_dataframe(grid_df)
        gb.configure_default_column(
            filter="agSetColumnFilter",
            floatingFilter=False,
            sortable=True,
            resizable=True,
            editable=False,
            wrapText=True,
            autoHeight=True,
            filterParams={"suppressMiniFilter": True},
        )
        gb.configure_column("__asset_id", hide=True)
        if "Asset Name" in grid_df.columns:
            sheet_key = (
                "internal"
                if str(selected_sheet).strip().casefold().startswith("internal")
                else "external"
            )
            asset_link_renderer = JsCode(
                f"""
                class AssetLinkRenderer {{
                    init(params) {{
                        const safeName = String(params.value ?? "");
                        const assetId = params.data.__asset_id;
                        this.eGui = document.createElement('a');
                        this.eGui.href = '/?sheet={sheet_key}&asset=' + assetId;
                        this.eGui.target = '_blank';
                        this.eGui.rel = 'noopener noreferrer';
                        this.eGui.textContent = safeName;
                        this.eGui.style.color = '#046A38';
                        this.eGui.style.fontWeight = '600';
                        this.eGui.style.textDecoration = 'none';
                        this.eGui.addEventListener('mouseenter', () => this.eGui.style.textDecoration = 'underline');
                        this.eGui.addEventListener('mouseleave', () => this.eGui.style.textDecoration = 'none');
                    }}
                    getGui() {{
                        return this.eGui;
                    }}
                }}
                """
            )
            gb.configure_column("Asset Name", cellRenderer=asset_link_renderer)

        grid_options = gb.build()
        grid_options["domLayout"] = "normal"

        grid_kwargs = dict(
            gridOptions=grid_options,
            fit_columns_on_grid_load=False,
            allow_unsafe_jscode=True,
            enable_enterprise_modules=True,
            height=360 if len(grid_df) > 5 else None,
            theme="streamlit",
            update_on=["filterChanged", "sortChanged", "modelUpdated", "selectionChanged"],
        )
        grid_kwargs["update_mode"] = (
            GridUpdateMode.MODEL_CHANGED if GridUpdateMode is not None else "MODEL_CHANGED"
        )
        grid_kwargs["data_return_mode"] = (
            DataReturnMode.FILTERED_AND_SORTED
            if DataReturnMode is not None
            else "FILTERED_AND_SORTED"
        )
        grid_response = AgGrid(grid_df, **grid_kwargs)
        filtered_data = None
        if isinstance(grid_response, dict):
            filtered_data = grid_response.get("data")
        elif hasattr(grid_response, "data"):
            filtered_data = getattr(grid_response, "data")

        filtered_df = None
        if isinstance(filtered_data, pd.DataFrame):
            filtered_df = filtered_data
        elif isinstance(filtered_data, list):
            filtered_df = pd.DataFrame(filtered_data)
        elif isinstance(filtered_data, dict):
            try:
                filtered_df = pd.DataFrame(filtered_data)
            except Exception:
                filtered_df = None

        if isinstance(filtered_df, pd.DataFrame) and "__asset_id" in filtered_df.columns:
            filtered_ids = (
                pd.to_numeric(filtered_df["__asset_id"], errors="coerce")
                .dropna()
                .astype(int)
                .tolist()
            )
            grid_filtered_df = table_base_df[table_base_df.index.isin(filtered_ids)].copy()

    
    with kpi_container:
        k1, k2, k3 = st.columns(3)
        with k1:
            ai_enable_count = 0
            if "AI Capabilities" in grid_filtered_df.columns:
                ai_enable_series = grid_filtered_df["AI Capabilities"].fillna("").astype(str).str.strip().str.casefold()
                ai_enable_count = int(ai_enable_series.eq("yes").sum())
            st.metric("AI Enabled", ai_enable_count)
        with k2:
            st.metric("Showing", len(grid_filtered_df))
        with k3:
            icc_utilization_count = 0
            if {"AI Capabilities", "Is X having access"}.issubset(grid_filtered_df.columns):
                ai_caps = grid_filtered_df["AI Capabilities"].fillna("").astype(str).str.strip().str.casefold()
                access_vals = grid_filtered_df["Is X having access"].fillna("").astype(str).str.strip().str.casefold()
                icc_utilization_count = int((ai_caps.eq("yes") & access_vals.eq("yes")).sum())
            st.metric("AI Enabled asset (ICC Utilization) ", icc_utilization_count)

    if chart_left is not None:
        with chart_left:
            draw_count_plot(
                build_distribution(grid_filtered_df, "Cross MF Usage", split_csv=True),
                "Cross MF Usage",
                height=analytics_height,
            )
    if chart_right is not None:
        with chart_right:
            draw_access_status_chart(grid_filtered_df, height=analytics_height)

    geo_height = 680 if expand_charts else 420
    st.caption("Country Footprint")
    draw_country_geoplot(grid_filtered_df, height=geo_height)


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

    #hero_image = f"https://picsum.photos/1200/420?random={100 + asset_id}"
    #inline_image_1 = f"https://picsum.photos/1000/330?random={200 + asset_id}"
    #inline_image_2 = f"https://picsum.photos/1000/330?random={300 + asset_id}"
    
    # --- Image resolution logic ---
    asset_folder = os.path.join("assets", asset_name)

    root_images = {
        "img1": "img1.jpg",
        "img2": "img2.jpg",
        "img3": "img3.jpg",
    }

    def resolve_image(img_name):
        asset_path = os.path.join(asset_folder, f"{img_name}.jpg")
        root_path = root_images[img_name]

        if os.path.exists(asset_path):
            return asset_path
        else:
            return root_path

    hero_image = resolve_image("img1")
    inline_image_1 = resolve_image("img2")
    inline_image_2 = resolve_image("img3")

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
    st.sidebar.markdown("### Control Panel")
    sheet_param = str(st.query_params.get("sheet", "")).strip().casefold()
    default_internal = sheet_param == "internal"
    sheet_choice = st.sidebar.radio(
        "Select Source",
        options=["Internal Asset Details", "External Asset Details"],
        index=0 if default_internal else 1,
        key="sidebar_sheet_choice",
    )
    selected_sheet = sheet_choice
    st.sidebar.caption(f"Active sheet: {selected_sheet}")

    search_query = ""
    expand_charts = st.sidebar.toggle("Expand charts", value=False)

    internal_assets_df = load_assets("Internal Asset Details")
    external_assets_df = load_assets("External Asset Details")
    internal_assets_count = len(internal_assets_df["Asset Name"]) if "Asset Name" in internal_assets_df.columns else 0
    external_assets_count = len(external_assets_df["Asset Name"]) if "Asset Name" in external_assets_df.columns else 0
    total_assets_count = internal_assets_count + external_assets_count

    df = load_assets(selected_sheet)
    if df.empty:
        st.error(f"No data available for sheet '{selected_sheet}'. Please check Asset Detail.xlsx")
        return

    asset_param = st.query_params.get("asset")
    if asset_param is not None:
        try:
            render_asset_detail(df, int(asset_param))
        except ValueError:
            st.error("Invalid asset selected.")
    else:
        render_home(
            df,
            search_query=search_query,
            total_assets_count=total_assets_count,
            internal_assets_count=internal_assets_count,
            external_assets_count=external_assets_count,
            expand_charts=expand_charts,
            selected_sheet=selected_sheet,
        )


if __name__ == "__main__":
    main()
