#!/usr/bin/env python3
"""
Convert Markdown file to PDF with proper Chinese font support.
"""
import sys
import os
from pathlib import Path
import markdown
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration

def convert_markdown_to_pdf(md_file_path, output_pdf_path=None):
    """
    Convert a Markdown file to PDF with Chinese font support.
    
    Args:
        md_file_path (str): Path to the input Markdown file
        output_pdf_path (str, optional): Path for the output PDF file
    
    Returns:
        str: Path to the generated PDF file
    """
    # Resolve input file path
    md_path = Path(md_file_path)
    if not md_path.exists():
        raise FileNotFoundError(f"Markdown file not found: {md_file_path}")
    
    # Generate output path if not provided
    if output_pdf_path is None:
        output_pdf_path = md_path.with_suffix('.pdf')
    
    # Read the Markdown file
    with open(md_path, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    # Convert Markdown to HTML
    md = markdown.Markdown(extensions=['tables', 'codehilite', 'toc'])
    html_content = md.convert(md_content)
    
    # Create a complete HTML document with CSS styling
    html_template = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Report</title>
        <style>
            @page {{
                margin: 2cm;
                @bottom-center {{
                    content: counter(page);
                }}
            }}
            
            body {{
                font-family: "SimSun", "Arial", "Microsoft YaHei", sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: none;
                margin: 0;
                padding: 0;
            }}
            
            h1, h2, h3, h4, h5, h6 {{
                color: #2c3e50;
                margin-top: 2em;
                margin-bottom: 1em;
            }}
            
            h1 {{
                font-size: 28px;
                border-bottom: 2px solid #3498db;
                padding-bottom: 10px;
            }}
            
            h2 {{
                font-size: 24px;
                border-bottom: 1px solid #bdc3c7;
                padding-bottom: 5px;
            }}
            
            h3 {{
                font-size: 20px;
            }}
            
            p {{
                margin: 1em 0;
                text-align: justify;
            }}
            
            table {{
                border-collapse: collapse;
                width: 100%;
                margin: 1em 0;
            }}
            
            th, td {{
                border: 1px solid #ddd;
                padding: 8px;
                text-align: left;
            }}
            
            th {{
                background-color: #f2f2f2;
                font-weight: bold;
            }}
            
            code {{
                background-color: #f4f4f4;
                padding: 2px 4px;
                border-radius: 3px;
                font-family: "Courier New", monospace;
            }}
            
            pre {{
                background-color: #f4f4f4;
                padding: 1em;
                border-radius: 5px;
                overflow: auto;
            }}
            
            blockquote {{
                border-left: 4px solid #3498db;
                margin: 1em 0;
                padding: 0 1em;
                color: #7f8c8d;
            }}
            
            ul, ol {{
                padding-left: 2em;
            }}
            
            li {{
                margin: 0.5em 0;
            }}
            
            .toc {{
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 5px;
                padding: 1em;
                margin: 2em 0;
            }}
        </style>
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """
    
    # Convert HTML to PDF using WeasyPrint
    font_config = FontConfiguration()
    html_doc = HTML(string=html_template)
    
    # Generate PDF
    html_doc.write_pdf(output_pdf_path, font_config=font_config)
    
    print(f"Successfully converted {md_file_path} to {output_pdf_path}")
    return str(output_pdf_path)

def main():
    if len(sys.argv) < 2:
        print("Usage: python convert_markdown_to_pdf.py <markdown_file> [output_pdf]")
        print("Example: python convert_markdown_to_pdf.py report.md")
        print("Example: python convert_markdown_to_pdf.py report.md output.pdf")
        sys.exit(1)
    
    md_file = sys.argv[1]
    output_pdf = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        result_path = convert_markdown_to_pdf(md_file, output_pdf)
        print(f"PDF generated successfully: {result_path}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()