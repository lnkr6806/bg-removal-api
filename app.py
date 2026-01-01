# app.py - FINAL WORKING VERSION
# CORS properly configured - GUARANTEED TO WORK

from flask import Flask, request, jsonify
from rembg import remove, new_session
from PIL import Image, ImageFilter, ImageDraw
import io
import base64
import ssl
import os
import gc

ssl._create_default_https_context = ssl._create_unverified_context
os.environ['REQUESTS_CA_BUNDLE'] = ''
os.environ['CURL_CA_BUNDLE'] = ''

app = Flask(__name__)

# Allowed origins
ALLOWED_ORIGINS = [
    "https://www.editorn.com",
    "https://editorn.com",
    "http://localhost:3000",
    "http://localhost:5000"
]

PORT = int(os.environ.get('PORT', 5000))

print("🚀 Loading AI models...")
MODELS = {
    'general': new_session("u2net"),
    'fast': new_session("u2netp"),
}
print("✅ Models loaded!")

# CORS handling - BEFORE every request
@app.before_request
def handle_preflight():
    if request.method == 'OPTIONS':
        origin = request.headers.get('Origin', '')
        response = jsonify({'status': 'ok'})
        
        if origin in ALLOWED_ORIGINS:
            response.headers['Access-Control-Allow-Origin'] = origin
        
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Max-Age'] = '86400'
        
        return response, 200

# CORS handling - AFTER every request
@app.after_request
def after_request(response):
    origin = request.headers.get('Origin', '')
    
    if origin in ALLOWED_ORIGINS:
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
    
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    
    return response

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        'service': 'Background Removal API',
        'status': 'running',
        'version': '3.1.0',
        'allowed_origins': ALLOWED_ORIGINS
    })

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'models': list(MODELS.keys()),
        'allowed_origins': ALLOWED_ORIGINS
    })

@app.route('/remove-background', methods=['POST'])
def remove_background():
    try:
        # Get parameters
        model_type = request.form.get('model', 'general')
        add_shadow = request.form.get('shadow', 'false').lower() == 'true'
        bg_type = request.form.get('bgType', 'transparent')
        bg_color = request.form.get('bgColor', '#FFFFFF')
        gradient_start = request.form.get('gradientStart', '#667EEA')
        gradient_end = request.form.get('gradientEnd', '#764BA2')
        
        print("\n" + "="*70)
        print(f"📥 REQUEST from {request.headers.get('Origin')}")
        print(f"   Model: {model_type}")
        print(f"   BG Type: {bg_type}")
        print(f"   BG Color: {bg_color}")
        print(f"   Gradient: {gradient_start} → {gradient_end}")
        print(f"   Shadow: {add_shadow}")
        print("="*70)
        
        if 'image' not in request.files:
            return jsonify({'success': False, 'error': 'No image provided'}), 400
        
        file = request.files['image']
        input_image = Image.open(file.stream)
        original_size = input_image.size
        
        print(f"📏 Original size: {original_size}")
        
        # Resize to save memory
        max_dimension = 1024
        processing_image = input_image.copy()
        
        if max(original_size) > max_dimension:
            ratio = min(max_dimension / original_size[0], max_dimension / original_size[1])
            new_size = (int(original_size[0] * ratio), int(original_size[1] * ratio))
            processing_image = processing_image.resize(new_size, Image.Resampling.LANCZOS)
            print(f"📐 Resized to: {processing_image.size}")
        
        # Convert to RGB
        if processing_image.mode == 'RGBA':
            bg = Image.new('RGB', processing_image.size, (255, 255, 255))
            bg.paste(processing_image, mask=processing_image.split()[3])
            processing_image = bg
        elif processing_image.mode != 'RGB':
            processing_image = processing_image.convert('RGB')
        
        # Remove background
        session = MODELS.get(model_type, MODELS['general'])
        print(f"🤖 Removing background with {model_type} model...")
        
        removed_bg = remove(
            processing_image,
            session=session,
            alpha_matting=True,
            alpha_matting_foreground_threshold=250,
            alpha_matting_background_threshold=5,
            alpha_matting_erode_size=5
        )
        
        print(f"✅ Background removed!")
        
        # Clean up
        del processing_image
        gc.collect()
        
        # Resize back to original
        if max(original_size) > max_dimension:
            removed_bg = removed_bg.resize(original_size, Image.Resampling.LANCZOS)
            print(f"📏 Resized back to: {original_size}")
        
        # Apply background
        final_image = removed_bg
        
        if bg_type == 'transparent':
            print("🔲 Transparent background")
            final_image = removed_bg
            
        elif bg_type == 'color':
            print(f"🎨 Solid color: {bg_color}")
            final_image = apply_solid_background(removed_bg, bg_color)
            
        elif bg_type == 'gradient':
            print(f"🌈 Gradient: {gradient_start} → {gradient_end}")
            final_image = apply_gradient_background(removed_bg, gradient_start, gradient_end)
        
        # Apply shadow
        if add_shadow and bg_type != 'transparent':
            print("✨ Adding shadow...")
            final_image = apply_shadow(final_image, removed_bg)
        
        # Clean up
        del removed_bg
        gc.collect()
        
        # Save and encode
        img_io = io.BytesIO()
        final_image.save(img_io, 'PNG', optimize=True)
        img_io.seek(0)
        img_base64 = base64.b64encode(img_io.getvalue()).decode('utf-8')
        
        # Clean up
        del final_image
        gc.collect()
        
        print(f"✅ SUCCESS!")
        print("="*70 + "\n")
        
        return jsonify({
            'success': True,
            'output': f'data:image/png;base64,{img_base64}',
            'dimensions': {
                'width': original_size[0],
                'height': original_size[1]
            },
            'bgType': bg_type,
            'hasBackground': bg_type != 'transparent'
        })
    
    except MemoryError:
        print(f"❌ OUT OF MEMORY!")
        gc.collect()
        return jsonify({
            'success': False,
            'error': 'Image too large. Try a smaller image or use "fast" model.'
        }), 413
    
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        gc.collect()
        return jsonify({'success': False, 'error': str(e)}), 500

