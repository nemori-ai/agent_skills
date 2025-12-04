#!/usr/bin/env python3
"""
Convert Markdown file to PDF using reportlab - a pure Python solution.
"""
import sys
import os
from pathlib import Path
import markdown
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import StringIO
import re

# Try to register Chinese fonts (optional)
def register_chinese_fonts():
    """Try to register Chinese fonts if available"""
    try:
        # Try to find and register common Chinese fonts
        font_paths = [
            '/System/Library/Fonts/Arial Unicode MS.ttf',  # macOS
            '/System/Library/Fonts/Helvetica.ttc',  # macOS
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',  # Linux
            '/Windows/Fonts/simsun.ttc',  # Windows
        ]
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                pdfmetrics.registerFont(TTFont('ChineseFont', font_path))
                return 'ChineseFont'
    except:
        pass
    return 'Helvetica'

def convert_markdown_to_pdf(md_file_path, output_pdf_path=None):
    """
    Convert a Markdown file to PDF using reportlab.
    
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
    
    # Register Chinese fonts
    font_name = register_chinese_fonts()
    
    # Create PDF document
    doc = SimpleDocTemplate(str(output_pdf_path), pagesize=A4,
                           rightMargin=72, leftMargin=72,
                           topMargin=72, bottomMargin=18)
    
    # Create styles
    styles = getSampleStyleSheet()
    
    # Define custom styles with Chinese font support
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontName=font_name,
        fontSize=18,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#2c3e50')
    )
    
    heading1_style = ParagraphStyle(
        'CustomHeading1',
        parent=styles['Heading1'],
        fontName=font_name,
        fontSize=16,
        spaceAfter=12,
        spaceBefore=20,
        textColor=colors.HexColor('#2c3e50')
    )
    
    heading2_style = ParagraphStyle(
        'CustomHeading2',
        parent=styles['Heading2'],
        fontName=font_name,
        fontSize=14,
        spaceAfter=10,
        spaceBefore=15,
        textColor=colors.HexColor('#34495e')
    )
    
    heading3_style = ParagraphStyle(
        'CustomHeading3',
        parent=styles['Heading3'],
        fontName=font_name,
        fontSize=12,
        spaceAfter=8,
        spaceBefore=12,
        textColor=colors.HexColor('#34495e')
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=10,
        spaceAfter=6,
        alignment=TA_JUSTIFY,
        textColor=colors.black
    )
    
    # Parse HTML and convert to reportlab elements
    story = []
    
    # Simple HTML parser for basic elements
    lines = html_content.split('\n')
    in_table = False
    table_data = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Handle headings
        if line.startswith('<h1>'):
            text = re.sub(r'<h1>(.*?)</h1>', r'\1', line)
            story.append(Paragraph(text, title_style))
        elif line.startswith('<h2>'):
            text = re.sub(r'<h2>(.*?)</h2>', r'\1', line)
            story.append(Paragraph(text, heading1_style))
        elif line.startswith('<h3>'):
            text = re.sub(r'<h3>(.*?)</h3>', r'\1', line)
            story.append(Paragraph(text, heading2_style))
        elif line.startswith('<h4>'):
            text = re.sub(r'<h4>(.*?)</h4>', r'\1', line)
            story.append(Paragraph(text, heading3_style))
        # Handle tables
        elif line.startswith('<table>'):
            in_table = True
            table_data = []
        elif line.startswith('</table>'):
            if table_data:
                table = Table(table_data)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), font_name),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('FONTNAME', (0, 1), (-1, -1), font_name),
                    ('FONTSIZE', (0, 1), (-1, -1), 9),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                story.append(table)
                story.append(Spacer(1, 12))
            in_table = False
        elif in_table and '<td>' in line:
            row_data = []
            cells = re.findall(r'<td>(.*?)</td>', line)
            table_data.append(cells)
        # Handle paragraphs
        elif line.startswith('<p>'):
            text = re.sub(r'<p>(.*?)</p>', r'\1', line)
            # Clean HTML tags
            text = re.sub(r'<[^>]+>', '', text)
            if text.strip():
                story.append(Paragraph(text, normal_style))
        # Handle list items
        elif line.startswith('<li>'):
            text = re.sub(r'<li>(.*?)</li>', r'• \1', line)
            text = re.sub(r'<[^>]+>', '', text)
            if text.strip():
                story.append(Paragraph(text, normal_style))
        # Handle other text
        elif not line.startswith('<') and not line.endswith('>'):
            if line.strip():
                story.append(Paragraph(line, normal_style))
    
    # Build the PDF
    doc.build(story)
    
    print(f"Successfully converted {md_file_path} to {output_pdf_path}")
    return str(output_pdf_path)

def main():
    if len(sys.argv) < 2:
        print("Usage: python convert_markdown_to_pdf_simple.py <markdown_file> [output_pdf]")
        print("Example: python convert_markdown_to_pdf_simple.py report.md")
        print("Example: python convert_markdown_to_pdf_simple.py report.md output.pdf")
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