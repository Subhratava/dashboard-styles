from pathlib import Path

import pandas as pd
from bokeh.io import output_file, save
from bokeh.layouts import column
from bokeh.models import Button, ColumnDataSource, CustomJS, DataTable, Div, HoverTool, StringFormatter, TableColumn, Tabs, TabPanel, TapTool
from bokeh.plotting import figure
from wordcloud import WordCloud


INPUT_CSV = Path("cloud.csv")
OUTPUT_HTML = Path("wordcloud_drilldown.html")
POS_DRILLDOWN_CSV = Path("positive_drilldown.csv")
NEG_DRILLDOWN_CSV = Path("negative_drilldown.csv")

POS_COL = "Positive Keywords"
NEG_COL = "Negative Keywords"
PROJECT_COL = "Project name"
SUMMARY_COL = "Summary"


def split_keywords(value: object) -> list[str]:
    if pd.isna(value):
        return []
    parts = [p.strip() for p in str(value).split("|")]
    return [p for p in parts if p]


def build_drilldown_df(df: pd.DataFrame, keyword_col: str) -> pd.DataFrame:
    rows: list[dict[str, str]] = []
    for _, r in df.iterrows():
        for kw in split_keywords(r.get(keyword_col, "")):
            rows.append(
                {
                    SUMMARY_COL: str(r.get(SUMMARY_COL, "")),
                    PROJECT_COL: str(r.get(PROJECT_COL, "")),
                    keyword_col: kw,
                }
            )
    return pd.DataFrame(rows, columns=[SUMMARY_COL, PROJECT_COL, keyword_col])


def keyword_frequencies(drilldown_df: pd.DataFrame, keyword_col: str) -> dict[str, int]:
    if drilldown_df.empty:
        return {}
    return drilldown_df[keyword_col].value_counts().to_dict()


def build_word_layout(freqs: dict[str, int]) -> pd.DataFrame:
    if not freqs:
        return pd.DataFrame(columns=["word", "freq", "x", "y", "font_size", "font_size_str", "color"])

    wc = WordCloud(
        width=1000,
        height=550,
        background_color="white",
        prefer_horizontal=1.0,
        collocations=False,
        random_state=42,
    ).generate_from_frequencies(freqs)

    records = []
    for (word, freq), font_size, (x, y), _, color in wc.layout_:
        records.append(
            {
                "word": word,
                "freq": float(freq),
                "x": float(x),
                "y": float(y),
                "font_size": int(font_size),
                "color": color,
            }
        )

    out = pd.DataFrame(records)
    out["font_size_str"] = out["font_size"].astype(int).astype(str) + "pt"
    return out


