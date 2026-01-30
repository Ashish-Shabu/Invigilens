
import markdown
from xhtml2pdf import pisa
import os

def convert_md_to_pdf(source_md, output_pdf):
    # 1. Read Markdown
    with open(source_md, 'r', encoding='utf-8') as f:
        text = f.read()

    # 2. Convert to HTML
    html_content = markdown.markdown(text, extensions=['extra', 'codehilite'])

    # 3. Add CSS/Styling for a "Report" look
    styled_html = f"""
    <html>
    <head>
    <style>
        body {{
            font-family: Helvetica, sans-serif;
            font-size: 12pt;
            line-height: 1.6;
            margin: 40px;
        }}
        h1 {{
            color: #2c3e50;
            text-align: center;
            border-bottom: 2px solid #2c3e50;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            border-bottom: 1px solid #bdc3c7;
            padding-bottom: 5px;
            margin-top: 20px;
        }}
        h3 {{
            color: #7f8c8d;
            margin-top: 15px;
        }}
        code {{
            background-color: #f4f4f4;
            padding: 2px 5px;
            font-family: Courier, monospace;
        }}
        pre {{
            background-color: #f8f8f8;
            padding: 10px;
            border: 1px solid #ddd;
            white-space: pre-wrap;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }}
        th {{
            background-color: #f2f2f2;
        }}
    </style>
    </head>
    <body>
    {html_content}
    </body>
    </html>
    """

    # 4. Generate PDF
    with open(output_pdf, "wb") as result_file:
        pisa_status = pisa.CreatePDF(
            styled_html, dest=result_file)

    if pisa_status.err:
        print(f"Error converting to PDF: {pisa_status.err}")
    else:
        print(f"Successfully created: {output_pdf}")

if __name__ == "__main__":
    source = os.path.join(os.path.dirname(__file__), '../project_report.md')
    output = os.path.join(os.path.dirname(__file__), '../InvigiLens_Technical_Report.pdf')
    
    print(f"Converting {source}...")
    try:
        convert_md_to_pdf(source, output)
    except Exception as e:
        print(f"Failed: {e}")
