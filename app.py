from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import yt_dlp
import os
import uuid

app = Flask(__name__)
CORS(app)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

YT_EXTRA = {
    'extractor_args': {
        'youtube': {
            'player_client': ['android', 'ios'],
        }
    }
}

@app.route('/')
def home():
    return jsonify({'status': 'Server running'})


@app.route('/get-info', methods=['POST'])
def get_info():
    data = request.json
    url = data.get('url')

    if not url:
        return jsonify({'error': 'URL missing'}), 400

    try:
        ydl_opts = {'quiet': True, 'no_warnings': True}
        ydl_opts.update(YT_EXTRA)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            formats = []
            for f in info.get('formats', []):
                if f.get('vcodec') != 'none' or f.get('acodec') != 'none':
                    formats.append({
                        'format_id': f.get('format_id'),
                        'ext': f.get('ext'),
                        'resolution': f.get('resolution', 'audio'),
                        'filesize': f.get('filesize', 0)
                    })

            return jsonify({
                'title': info.get('title'),
                'thumbnail': info.get('thumbnail'),
                'duration': info.get('duration'),
                'formats': formats[:10]
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/download', methods=['POST'])
def download():
    data = request.json
    url = data.get('url')
    format_id = data.get('format_id', 'best')

    try:
        unique_id = str(uuid.uuid4())
        outtmpl = os.path.join(DOWNLOAD_DIR, unique_id + ".%(ext)s")

        ydl_opts = {
            'quiet': True,
            'format': format_id + '+bestaudio/best',
            'merge_output_format': 'mp4',
            'outtmpl': outtmpl,
        }
        ydl_opts.update(YT_EXTRA)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        final_file = None
        for f in os.listdir(DOWNLOAD_DIR):
            if f.startswith(unique_id):
                final_file = f
                break

        if not final_file:
            return jsonify({'error': 'File not created'}), 500

        download_link = request.host_url + "files/" + final_file

        return jsonify({
            'download_url': download_link,
            'title': info.get('title'),
            'ext': 'mp4'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/files/<filename>')
def serve_file(filename):
    file_path = os.path.join(DOWNLOAD_DIR, filename)
    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404

    file_size = os.path.getsize(file_path)
    response = send_from_directory(DOWNLOAD_DIR, filename, as_attachment=True)
    response.headers['Content-Length'] = str(file_size)
    response.headers['Accept-Ranges'] = 'bytes'
    return response


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
