from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import pandas as pd, io
from reportlab.lib.pagesizes import landscape
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.graphics.barcode import code128
from textwrap import wrap

app = Flask(__name__)
# Allow your Hostinger site to call this API
# For stricter security, replace "*" with "https://YOURDOMAIN.com"
CORS(app, resources={r"/*": {"origins": "https://lightgreen-llama-621491.hostingersite.com"}})

@app.get("/")
def health():
    return jsonify(status="ok", message="Label Generator API running")

@app.post("/generate")
def generate():
    if "file" not in request.files:
        return jsonify(error="No file uploaded. Use form field 'file'."), 400
    f = request.files["file"]
    try:
        df = pd.read_excel(f).fillna("")
    except Exception as e:
        return jsonify(error=f"Failed reading Excel: {e}"), 400

    if "Tracking_Id" not in df.columns:
        return jsonify(error="Excel must include 'Tracking_Id' column."), 400

    buf = io.BytesIO()
    W, H = landscape((4*inch, 6*inch))
    c = canvas.Canvas(buf, pagesize=(W, H))

    for _, row in df.iterrows():
        tracking = str(row.get("Tracking_Id", "")).strip()
        pay = str(row.get("Payment_Method", "")).lower()
        name = str(row.get("Consignee_Name", "")).strip()
        addr = str(row.get("Consignee_Address", "")).strip()

        m = 14
        c.setStrokeColor(colors.black)
        c.rect(m, m, W-2*m, H-2*m)

        banner = "COD: Check the payable amount on the app" if ("cod" in pay or "cash" in pay) else "PREPAID"
        c.setFillColor(colors.black)
        c.rect(m, H-m-28, W-2*m, 28, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(m+10, H-m-20, banner)

        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(m+10, H-m-48, "Customer Address")
        c.setFont("Helvetica-Bold", 12)
        c.drawString(m+10, H-m-66, (name or "-")[:46])
        c.setFont("Helvetica", 9)
        y = H-m-82
        for line in wrap(addr or "-", 72):
            c.drawString(m+10, y, line)
            y -= 12

        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(W/2, m+86, tracking or "-")
        if tracking:
            bc = code128.Code128(tracking, barHeight=40, barWidth=0.9)
            bw = bc.width
            scale = min(1.0, (W-2*m-40)/bw)
            x = (W - bw*scale)/2
            yb = m+44
            c.saveState()
            c.translate(x, yb)
            c.scale(scale, 1.0)
            bc.drawOn(c, 0, 0)
            c.restoreState()

        c.showPage()

    c.save()
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name="labels.pdf", mimetype="application/pdf")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