def make_tab(
    title: str,
    keyword_col: str,
    drilldown_df: pd.DataFrame,
    word_layout_df: pd.DataFrame,
) -> TabPanel:
    fig = figure(
        width=1100,
        height=520,
        title=f"{title} Word Cloud",
        tools="tap,reset,pan,wheel_zoom,save",
        toolbar_location="above",
        x_axis_location=None,
        y_axis_location=None,
    )
    fig.grid.visible = False

    if not word_layout_df.empty:
        x_max = float(word_layout_df["x"].max()) + 60
        y_max = float(word_layout_df["y"].max()) + 60
    else:
        x_max = 1000
        y_max = 550

    fig.x_range.start = 0
    fig.x_range.end = x_max
    fig.y_range.start = y_max
    fig.y_range.end = 0

    wc_source = ColumnDataSource(word_layout_df)
    text_renderer = fig.text(
        x="x",
        y="y",
        text="word",
        text_font_size="font_size_str",
        text_color="color",
        text_alpha=0.9,
        source=wc_source,
    )

    fig.add_tools(
        HoverTool(
            renderers=[text_renderer],
            tooltips=[("Word", "@word"), ("Frequency", "@freq{0}")],
        )
    )

    drill_all_source = ColumnDataSource(
        {
            SUMMARY_COL: drilldown_df[SUMMARY_COL].astype(str).tolist(),
            PROJECT_COL: drilldown_df[PROJECT_COL].astype(str).tolist(),
            keyword_col: drilldown_df[keyword_col].astype(str).tolist(),
            "word": drilldown_df[keyword_col].astype(str).tolist(),
        }
    )
    table_source = ColumnDataSource({SUMMARY_COL: [], PROJECT_COL: [], keyword_col: []})
    selection_div = Div(text="<b>Selected word:</b> None", width=1100)

    table = DataTable(
        source=table_source,
        width=1100,
        height=280,
        columns=[
            TableColumn(field=SUMMARY_COL, title=SUMMARY_COL, formatter=StringFormatter()),
            TableColumn(field=PROJECT_COL, title=PROJECT_COL, formatter=StringFormatter()),
            TableColumn(field=keyword_col, title=keyword_col, formatter=StringFormatter()),
        ],
        index_position=None,
        autosize_mode="fit_columns",
    )

    filter_callback = CustomJS(
        args=dict(words_src=wc_source, all_src=drill_all_source, view_src=table_source, sel_div=selection_div),
        code=f"""
const inds = words_src.selected.indices;
if (!inds || inds.length === 0) {{
    sel_div.text = "<b>Selected word:</b> None";
    view_src.data = {{"{SUMMARY_COL}": [], "{PROJECT_COL}": [], "{keyword_col}": []}};
    view_src.change.emit();
    return;
}}

// Use the most recent index in case the selection array contains older items.
const i = inds[inds.length - 1];
const w = words_src.data["word"][i];
sel_div.text = `<b>Selected word:</b> ${{w}}`;

const data_all = all_src.data;
const view_fields = Object.keys(view_src.data);
const n = (data_all["word"] && data_all["word"].length) ? data_all["word"].length : 0;
const new_data = {{}};
for (const f of view_fields) new_data[f] = [];

for (let r = 0; r < n; r++) {{
    if (data_all["word"][r] === w) {{
        for (const f of view_fields) new_data[f].push(data_all[f][r]);
    }}
}}

view_src.data = new_data;
view_src.change.emit();
""",
    )

    tap_tool = fig.select_one(TapTool)
    if tap_tool is not None:
        tap_tool.renderers = [text_renderer]
    wc_source.selected.js_on_change("indices", filter_callback)

    reset_callback = CustomJS(
        args=dict(words_source=wc_source, table_source=table_source, sel_div=selection_div),
        code=f"""
words_source.selected.indices = [];
words_source.selected.change.emit();
table_source.data = {{"{SUMMARY_COL}": [], "{PROJECT_COL}": [], "{keyword_col}": []}};
table_source.change.emit();
sel_div.text = "<b>Selected word:</b> None";
""",
    )
    reset_button = Button(label="Reset Filter", button_type="primary", width=160)
    reset_button.js_on_click(reset_callback)

    layout = column(fig, selection_div, reset_button, table)
    return TabPanel(title=title, child=layout)


def main() -> None:
    df = pd.read_csv(INPUT_CSV)

    required = [PROJECT_COL, SUMMARY_COL, POS_COL, NEG_COL]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required column(s): {missing}")

    pos_drill = build_drilldown_df(df, POS_COL)
    neg_drill = build_drilldown_df(df, NEG_COL)

    pos_drill.to_csv(POS_DRILLDOWN_CSV, index=False)
    neg_drill.to_csv(NEG_DRILLDOWN_CSV, index=False)

    pos_freq = keyword_frequencies(pos_drill, POS_COL)
    neg_freq = keyword_frequencies(neg_drill, NEG_COL)

    pos_layout = build_word_layout(pos_freq)
    neg_layout = build_word_layout(neg_freq)

    tabs = Tabs(
        tabs=[
            make_tab("Positive", POS_COL, pos_drill, pos_layout),
            make_tab("Negative", NEG_COL, neg_drill, neg_layout),
        ]
    )

    output_file(OUTPUT_HTML, title="Word Cloud Drilldown")
    save(tabs)

    print(f"Created: {OUTPUT_HTML.resolve()}")
    print(f"Saved drilldown CSV: {POS_DRILLDOWN_CSV.resolve()}")
    print(f"Saved drilldown CSV: {NEG_DRILLDOWN_CSV.resolve()}")


if __name__ == "__main__":
    main()
