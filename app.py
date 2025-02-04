import os
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
from pymongo import MongoClient
from io import BytesIO
from datetime import datetime
import requests
import uuid
import gridfs

load_dotenv()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024 # 5MB

REMOVE_BG_API_KEY = os.getenv('REMOVE_BG_API_KEY')

# MongoDB connection
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb+srv://cssanju19:sanju123@cluster0.zx6eu.mongodb.net/bg_remover?retryWrites=true&w=majority&appName=Cluster0')
client = MongoClient(MONGODB_URI)
db = client.get_database()
fs = gridfs.GridFS(db)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    response = requests.post(
        'https://api.remove.bg/v1.0/removebg',
        files={'image_file': file},
        data={'size': 'auto'},
        headers={'X-Api-Key': REMOVE_BG_API_KEY}
    )

    if response.status_code == 200:
        original_id = uuid.uuid4().hex
        result_path = os.path.join(app.config['UPLOAD_FOLDER'], f'result_{original_id}.png')
        with open(result_path, 'wb') as f:
            f.write(response.content)

        # Save to MongoDB
        with open(result_path, 'rb') as f:
            result_file = fs.put(f, filename=result_path, metadata={
                'original_id': original_id,
                'uploaded_on': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'original_filename': file.filename,
                'result_path': result_path,
                'size': os.path.getsize(result_path),
                'content_type': 'image/png',
            })

            db.images.insert_one({
                "_id": original_id,
                "filename": file.filename,
                "result_id": result_file,
                "upload_date": datetime.now(),
                "status": "success",
                "size": os.path.getsize(result_path),
            })

        return jsonify({'result': result_path}), 200
    
    else:
        return jsonify({'error': response.json()}), 500
    
if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)