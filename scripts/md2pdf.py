#!/usr/bin/env python3
"""
md2pdf - Convert Markdown to PDF for Supernote viewing

Usage: python md2pdf.py input.md [output.pdf]
"""

import sys
import re
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

def parse_markdown_table(lines):
    """Parse markdown table into list of lists."""
    rows = []
    for line in lines:
        line = line.strip()
        if line.startswith('|') and line.endswith('|'):
            cells = [c.strip() for c in line[1:-1].split('|')]
            # Skip separator rows (contain only dashes/colons)
            if not all(re.match(r'^[-:]+$', c) for c in cells):
                rows.append(cells)
    return rows

def md_to_pdf(md_path, pdf_path=None):
    """Convert markdown file to PDF."""
    md_path = Path(md_path)
    if pdf_path is None:
        pdf_path = md_path.with_suffix('.pdf')
    else:
        pdf_path = Path(pdf_path)
    
    # Read markdown
    content = md_path.read_text()
    lines = content.split('\n')
    
    # Set up PDF
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=letter,
        rightMargin=0.5*inch,
        leftMargin=0.5*inch,
        topMargin=0.5*inch,
        bottomMargin=0.5*inch
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=16,
        alignment=TA_CENTER,
        spaceAfter=12
    )
    h2_style = ParagraphStyle(
        'CustomH2',
        parent=styles['Heading2'],
        fontSize=12,
        spaceBefore=12,
        spaceAfter=6,
        textColor=colors.HexColor('#333333')
    )
    h3_style = ParagraphStyle(
        'CustomH3',
        parent=styles['Heading3'],
        fontSize=10,
        spaceBefore=8,
        spaceAfter=4,
        textColor=colors.HexColor('#555555')
    )
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=9,
        spaceAfter=6
    )
    small_style = ParagraphStyle(
        'Small',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.gray
    )
    
    story = []
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        # Skip empty lines
        if not line:
            i += 1
            continue
        
        # Skip blockquotes (like the Supernote note)
        if line.startswith('>'):
            i += 1
            continue
        
        # Skip horizontal rules
        if line == '---':
            i += 1
            continue
        
        # Title (# )
        if line.startswith('# '):
            story.append(Paragraph(line[2:], title_style))
            i += 1
            continue
        
        # H2 (## )
        if line.startswith('## '):
            story.append(Paragraph(line[3:], h2_style))
            i += 1
            continue
        
        # H3 (### )
        if line.startswith('### '):
            story.append(Paragraph(line[4:], h3_style))
            i += 1
            continue
        
        # Table
        if line.startswith('|'):
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                table_lines.append(lines[i])
                i += 1
            
            rows = parse_markdown_table(table_lines)
            if rows:
                # Calculate column widths based on content
                num_cols = len(rows[0])
                available_width = 7.5 * inch
                col_width = available_width / num_cols
                col_widths = [col_width] * num_cols
                
                t = Table(rows, colWidths=col_widths)
                t.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f0f0')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#333333')),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fafafa')]),
                    ('TOPPADDING', (0, 0), (-1, -1), 3),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                    ('LEFTPADDING', (0, 0), (-1, -1), 4),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ]))
                story.append(t)
                story.append(Spacer(1, 6))
            continue
        
        # Italic text (standalone like *Generated...*)
        if line.startswith('*') and line.endswith('*') and not line.startswith('**'):
            text = line[1:-1]
            story.append(Paragraph(f"<i>{text}</i>", small_style))
            i += 1
            continue
        
        # Regular paragraph
        # Handle bold (**text**)
        line = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', line)
        story.append(Paragraph(line, normal_style))
        i += 1
    
    # Build PDF
    doc.build(story)
    return pdf_path

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python md2pdf.py input.md [output.pdf]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    result = md_to_pdf(input_file, output_file)
    print(f"Created: {result}")
