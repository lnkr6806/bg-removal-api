# app.py - PRODUCTION READY!

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

# CORS configuration for production
CORS(app, resources={
    r"/*": {
        "origins": "*",  # In production, replace with your domain
        "methods": ["GET", "POST"],
        "allow_headers": ["Content-Type"]
    }
})

# Get port from environment (for Railway, Render, etc.)
PORT = int(os.environ.get('PORT', 5000))

# Determine if running in production
DEBUG = os.environ.get('FLASK_ENV', 'production') == 'development'

# Pre-load AI model for speed
print("🚀 Loading AI model... (takes 10 seconds)")
try:
    session = new_session("u2net")
    print("✅ Model loaded successfully!")
    MODEL_LOADED = True
except Exception as e:
    print(f"⚠️ Warning: Could not pre-load model: {e}")
    print("⚠️ Model will load on first request")
    session = None
    MODEL_LOADED = False

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
    return jsonify({
        'status': 'healthy',
        'model_loaded': MODEL_LOADED,
        'debug_mode': DEBUG
    })

@app.route('/remove-background', methods=['POST'])
def remove_background():
    try:
        print("⚡ Received background removal request")
        
        if 'image' not in request.files:
            return jsonify({'error': 'No image provided'}), 400
        
        file = request.files['image']
        
        if not file.filename:
            return jsonify({'error': 'Empty filename'}), 400
        
        print(f"📁 Processing: {file.filename}")
        
        # Read image
        input_image = Image.open(file.stream)
        original_size = input_image.size
        print(f"📏 Original size: {original_size}")
        
        # Resize large images for faster processing
        max_size = 1024
        if max(original_size) > max_size:
            ratio = max_size / max(original_size)
            new_size = tuple(int(dim * ratio) for dim in original_size)
            input_image = input_image.resize(new_size, Image.Lanczos)
            print(f"⚡ Resized to: {new_size}")
        
        # Convert RGBA to RGB if needed
        if input_image.mode == 'RGBA':
            background = Image.new('RGB', input_image.size, (255, 255, 255))
            background.paste(input_image, mask=input_image.split()[3])
            input_image = background
        
        print("🤖 Removing background with AI...")
        
        # Remove background (use pre-loaded session if available)
        if session:
            output_image = remove(input_image, session=session)
        else:
            output_image = remove(input_image)
        
        # Resize back to original size
        if max(original_size) > max_size:
            output_image = output_image.resize(original_size, Image.Lanczos)
            print(f"📏 Resized back to: {original_size}")
        
        print("✅ Background removed!")
        
        # Convert to base64
        img_io = io.BytesIO()
        output_image.save(img_io, 'PNG', optimize=False, compress_level=1)
        img_io.seek(0)
        img_base64 = base64.b64encode(img_io.getvalue()).decode('utf-8')
        
        print("🎉 Sending response")
        return jsonify({
            'success': True,
            'output': f'data:image/png;base64,{img_base64}',
            'original_size': original_size
        })
    
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Endpoint not found',
        'available_endpoints': {
            'home': '/',
            'health': '/health',
            'remove_background': '/remove-background (POST)'
        }
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'error': 'Internal server error',
        'message': str(error)
    }), 500

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 Background Removal API - PRODUCTION MODE")
    print("="*60)
    print(f"✅ Model pre-loaded: {MODEL_LOADED}")
    print(f"✅ Debug mode: {DEBUG}")
    print(f"✅ Port: {PORT}")
    print("🔥 Expected speed: 1-3 seconds per image!")
    print("="*60 + "\n")
    print(f"🌐 Starting API on http://0.0.0.0:{PORT}\n")
    
    app.run(host='0.0.0.0', port=PORT, debug=DEBUG)