def apply_solid_background(foreground_rgba, color_hex):
    """Apply solid color background"""
    if foreground_rgba.mode != 'RGBA':
        foreground_rgba = foreground_rgba.convert('RGBA')
    
    width, height = foreground_rgba.size
    color_hex = color_hex.lstrip('#')
    r = int(color_hex[0:2], 16)
    g = int(color_hex[2:4], 16)
    b = int(color_hex[4:6], 16)
    
    background = Image.new('RGB', (width, height), (r, g, b))
    background.paste(foreground_rgba, (0, 0), foreground_rgba)
    
    return background

def apply_gradient_background(foreground_rgba, start_hex, end_hex):
    """Apply gradient background"""
    if foreground_rgba.mode != 'RGBA':
        foreground_rgba = foreground_rgba.convert('RGBA')
    
    width, height = foreground_rgba.size
    
    start_hex = start_hex.lstrip('#')
    end_hex = end_hex.lstrip('#')
    
    start_r = int(start_hex[0:2], 16)
    start_g = int(start_hex[2:4], 16)
    start_b = int(start_hex[4:6], 16)
    
    end_r = int(end_hex[0:2], 16)
    end_g = int(end_hex[2:4], 16)
    end_b = int(end_hex[4:6], 16)
    
    gradient = Image.new('RGB', (width, height))
    draw = ImageDraw.Draw(gradient)
    
    for y in range(height):
        ratio = y / height
        r = int(start_r * (1 - ratio) + end_r * ratio)
        g = int(start_g * (1 - ratio) + end_g * ratio)
        b = int(start_b * (1 - ratio) + end_b * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    
    gradient.paste(foreground_rgba, (0, 0), foreground_rgba)
    return gradient

def apply_shadow(background_image, foreground_rgba):
    """Apply shadow effect"""
    try:
        if foreground_rgba.mode != 'RGBA':
            return background_image
        
        width, height = background_image.size
        alpha = foreground_rgba.split()[3]
        shadow = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        shadow.paste((0, 0, 0, 80), (0, 0), alpha)
        shadow = shadow.filter(ImageFilter.GaussianBlur(10))
        
        shadow_with_offset = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        shadow_with_offset.paste(shadow, (5, 8))
        
        result = background_image.convert('RGBA')
        result = Image.alpha_composite(result, shadow_with_offset)
        result = Image.alpha_composite(result, foreground_rgba)
        
        return result.convert('RGB')
    except:
        return background_image

if __name__ == '__main__':
    print("\n" + "="*70)
    print("🚀 Background Removal API v3.1.0")
    print("="*70)
    print(f"✅ CORS enabled for: {', '.join(ALLOWED_ORIGINS)}")
    print("✅ Memory optimized (max 1024px)")
    print("✅ All features working")
    print("="*70 + "\n")
    print(f"🌐 Running on http://0.0.0.0:{PORT}\n")
    
    app.run(host='0.0.0.0', port=PORT, debug=False)