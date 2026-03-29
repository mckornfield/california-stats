"""Generate a combined HTML report from all executed notebooks."""

import json
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOTEBOOKS_DIR = ROOT / "notebooks"
DOCS_DIR = ROOT / "docs"
DOCS_DIR.mkdir(parents=True, exist_ok=True)

NOTEBOOKS = [
    "01_data_collection.ipynb",
    "02_assessment_ratio_map.ipynb",
    "03_top_bottom_counties.ipynb",
    "04_revenue_gap_map.ipynb",
    "05_income_correlation.ipynb",
]


def extract_outputs(nb_path: Path) -> str:
    """Extract notebook outputs as HTML fragments directly from the .ipynb JSON."""
    nb = json.loads(nb_path.read_text())
    parts = []

    for cell in nb.get("cells", []):
        if cell["cell_type"] == "markdown":
            source = "".join(cell.get("source", []))
            html_lines = []
            for line in source.split("\n"):
                if line.startswith("### "):
                    html_lines.append(f"<h4>{line[4:]}</h4>")
                elif line.startswith("## "):
                    html_lines.append(f"<h3>{line[3:]}</h3>")
                elif line.startswith("# "):
                    html_lines.append(f"<h3>{line[2:]}</h3>")
                elif line.startswith("**") and line.endswith("**"):
                    html_lines.append(f"<p><strong>{line[2:-2]}</strong></p>")
                elif line.startswith("- "):
                    html_lines.append(f"<li>{line[2:]}</li>")
                elif line.strip():
                    html_lines.append(f"<p>{line}</p>")
            parts.append("\n".join(html_lines))
            continue

        if cell["cell_type"] != "code":
            continue

        for output in cell.get("outputs", []):
            otype = output.get("output_type", "")

            if otype in ("display_data", "execute_result"):
                data = output.get("data", {})

                if "application/vnd.plotly.v1+json" in data:
                    plotly_data = data["application/vnd.plotly.v1+json"]
                    div_id = f"plotly-{uuid.uuid4().hex[:12]}"
                    fig_data = json.dumps(plotly_data.get("data", []))
                    layout = plotly_data.get("layout", {})
                    layout.setdefault("autosize", True)
                    layout.setdefault("margin", {})
                    layout["margin"].setdefault("l", 10)
                    layout["margin"].setdefault("r", 10)
                    layout["margin"].setdefault("t", 60)
                    layout["margin"].setdefault("b", 10)
                    fig_layout = json.dumps(layout)
                    parts.append(
                        f'<div id="{div_id}" class="plotly-graph-div" '
                        f'style="width:100%;"></div>\n'
                        f'<script type="text/javascript">\n'
                        f'Plotly.newPlot("{div_id}", {fig_data}, {fig_layout}, '
                        f'{{"responsive": true, "displayModeBar": false}});\n'
                        f'</script>'
                    )

                elif "text/html" in data:
                    html_content = "".join(data["text/html"])
                    if "<table" in html_content:
                        parts.append(f'<div class="table-wrapper">{html_content}</div>')
                    else:
                        parts.append(f'<div class="output-html">{html_content}</div>')

                elif "image/png" in data:
                    img_data = data["image/png"]
                    if isinstance(img_data, list):
                        img_data = "".join(img_data)
                    parts.append(
                        f'<div class="output-image">'
                        f'<img src="data:image/png;base64,{img_data.strip()}">'
                        f'</div>'
                    )

            elif otype == "stream":
                text = "".join(output.get("text", []))
                if text.strip():
                    parts.append(f'<pre class="output-text">{text}</pre>')

    return "\n".join(parts)


