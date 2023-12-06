from flask import Flask, render_template, request, send_from_directory
from flask import jsonify  
import requests
import qrcode
from PIL import Image
import os
from fpdf import FPDF
from dotenv import load_dotenv
from utils import create_qr_code, convert_png_to_pdf, check_contractor_exists

load_dotenv()

app = Flask(__name__, static_url_path='/static')
AIRTABLE_BASE_ID = os.getenv('AIRTABLE_BASE_ID')
AIRTABLE_API_KEY = os.getenv('AIRTABLE_API_KEY')
USER_TABLE_URL = f'https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/UserTable'
QR_CODE_TABLE_URL = f'https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/QRTable'


@app.route('/register-contractor', methods=['GET', 'POST'])
def register_contractor():
    if request.method == 'POST':
        phone = request.form.get('phone')
        name = request.form.get('name')

        # Check if phone number already exists
        if check_contractor_exists(phone, AIRTABLE_API_KEY, USER_TABLE_URL):
            return "Contractor already exists"
        else:
            # Create a new user
            data = {'records': [{'fields': {'Name': name, 'phone no.': phone}}]}
            headers = {'Authorization': f'Bearer {AIRTABLE_API_KEY}'}
            response = requests.post(USER_TABLE_URL, headers=headers, json=data)

            if response.status_code == 200:
                created_records = response.json().get('records')
                if created_records:
                    created_record = created_records[0]
                    return f"Contractor successfully registered with ID: {created_record['id']}"
                else:
                    return "Contractor registration failed"
            else:
                return f"Contractor registration failed - {response.text}"

    return render_template('registration_form.html')

@app.route('/redeem-qr/<int:qr_id>', methods=['GET', 'POST'])
def redeem_qr(qr_id):
    if not qr_id:
        return "QR ID not provided"

    # Check if QR code is valid and not redeemed
    headers = {'Authorization': f'Bearer {AIRTABLE_API_KEY}'}
    
    # 'QR_ID' is the field in the QRTable
    params = {'filterByFormula': f'{{QR_ID}}={qr_id}'}
    response = requests.get(QR_CODE_TABLE_URL, headers=headers, params=params)
    
    records = response.json().get('records')

    if not records or records[0].get('fields', {}).get('is_redeemed'):
        return "Not a valid code"

    qr_record = records[0].get('fields')

    if request.method == 'POST':
        contractor_phone = request.form.get('contractor_phone')

        # Check if contractor is a registered user
        headers = {'Authorization': f'Bearer {AIRTABLE_API_KEY}'}
        response = requests.get(USER_TABLE_URL, headers=headers)
        user_records = response.json().get('records')

        contractor_record = None
        if user_records:
            # Check if the phone number already exists in any record
            for record in user_records:
                fields = record.get('fields', {})
                phone_no = fields.get('phone no.')
                if phone_no and phone_no == contractor_phone:
                    contractor_record = record
                    break

        if contractor_record:
            contractor_id = contractor_record['id']
            # Mark QR code as redeemed and associate with the contractor
            data = {'fields': {'is_redeemed': True, 'UserTable': [contractor_id]}}
            response = requests.patch(f"{QR_CODE_TABLE_URL}/{records[0]['id']}", headers=headers, json=data)

            if response.status_code == 200:
                return "QR code successfully redeemed"
            else:
                return f"Failed to redeem QR code - {response.text}"
        else:
            return "You're not a registered contractor"

    return render_template('qr_redemption_form.html', qr_id=qr_id)


@app.route('/create-qr', methods=['GET', 'POST'])
def create_qr():
    result = None

    if request.method == 'POST':
        amount_str = request.form.get('amount')

        try:
            # Convert amount to float
            amount = float(amount_str)

            # Check if the amount is greater than or equal to 0
            if amount < 0:
                raise ValueError("Amount must be greater than or equal to 0.")

            # Create the QR code
            result = create_qr_code(amount, AIRTABLE_API_KEY, QR_CODE_TABLE_URL)

        except ValueError as e:
            return f"Invalid amount. {str(e)}"

    return render_template('create_qr.html', result=result)

@app.route('/download-qr/<qr_format>/<path:qr_path>')
def download_qr(qr_format, qr_path):
    img_path = f'static/{qr_path}'

    if qr_format == 'png':
        return send_from_directory('static', qr_path, as_attachment=True)

    elif qr_format == 'pdf':
        pdf_path = convert_png_to_pdf(img_path)
        return send_from_directory('', pdf_path, as_attachment=True)

    else:
        return 'Invalid QR format'


if __name__ == '__main__':
    app.run(debug=False)
