from flask import Flask, render_template, request, send_file
import pandas as pd
from reportlab.lib.pagesizes import A4
import qrcode
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from io import BytesIO
from flask import Flask, request, send_file
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
import qrcode

from flask import Flask, request, send_file
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
import qrcode


app = Flask(__name__)

def get_regno_name_mapping():
    csv = pd.read_csv("candidates.csv", header=None)
    mapping = {}

    current_unit = None

    for index, row in csv.iterrows():
        if isinstance(row[3], str) and row[3].startswith("Unit:"):
            current_unit = row[3].split("Unit:")[1].strip()
        elif pd.notna(row[0]) and pd.notna(row[1]) and current_unit:
            name_candidate = str(row[0]).strip()
            regno_candidate = str(row[1]).strip()
            if name_candidate != "" and regno_candidate != "":
                mapping[regno_candidate] = name_candidate

    return mapping


# Read CSV
def load_data():
    data = []
    csv = pd.read_csv("candidates.csv", header=None)
    
    # Extract header info
    series = csv.iloc[0, 0].split("Series:")[1].strip()
    center = csv.iloc[0, 1].split("Center:")[1].strip()
    course = csv.iloc[0, 2].split("COURSE :")[1].strip()

    current_unit = None

    for index, row in csv.iterrows():
        # Check for Unit
        if isinstance(row[3], str) and str(row[3]).startswith("Unit:"):
            current_unit = row[3].split("Unit:")[1].strip()
        
        # Check for Candidate Name Row
        elif pd.notna(row[0]) and pd.notna(row[1]) and current_unit:
            name_candidate = str(row[0]).strip()
            regno_candidate = str(row[1]).strip()
            # Skip empty or unwanted rows
            if name_candidate != "" and regno_candidate != "":
                data.append({
                    "name": name_candidate,
                    "regno": regno_candidate,
                    "unit": current_unit
                })

    df = pd.DataFrame(data)
    grouped = df.groupby(['name', 'regno'])['unit'].apply(list).reset_index()
    return series, center, course, grouped
@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/search', methods=['GET', 'POST'])
def search():
    exam = request.args.get('exam')  # get exam type from the landing page
    return render_template('search.html', exam=exam)

@app.route('/search_internal', methods=['GET', 'POST'])
def search_internal():
    exam = request.args.get('exam')  # Get the exam type from the URL parameters
    return render_template('search_internal.html', exam=exam)


@app.route('/mapping')
def mapping():
    mapping = get_regno_name_mapping()
    return render_template("mapping.html", mapping=mapping)


@app.route('/card', methods=['POST'])
def card():
    series, center, course, df = load_data()
    mapping = get_regno_name_mapping()
    
    query = request.form.get("query").strip()

    # Check if query is in regno or name (case insensitive)
    candidate_regno = None
    candidate_name = None

    for regno, name in mapping.items():
        if query.lower() in regno.lower() or query.lower() in name.lower():
            candidate_regno = regno
            candidate_name = name
            break

    if not candidate_regno:
        return "Candidate not found!"

    # Get candidate's units
    candidate = df[df['regno'] == candidate_regno]

    if candidate.empty:
        return "Candidate found but no registered units!"

    # Units list
    units = candidate.iloc[0]['unit']

    return render_template("card.html",
                           series=series,
                           center=center,
                           course=course,
                           name=candidate_name,
                           regno=candidate_regno,
                           units=units)



@app.route('/download', methods=['POST'])
def download():
    series = request.form['series']
    center = request.form['center']
    course = request.form['course']
    name = request.form['name']
    regno = request.form['regno']
    units = request.form.getlist('units')

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    styles = getSampleStyleSheet()
    normal = styles['Normal']
    

    # ===== Header =====
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(150, height - 60, "TVET CDACC Examination Card")

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 80, "Series:")
    c.setFont("Helvetica", 12)
    c.drawString(95, height - 80, series)

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 100, "Center:")
    c.setFont("Helvetica", 10)
    c.drawString(95, height - 100, center)

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 120, "Course:")
    c.line(120, height - 120, 350, height - 120)  # underline

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 140, "Candidate Name:")
    c.setFont("Helvetica", 12)
    c.drawString(150, height - 140, name)

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 160, "TVET CDACC Reg No:")
    c.setFont("Helvetica", 12)
    c.drawString(180, height - 160, regno)
    # ===== Registered Units =====
    c.setFont("Helvetica-Bold", 13)
    c.drawString(50, height - 180, "Registered Units")

    # ===== Table =====
    data = [['No.', 'Unit Name', 'Done']]

    for idx, unit in enumerate(units, start=1):
        data.append([str(idx), Paragraph(unit, normal), ''])

    table = Table(data, colWidths=[30, 220, 35])
    table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
    ]))

    # ===== Table Positioning Dynamically =====
    table.wrapOn(c, width, height)

    table_y_start = height - 295  # Adjusted to ensure it's below "Registered Units"
    row_height = 15  # Approximate height per row
    table_height = row_height * len(data)  # Calculate total table height
    table_y_position = table_y_start - table_height  # Adjust position dynamically

# Ensure table does not go too low on the page
    if table_y_position < 200:  
        table_y_position = 200  

    table.drawOn(c, 50, table_y_position)  # Draw table dynamically

# ===== QR Code Below the Table =====
    qr_data = f"Name: {name}\nReg No: {regno}\nSeries: {series}\nCenter: {center}\nCourse: {course}"
    qr_img = qrcode.make(qr_data)
    qr_buffer = BytesIO()
    qr_img.save(qr_buffer)
    qr_buffer.seek(0)
    qr_reader = ImageReader(qr_buffer)

# Position QR code 50px below the table
    qr_y = table_y_position - 100  

# Ensure QR does not go off-page
    if qr_y < 100:  
        qr_y = 100  

    c.drawImage(qr_reader, 50, qr_y, width=100, height=100)  # Draw QR at adjusted position

# ===== Signature & Stamp Below QR Code =====
    signature_y = qr_y - 60  # Place signature section below QR

# Ensure it does not go off the page
    if signature_y < 50:  
        signature_y = 50  

    c.setFont("Helvetica", 10)
    c.drawString(50, signature_y, "Candidate Signature: _______________________________")
    c.drawString(50, signature_y - 20, "Official Stamp: ")
    c.drawString(50, signature_y - 50, "The Exam Card is Valid only if signed and stamped by HOD /Exam Officer / Registrar")

    c.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"{name}_Exam_Card.pdf", mimetype='application/pdf')




if __name__ == "__main__":
    app.run(debug=True)
