# utils.py
import os
import qrcode
from PIL import Image
from fpdf import FPDF
import requests

def check_contractor_exists(phone, AIRTABLE_API_KEY, USER_TABLE_URL):
    headers = {'Authorization': f'Bearer {AIRTABLE_API_KEY}'}
    response = requests.get(USER_TABLE_URL, headers=headers)
    records = response.json().get('records')

    if records:
        # Check if the phone number already exists in any record
        for record in records:
            fields = record.get('fields', {})
            phone_no = fields.get('phone no.')
            if phone_no and phone_no == phone:
                return True

    return False


def create_qr_code(amount, AIRTABLE_API_KEY, QR_CODE_TABLE_URL):
    # Create a QR code instance
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )

    # Now, add the QR code data to your QRTable
    qr_data = {'records': [{'fields': {'Amount': amount}}]}
    headers = {'Authorization': f'Bearer {AIRTABLE_API_KEY}'}
    response = requests.post(QR_CODE_TABLE_URL, headers=headers, json=qr_data)

    if response.status_code == 200:
        created_records = response.json().get('records')
        if created_records:
            created_record = created_records[0]
            qr_id = created_record['fields'].get('QR_ID')

            # Generate redeem URL with the corresponding QR_ID
            redeem_url = f"http://127.0.0.1:5000/redeem-qr/{qr_id}"

            # Add the URL to the QR code
            qr.add_data(redeem_url)
            qr.make(fit=True)

            # Create an image from the QR code instance
            img = qr.make_image(fill_color="black", back_color="white")

            # Save the image (create the directory if it doesn't exist)
            img_directory = 'static/qr_codes/'
            os.makedirs(img_directory, exist_ok=True)

            img_path = os.path.join(img_directory, f"qr_{qr_id}.png")
            img.save(img_path)

            return redeem_url, img_path

    return None, None

def convert_png_to_pdf(png_path):
    pdf_path = f'{png_path[:-4]}.pdf'
    image = Image.open(png_path)

    # Convert PNG to PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.image(png_path, 10, 10, 100)
    pdf.output(pdf_path)

    return pdf_path  