def main():
    sections = []
    for nb_name in NOTEBOOKS:
        nb_path = NOTEBOOKS_DIR / nb_name
        if not nb_path.exists():
            print(f"Skipping {nb_name} (not found)")
            continue
        print(f"Extracting outputs from {nb_name} ...")
        html_fragment = extract_outputs(nb_path)
        if html_fragment:
            title = nb_name.replace(".ipynb", "").replace("_", " ").title()
            title = title.lstrip("0123456789 ")
            sections.append((title, html_fragment))

    nav_items = []
    content_sections = []
    for i, (title, fragment) in enumerate(sections):
        slug = f"section-{i}"
        nav_items.append(f'<a href="#{slug}">{title}</a>')
        content_sections.append(
            f'<section id="{slug}">\n'
            f'<h2 class="section-title">{title}</h2>\n'
            f'<div class="notebook-content">{fragment}</div>\n'
            f'</section>\n<hr>\n'
        )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>California Prop 13 Tax Disparity Analysis</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
    * {{ box-sizing: border-box; }}
    body {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
        max-width: 1200px;
        margin: 0 auto;
        padding: 20px;
        background: #f7f8fa;
        color: #333;
    }}
    h1 {{
        text-align: center;
        color: #1a3a5c;
        border-bottom: 3px solid #2980b9;
        padding-bottom: 15px;
        font-size: clamp(1.4rem, 4vw, 2rem);
    }}
    .subtitle {{
        text-align: center;
        color: #666;
        margin: -10px 0 20px;
        font-size: 0.95rem;
    }}
    nav {{
        display: flex;
        flex-wrap: wrap;
        justify-content: center;
        gap: 8px 16px;
        margin: 20px 0 30px;
        padding: 15px;
        background: #fff;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }}
    nav a {{
        color: #2980b9;
        text-decoration: none;
        font-weight: 600;
        font-size: 14px;
        white-space: nowrap;
    }}
    nav a:hover {{ text-decoration: underline; }}
    .section-title {{
        color: #1a3a5c;
        border-left: 4px solid #2980b9;
        padding-left: 12px;
        font-size: clamp(1.1rem, 3vw, 1.5rem);
    }}
    section {{
        background: #fff;
        padding: 25px;
        margin: 20px 0;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        overflow: hidden;
    }}
    .notebook-content img {{
        max-width: 100%;
        height: auto;
        display: block;
        margin: 0 auto;
    }}
    .output-text {{
        background: #f5f5f5;
        padding: 10px;
        border-radius: 4px;
        overflow-x: auto;
        font-size: 13px;
        white-space: pre-wrap;
        word-break: break-word;
    }}
    .table-wrapper {{
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
        margin: 10px 0;
    }}
    .notebook-content table {{
        border-collapse: collapse;
        font-size: 13px;
        min-width: 400px;
    }}
    .notebook-content table th,
    .notebook-content table td {{
        border: 1px solid #ddd;
        padding: 6px 10px;
        text-align: right;
        white-space: nowrap;
    }}
    .notebook-content table th {{
        background: #eaf2fb;
        position: sticky;
        top: 0;
        z-index: 1;
        color: #1a3a5c;
    }}
    .output-image {{
        text-align: center;
        margin: 15px 0;
        overflow-x: auto;
    }}
    .output-html {{ margin: 15px 0; overflow-x: auto; }}
    hr {{
        border: none;
        border-top: 1px solid #eee;
        margin: 30px 0;
    }}
    .plotly-graph-div {{
        margin: 15px 0;
        min-height: 400px;
    }}
    footer {{
        text-align: center;
        color: #999;
        font-size: 13px;
        margin-top: 40px;
        padding: 20px;
        border-top: 1px solid #eee;
    }}
    @media (max-width: 768px) {{
        body {{ padding: 10px; }}
        section {{ padding: 12px; margin: 10px 0; border-radius: 6px; }}
        nav {{ padding: 10px; gap: 6px 12px; }}
        nav a {{ font-size: 13px; }}
        .plotly-graph-div {{ min-height: 300px; }}
        .notebook-content table {{ font-size: 11px; }}
        .notebook-content table th,
        .notebook-content table td {{ padding: 4px 6px; }}
        .output-text {{ font-size: 11px; padding: 8px; }}
    }}
</style>
</head>
<body>
<h1>California Prop 13 Property Tax Disparity Analysis</h1>
<p class="subtitle">Which counties have the largest gaps between assessed value and market value?</p>
<nav>
    {"".join(nav_items)}
</nav>

{"".join(content_sections)}

<footer>
    Generated from Jupyter notebooks &mdash;
    Data sources: CA Board of Equalization Annual Report 2022-23, Zillow Research ZHVI, Census ACS 5-Year 2022.
    <br>
    <em>Note: BOE total secured roll includes all property types; residential fraction estimated at ~70% per county type.
    Market value estimates use Zillow ZHVI median home values. Tax gap assumes 1.1% effective rate on assessed value.</em>
</footer>
</body>
</html>"""

    out_path = ROOT / "index.html"
    out_path.write_text(html)
    print(f"\nWrote combined report to {out_path}")
    print(f"  File size: {out_path.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
