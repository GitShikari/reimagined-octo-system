import os
import base64
from urllib.parse import unquote
from flask import Flask, render_template_string, request, abort

app = Flask(__name__)

# HTML template for video player
PLAYER_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ filename }} - Terabox Player</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }

        .container {
            max-width: 1200px;
            width: 100%;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            overflow: hidden;
            backdrop-filter: blur(10px);
        }

        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px 30px;
            display: flex;
            align-items: center;
            gap: 15px;
        }

        .header h1 {
            font-size: 1.5rem;
            font-weight: 600;
            word-break: break-word;
        }

        .video-wrapper {
            position: relative;
            width: 100%;
            background: #000;
        }

        video {
            width: 100%;
            height: auto;
            display: block;
            max-height: 70vh;
        }

        .controls {
            padding: 20px 30px;
        }

        .info-section {
            margin-bottom: 20px;
        }

        .info-label {
            font-size: 0.875rem;
            color: #666;
            margin-bottom: 5px;
            font-weight: 500;
        }

        .info-value {
            font-size: 1rem;
            color: #333;
            word-break: break-all;
        }

        .button-group {
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
        }

        .btn {
            flex: 1;
            min-width: 150px;
            padding: 15px 25px;
            border: none;
            border-radius: 12px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
        }

        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }

        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 25px rgba(102, 126, 234, 0.4);
        }

        .btn-secondary {
            background: #f3f4f6;
            color: #333;
        }

        .btn-secondary:hover {
            background: #e5e7eb;
            transform: translateY(-2px);
        }

        .loading {
            text-align: center;
            padding: 40px;
            color: #666;
        }

        .spinner {
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .error {
            background: #fee;
            color: #c33;
            padding: 15px;
            border-radius: 10px;
            margin: 20px;
            text-align: center;
        }

        @media (max-width: 768px) {
            .header h1 {
                font-size: 1.2rem;
            }

            .button-group {
                flex-direction: column;
            }

            .btn {
                width: 100%;
            }

            video {
                max-height: 50vh;
            }
        }

        .icon {
            font-size: 1.2rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <span class="icon">🎬</span>
            <h1>{{ filename }}</h1>
        </div>

        <div class="video-wrapper">
            <video id="videoPlayer" controls autoplay preload="metadata">
                <source src="{{ video_url }}" type="video/mp4">
                Your browser does not support the video tag.
            </video>
        </div>

        <div class="controls">
            <div class="info-section">
                <div class="info-label">File Name</div>
                <div class="info-value">{{ filename }}</div>
            </div>

            <div class="button-group">
                <a href="{{ video_url }}" class="btn btn-primary" download="{{ filename }}">
                    <span class="icon">⬇️</span>
                    Download Video
                </a>
                <button onclick="copyLink()" class="btn btn-secondary">
                    <span class="icon">📋</span>
                    Copy Link
                </button>
            </div>
        </div>
    </div>

    <script>
        const video = document.getElementById('videoPlayer');
        
        // Handle video errors
        video.addEventListener('error', function(e) {
            console.error('Video error:', e);
            const wrapper = document.querySelector('.video-wrapper');
            wrapper.innerHTML = '<div class="error">Failed to load video. The link might have expired. Please try downloading instead.</div>';
        });

        // Copy link function
        function copyLink() {
            const url = "{{ video_url }}";
            
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(url).then(function() {
                    alert('Link copied to clipboard!');
                }).catch(function(err) {
                    fallbackCopy(url);
                });
            } else {
                fallbackCopy(url);
            }
        }

        function fallbackCopy(text) {
            const textArea = document.createElement('textarea');
            textArea.value = text;
            textArea.style.position = 'fixed';
            textArea.style.left = '-999999px';
            document.body.appendChild(textArea);
            textArea.select();
            
            try {
                document.execCommand('copy');
                alert('Link copied to clipboard!');
            } catch (err) {
                alert('Failed to copy link. Please copy manually.');
            }
            
            document.body.removeChild(textArea);
        }

        // Save playback position
        video.addEventListener('timeupdate', function() {
            localStorage.setItem('videoPosition_{{ video_id }}', video.currentTime);
        });

        // Restore playback position
        window.addEventListener('load', function() {
            const savedPosition = localStorage.getItem('videoPosition_{{ video_id }}');
            if (savedPosition) {
                video.currentTime = parseFloat(savedPosition);
            }
        });
    </script>
</body>
</html>
"""

# Error template
ERROR_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Error - Terabox Player</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }

        .error-container {
            max-width: 500px;
            background: white;
            border-radius: 20px;
            padding: 40px;
            text-align: center;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        }

        .error-icon {
            font-size: 4rem;
            margin-bottom: 20px;
        }

        h1 {
            color: #333;
            margin-bottom: 15px;
            font-size: 1.8rem;
        }

        p {
            color: #666;
            line-height: 1.6;
            margin-bottom: 30px;
        }

        .btn {
            display: inline-block;
            padding: 15px 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-decoration: none;
            border-radius: 12px;
            font-weight: 600;
            transition: transform 0.3s ease;
        }

        .btn:hover {
            transform: translateY(-2px);
        }
    </style>
</head>
<body>
    <div class="error-container">
        <div class="error-icon">❌</div>
        <h1>{{ title }}</h1>
        <p>{{ message }}</p>
    </div>
</body>
</html>
"""


def decode_url(encoded_url: str) -> str:
    """Decode the base64 encoded URL"""
    try:
        return base64.urlsafe_b64decode(encoded_url.encode()).decode()
    except Exception as e:
        return None


@app.route('/')
def index():
    """Home page"""
    return render_template_string(ERROR_TEMPLATE,
        title="Terabox Player",
        message="Use the Telegram bot to generate player links."
    )


@app.route('/player')
def player():
    """Video player page"""
    try:
        # Get encoded video URL from query parameter
        encoded_url = request.args.get('v')
        filename = request.args.get('name', 'Video')
        
        if not encoded_url:
            return render_template_string(ERROR_TEMPLATE,
                title="Missing Parameter",
                message="No video URL provided."
            ), 400
        
        # Decode the video URL
        video_url = decode_url(encoded_url)
        
        if not video_url:
            return render_template_string(ERROR_TEMPLATE,
                title="Invalid URL",
                message="The provided video URL is invalid or corrupted."
            ), 400
        
        # Decode filename if URL encoded
        filename = unquote(filename)
        
        # Generate a unique ID for this video (for localStorage)
        video_id = abs(hash(video_url)) % (10 ** 8)
        
        # Render the player template
        return render_template_string(
            PLAYER_TEMPLATE,
            video_url=video_url,
            filename=filename,
            video_id=video_id
        )
        
    except Exception as e:
        return render_template_string(ERROR_TEMPLATE,
            title="Error",
            message=f"An error occurred: {str(e)}"
        ), 500


@app.route('/health')
def health():
    """Health check endpoint"""
    return {'status': 'ok'}, 200


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
