import pandas as pd
import pyodbc
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import os
import cv2
from pyzbar.pyzbar import decode

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['PROCESSED_FOLDER'] = 'processed'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['PROCESSED_FOLDER'], exist_ok=True)

# MSSQL configuration
DB_CONFIG = {
    'server': '127.0.0.1',
    'database': 'LabelAnalysisDB',
    'username': 'label',
    'password': 'label',
    'driver': '{ODBC Driver 17 for SQL Server}'
}

def read_field_list_from_file(filepath):
    with open(filepath, 'r') as file:
        lines = file.readlines()
    # Remove whitespace and empty lines
    field_list = [line.strip() for line in lines if line.strip()]
    return [''] + field_list

@app.route('/')
def index():
    field_list = read_field_list_from_file('MeaningList.txt')
    return render_template('index.html', field_list=field_list)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400

    file = request.files['image']
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    # Analyze the image
    image = cv2.imread(filepath)
    barcodes = decode(image)

    # Extract barcode data
    barcode_data = []
    for barcode in barcodes:
        x, y, w, h = barcode.rect
        content = barcode.data.decode('utf-8')
        barcode_data.append({
         'content': content,
         'meaning':'',
         'type': barcode.type,
         'x': x,
         'y': y,
         'length': len(content),  # Count the number of characters in the barcode
         'rect': (x, y, w, h)
        })

    # Sort barcodes top-to-bottom, left-to-right
    barcode_data.sort(key=lambda b: (b['y'], b['x']))
        
	# Sort barcodes left-to-right, top-to-bottom
    # barcode_data.sort(key=lambda b: (b['x'], b['y']))

    # Annotate the image
    for idx, barcode in enumerate(barcode_data, start=1):
        x, y, w, h = barcode['rect']
        cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(image, f"{idx}", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

    processed_path = os.path.join(app.config['PROCESSED_FOLDER'], filename)
    cv2.imwrite(processed_path, image)

    # Add reading order to response
    for idx, barcode in enumerate(barcode_data, start=1):
        barcode['order'] = idx

    if(barcode_data != []) :
        x_max = max(b["x"] + b["rect"][2] for b in barcode_data)
        y_max = max(b["y"] + b["rect"][3] for b in barcode_data)
        x_min = min(b["x"] for b in barcode_data)
        y_min = min(b["y"] for b in barcode_data)
        for b in barcode_data:
            b["normalized_x"] = (b["x"] - x_min) / (x_max - x_min)
            b["normalized_y"] = (b["y"] - y_min) / (y_max - y_min)

    return jsonify({'barcodes': barcode_data, 'image_url': f'/processed/{filename}'})

@app.route('/processed/<filename>')
def processed_file(filename):
    return send_from_directory(app.config['PROCESSED_FOLDER'], filename)

@app.route('/submit', methods=['POST'])
def submit_data():
    data = request.json
    vendor = data.get('vendor')
    table_data = data.get('tableData')
    qty = data.get('qty')

    # Save data to MSSQL
    conn = pyodbc.connect(
        f"DRIVER={DB_CONFIG['driver']};SERVER={DB_CONFIG['server']};DATABASE={DB_CONFIG['database']};"
        f"UID={DB_CONFIG['username']};PWD={DB_CONFIG['password']}"
    )
    cursor = conn.cursor()

    cursor.execute("""
            INSERT INTO Labels (vendor_name, sap_vendor_name, revision, barcode_count)
            VALUES (?, ?, ?, ?)
        """, vendor, "", "1", qty)

    for row in table_data:
        cursor.execute("""
            INSERT INTO Barcodes (vendor_name, read_order, content, meaning, barcode_type, normalized_x, normalized_y, length)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, vendor, row['read_order'], row['content'], row['meaning'], row['type'], row['x'], row['y'], row['length'])

    conn.commit()
    conn.close()
    return jsonify({'message': 'Data saved successfully'})

if __name__ == '__main__':
    app.run(debug=True)
