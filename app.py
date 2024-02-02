from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import qrcode
import os
import base64
import firebase_admin
from firebase_admin import credentials, firestore, auth
from io import BytesIO

##### App Configuaration
app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = 'GFREDD$FVSNKSKKK76GVDNJK'
app.config['UPLOAD_FOLDER'] = 'uploads'
cred = credentials.Certificate("eventparticipants-fe9eb-firebase-adminsdk-b72n1-09e7ab8063.json")
firebase_admin.initialize_app(cred)
db = firestore.client()


### ROUTE TO GET THE PARTICIPANTS
@app.route('/participants', methods=['GET'])
def get_participants():
    participants_ref = db.collection("participants")
    docs = participants_ref.stream()
    participant_list = [doc.to_dict() for doc in docs ]
    return jsonify(participant_list)


### ROUTE TO GENERATE THE QR CODE
@app.route('/generate_qr', methods=['POST'])
def generate_qr():
    json_data = request.get_json(force=True)
    print(json_data)
    qr_folder = json_data.get('qr_folder', 'uploads')  # Default folder is 'uploads'
    
    try:
        # Generate QR codes and get the data (title, name, surname, affiliation, QR code as base64)
        qr_data = generate_qr_codes(json_data['json_data'], qr_folder)

        # Respond with success and the data of the generated QR codes
        return jsonify({'status': 'success', 'message': 'QR Codes generated successfully.', 'qr_data': qr_data})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'An error occurred: {e}'})

def generate_qr_codes(json_data, qr_folder):
    qr_data = []

    if not os.path.exists(qr_folder):
        os.makedirs(qr_folder)

    for row in json_data:
        title = row.get('Title', '')
        name = row.get('Personal Information - Name', '')
        surname = row.get('Personal Information - Surname', '')
        affiliation = row.get('Affiliation - Organization affiliation', '')

        data = f"{name} {surname} {affiliation}"
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        # Save image to BytesIO and encode to base64
        img_stream = BytesIO()
        img.save(img_stream, format="PNG")
        img_base64 = base64.b64encode(img_stream.getvalue()).decode('utf-8')

        qr_data.append({
            'title': title,
            'name': name,
            'surname': surname,
            'affiliation': affiliation,
            'qr_code_base64': img_base64
        })

        # Add the generated QR data to Firestore
        add_member_to_firestore({
            'affiliation': affiliation,
            'name': name,
            'surname': surname,
            'title': title,
            'qr_code_base64': img_base64
        })

    return qr_data

#########ENDPOINT TO CREATE QR CODES
@app.route('/create_qr', methods=['POST'])
def create_qr():
    json_data = request.get_json(force=True)

    title = json_data.get('title', '')
    name = json_data.get('name', '')
    surname = json_data.get('surname', '')
    affiliation = json_data.get('affiliation', '')

    try:
        # Generate QR code for the provided data
        data = f"{name} {surname} {affiliation}"
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        # Save image to BytesIO and encode to base64
        img_stream = BytesIO()
        img.save(img_stream, format="PNG")
        img_base64 = base64.b64encode(img_stream.getvalue()).decode('utf-8')

        # Respond with success and the generated QR code data
        return jsonify({
            'status': 'success',
            'message': 'QR Code generated successfully.',
            'qr_data': {
                'title': title,
                'name': name,
                'surname': surname,
                'affiliation': affiliation,
                'qr_code_base64': img_base64
            }
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'An error occurred: {e}'})



### Function to upload the data to Firebase which is called once the qr code is created
def add_member_to_firestore(member_data):
    doc_ref = db.collection("participants").document("VDHXJiRiVGGNl7FnHCo7")
    doc = doc_ref.get()

    if not doc.exists:
        arrays = {}
    else:
        arrays = doc.to_dict()

    for field in member_data:
        if field not in arrays:
            arrays[field] = []

    arrays['affiliation'].append(member_data.get('affiliation', ''))
    arrays['name'].append(member_data.get('name', ''))
    arrays['surname'].append(member_data.get('surname', ''))
    arrays['title'].append(member_data.get('title', ''))
    arrays['qr_code_base64'].append(member_data.get('qr_code_base64', ''))

    doc_ref.set(arrays)


####################################################################################################
####################################################################################################
#####################################################################################################
## This needs to be worked on
###### Code for the scanning part to mark the attendees
def mark_attendance(qr_code_data):
    # Assuming qr_code_data is a dictionary containing participant information obtained from scanning QR code
    # Example: {'qr_code_base64': 'base64_encoded_image_data', ...}
    query = db.collection("participants").where("qr_code_base64", "==", qr_code_data['qr_code_base64'])
    result = query.get()

    for doc in result:
        doc_ref = db.collection("participants").document(doc.id)
        doc_data = doc.to_dict()
        doc_data['attended_event'] = True
        doc_ref.update(doc_data)


# API endpoint to mark attendance
@app.route('/mark_attendance', methods=['POST'])
def mark_attendance():
    try:
        data = request.get_json()
        qr_code_base64 = data.get('qr_code_base64', '')
        participant_name = data.get('qrData', '')
        print(data)
        print(participant_name)
        # Query Firestore to find the participant with the given QR code
        
        document_id_to_update = "Jane"  # Replace with the actual document ID
        field_name = "Attended"
        field_value = "YES"

        query = db.collection("your_collection").where("id", "==", document_id_to_update, use_field_for_ops=True)
        result = query.get()

        # Update the first document in the result (assuming there is only one document with the specified ID)
        for doc in result:
            doc_ref = db.collection("participants").document(doc.id)
            doc_data = doc.to_dict()

            # Add the field if it doesn't exist
            if field_name not in doc_data:
                doc_ref.update({field_name: field_value})
                print(f"Field '{field_name}' added to document with ID '{document_id_to_update}' with value '{field_value}'.")
            else:
                print(f"Field '{field_name}' already exists in document with ID '{document_id_to_update}'.")

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})




if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3400, debug=True)
