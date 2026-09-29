from io import BytesIO
from datetime import datetime
from fpdf import FPDF


class Certificate(FPDF):
    def header(self):
        pass

    def footer(self):
        pass


def generate_certificate(trainee_name, program_title, issue_date=None):
    """Returns PDF bytes for a training completion certificate."""
    issue_date = issue_date or datetime.utcnow()
    pdf = Certificate(orientation="L", unit="mm", format="A4")
    pdf.add_page()

    # Outer border (brand green)
    pdf.set_draw_color(141, 198, 63)
    pdf.set_line_width(2)
    pdf.rect(10, 10, 277, 190)

    # Inner thin border
    pdf.set_draw_color(111, 168, 46)
    pdf.set_line_width(0.5)
    pdf.rect(15, 15, 267, 180)

    # Top brand bar
    pdf.set_fill_color(141, 198, 63)
    pdf.rect(10, 10, 277, 22, "F")

    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_xy(20, 14)
    pdf.cell(0, 10, "MAXIM NYANSA ELECTRONICS", ln=0)
    pdf.set_xy(20, 23)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, "Sierra Leone  |  Skills Today, Success Tomorrow", ln=0)

    # Title
    pdf.set_text_color(26, 26, 26)
    pdf.set_font("Helvetica", "B", 34)
    pdf.set_xy(0, 55)
    pdf.cell(297, 15, "CERTIFICATE OF COMPLETION", align="C")

    # Decorative line
    pdf.set_draw_color(141, 198, 63)
    pdf.set_line_width(1.2)
    pdf.line(100, 75, 197, 75)

    # Body
    pdf.set_font("Helvetica", "", 13)
    pdf.set_text_color(74, 74, 74)
    pdf.set_xy(0, 88)
    pdf.cell(297, 8, "This certificate is proudly presented to", align="C")

    # Name
    pdf.set_text_color(26, 26, 26)
    pdf.set_font("Helvetica", "B", 30)
    pdf.set_xy(0, 100)
    pdf.cell(297, 16, trainee_name.upper(), align="C")

    # Underline under name
    pdf.set_draw_color(141, 198, 63)
    pdf.line(90, 120, 207, 120)

    # Body 2
    pdf.set_font("Helvetica", "", 13)
    pdf.set_text_color(74, 74, 74)
    pdf.set_xy(0, 128)
    pdf.cell(297, 8, "for successfully completing the", align="C")

    pdf.set_text_color(26, 26, 26)
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_xy(0, 140)
    pdf.multi_cell(297, 9, program_title, align="C")

    # Signature line + date
    pdf.set_draw_color(74, 74, 74)
    pdf.set_line_width(0.4)
    pdf.line(45, 175, 115, 175)
    pdf.line(182, 175, 252, 175)

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(74, 74, 74)
    pdf.set_xy(45, 178)
    pdf.cell(70, 6, "Michael Jobie Musa — Country Director", align="C")
    pdf.set_xy(182, 178)
    pdf.cell(70, 6, f"Issued: {issue_date.strftime('%B %d, %Y')}", align="C")

    # Footer ID
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(167, 169, 172)
    pdf.set_xy(15, 190)
    pdf.cell(267, 4, "This certifies completion of practical vocational training at Maxim Nyansa Electronics SL, Freetown.",
             align="C")

    return bytes(pdf.output())