from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
import os
import cv2
from pyzbar.pyzbar import decode

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

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
    barcode_data = []

    for barcode in barcodes:
        if barcode.type:  # Ensure it's a valid barcode
            x, y, w, h = barcode.rect
            barcode_data.append({
                'content': barcode.data.decode('utf-8'),
                'type': barcode.type,
                'coordinates': {'x': x, 'y': y}
            })

    # Clean up uploaded file (optional)
    os.remove(filepath)

    return jsonify({'barcodes': barcode_data})

if __name__ == '__main__':
    app.run(debug=True)
