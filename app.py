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

    # Extract barcode data
    barcode_data = []
    for barcode in barcodes:
        x, y, w, h = barcode.rect
        content = barcode.data.decode('utf-8')
        barcode_data.append({
         'content': content,
         'type': barcode.type,
         'coordinates': {'x': x, 'y': y},
         'length': len(content),  # Count the number of characters in the barcode
         'rect': (x, y, w, h)
        })

    # Sort barcodes top-to-bottom, left-to-right
    # barcode_data.sort(key=lambda b: (b['coordinates']['y'], b['coordinates']['x']))
    
		# Sort barcodes left-to-right, top-to-bottom
    barcode_data.sort(key=lambda b: (b['coordinates']['x'], b['coordinates']['y']))

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

    return jsonify({'barcodes': barcode_data, 'image_url': f'/processed/{filename}'})

@app.route('/processed/<filename>')
def processed_file(filename):
    return send_from_directory(app.config['PROCESSED_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)
