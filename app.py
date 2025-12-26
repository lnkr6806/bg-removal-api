# app.py - PRODUCTION READY WITH CORS FIX

from flask import Flask, request, jsonify
from flask_cors import CORS
from rembg import remove, new_session
from PIL import Image
import io
import base64
import ssl
import os

# Disable SSL verification (fix for PostgreSQL issue)
ssl._create_default_https_context = ssl._create_unverified_context
os.environ['REQUESTS_CA_BUNDLE'] = ''
os.environ['CURL_CA_BUNDLE'] = ''

app = Flask(__name__)

# ⚡ CORS FIX: Allow your production domain!
CORS(app, resources={
    r"/*": {
        "origins": [
            "https://www.editorn.com",
            "https://editorn.com",
            "http://localhost:3000",
            "http://localhost:5000"
        ],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"],
        "supports_credentials": True
    }
})

# Get port from environment (Railway provides this)
PORT = int(os.environ.get('PORT', 5000))

# ⚡ SPEED OPTIMIZATION: Pre-load model
print("🚀 Loading AI model... (this takes 10 seconds, but only happens once!)")
session = new_session("u2net")
print("✅ Model loaded! API is ready for FAST processing!")

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        'service': 'Background Removal API',
        'status': 'running',
        'version': '1.0.0',
        'endpoints': {
            'health': '/health',
            'remove_background': '/remove-background (POST)'
        }
    })

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'model_loaded': True})

@app.route('/remove-background', methods=['POST', 'OPTIONS'])
def remove_background():
    # Handle OPTIONS request (CORS preflight)
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200
    
    try:
        print("⚡ Received request!")
        
        if 'image' not in request.files:
            return jsonify({'error': 'No image provided'}), 400
        
        file = request.files['image']
        print(f"📁 Processing: {file.filename}")
        
        # Read image
        input_image = Image.open(file.stream)
        original_size = input_image.size
        print(f"📏 Original size: {original_size}")
        
        # Resize large images for speed
        max_size = 1024
        if max(original_size) > max_size:
            ratio = max_size / max(original_size)
            new_size = tuple(int(dim * ratio) for dim in original_size)
            input_image = input_image.resize(new_size, Image.Resampling.LANCZOS)
            print(f"⚡ Resized to: {new_size}")
        
        # Convert RGBA to RGB if needed
        if input_image.mode == 'RGBA':
            background = Image.new('RGB', input_image.size, (255, 255, 255))
            background.paste(input_image, mask=input_image.split()[3])
            input_image = background
        
        print("🤖 Removing background with AI...")
        
        # Remove background
        output_image = remove(input_image, session=session)
        
        # Resize back to original size
        if max(original_size) > max_size:
            output_image = output_image.resize(original_size, Image.Resampling.LANCZOS)
            print(f"📏 Resized back to: {original_size}")
        
        print("✅ Background removed!")
        
        # Convert to base64
        img_io = io.BytesIO()
        output_image.save(img_io, 'PNG', optimize=False, compress_level=1)
        img_io.seek(0)
        img_base64 = base64.b64encode(img_io.getvalue()).decode('utf-8')
        
        print("🎉 Sending response")
        
        response = jsonify({
            'success': True,
            'output': f'data:image/png;base64,{img_base64}'
        })
        
        # Add CORS headers to response
        response.headers.add('Access-Control-Allow-Origin', request.headers.get('Origin', '*'))
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        
        return response
    
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        
        error_response = jsonify({'success': False, 'error': str(e)})
        error_response.headers.add('Access-Control-Allow-Origin', request.headers.get('Origin', '*'))
        
        return error_response, 500

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 Background Removal API - PRODUCTION MODE")
    print("="*60)
    print("✅ Model pre-loaded (FAST mode enabled!)")
    print("✅ CORS configured for www.editorn.com")
    print("✅ Image resizing enabled (max 1024px)")
    print("✅ Optimized PNG compression")
    print("🔥 Expected speed: 1-3 seconds per image!")
    print("="*60 + "\n")
    print(f"🌐 Starting API on http://0.0.0.0:{PORT}\n")
    
    app.run(host='0.0.0.0', port=PORT, debug=False)