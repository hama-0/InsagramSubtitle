import os
import tempfile
import subprocess
import whisper
from flask import Flask, render_template, request, jsonify, send_file, url_for
from googletrans import Translator
import re
from datetime import datetime
import shutil

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'temp_files'
OUTPUT_FOLDER = 'static/output'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Initialize Whisper model and translator
print("Loading Whisper model...")
whisper_model = whisper.load_model("base")
translator = Translator()

FFMPEG_PATH = "ffmpeg.exe"

class VideoSubtitleProcessor:
    def __init__(self, ffmpeg_path=FFMPEG_PATH):
        self.whisper_model = whisper_model
        self.translator = translator
        self.ffmpeg_path = ffmpeg_path

    def download_instagram_video(self, url, output_path):
        """Download Instagram video using yt-dlp"""
        try:
            cmd = [
                'yt-dlp',
                '-o', output_path,
                '--format', 'best[ext=mp4]',
                url
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"yt-dlp error output: {result.stderr}")
                return False
            if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                print(f"Downloaded file not found or empty: {output_path}")
                return False
            return True
        except Exception as e:
            print(f"Error downloading video: {e}")
            return False

    def transcribe_audio(self, video_path):
        """Extract and transcribe audio using Whisper"""
        try:
            result = self.whisper_model.transcribe(video_path)
            return result
        except Exception as e:
            print(f"Error transcribing audio: {e}")
            return None

    def translate_to_arabic(self, text):
        """Translate text to Arabic"""
        try:
            translated = self.translator.translate(text, dest='ar')
            return translated.text
        except Exception as e:
            print(f"Error translating: {e}")
            return text

    def create_srt_file(self, transcription_result, output_path, include_arabic=True):
        """Create SRT subtitle file with optional Arabic translation"""
        try:
            # Save as UTF-8 with BOM for better ffmpeg compatibility on Windows
            with open(output_path, 'w', encoding='utf-8-sig') as f:
                for i, segment in enumerate(transcription_result['segments']):
                    start_time = segment['start']
                    end_time = segment['end']
                    text = segment['text'].strip()
                    # Format timestamps for SRT
                    start_srt = self.format_timestamp(start_time)
                    end_srt = self.format_timestamp(end_time)
                    # Write subtitle entry
                    f.write(f"{i + 1}\n")
                    f.write(f"{start_srt} --> {end_srt}\n")
                    if include_arabic:
                        arabic_text = self.translate_to_arabic(text)
                        print(f"DEBUG: Original: {text}")
                        print(f"DEBUG: Arabic: {arabic_text}")
                        f.write(f"{text}\n")
                        f.write(f"{arabic_text}\n\n")
                    else:
                        f.write(f"{text}\n\n")
            return True
        except Exception as e:
            print(f"Error creating SRT file: {e}")
            return False

    @staticmethod
    def format_timestamp(seconds):
        """Convert seconds to SRT timestamp format"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millisecs = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"

    def burn_subtitles(self, video_path, srt_path, output_path):
        """Burn subtitles into video using ffmpeg"""
        try:
            srt_path_real = os.path.abspath(srt_path)
            # Use relative path with forward slashes
            srt_path_relative = os.path.relpath(srt_path_real, os.getcwd()).replace("\\", "/")
            video_path_ffmpeg = os.path.abspath(video_path)
            output_path_ffmpeg = os.path.abspath(output_path)
            if not os.path.exists(srt_path_real) or os.path.getsize(srt_path_real) == 0:
                print(f"SRT file not found or empty: {srt_path_real}")
                return False
            filter_arg = f"subtitles={srt_path_relative}"
            cmd = [
                self.ffmpeg_path,
                '-i', video_path_ffmpeg,
                '-vf', filter_arg,
                '-c:a', 'copy',
                '-y',
                output_path_ffmpeg
            ]
            print("Running ffmpeg command:", ' '.join(cmd))
            result = subprocess.run(cmd, capture_output=True, text=True)
            print("FFmpeg stdout:", result.stdout)
            if result.returncode != 0:
                print("FFmpeg error output:", result.stderr)
                return False
            if not os.path.exists(output_path_ffmpeg) or os.path.getsize(output_path_ffmpeg) == 0:
                print(f"Output video not found or empty: {output_path_ffmpeg}")
                return False
            return True
        except Exception as e:
            print(f"Error burning subtitles: {e}")
            return False

processor = VideoSubtitleProcessor()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_video():
    try:
        data = request.get_json()
        instagram_url = data.get('url')
        include_arabic = data.get('include_arabic', True)
        
        if not instagram_url:
            return jsonify({'error': 'No URL provided'}), 400
        
        # Generate unique filenames
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        video_filename = f"video_{timestamp}.mp4"
        srt_filename = f"subtitles_{timestamp}.srt"
        output_filename = f"final_{timestamp}.mp4"
        
        video_path = os.path.join(UPLOAD_FOLDER, video_filename)
        srt_path = os.path.join(UPLOAD_FOLDER, srt_filename)
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)
        
        # Step 1: Download Instagram video
        print("Downloading Instagram video...")
        if not processor.download_instagram_video(instagram_url, video_path):
            return jsonify({'error': 'Failed to download Instagram video. Make sure the URL is valid and public.'}), 400
        
        # Step 2: Transcribe audio
        print("Transcribing audio...")
        transcription = processor.transcribe_audio(video_path)
        if not transcription:
            return jsonify({'error': 'Failed to transcribe audio'}), 500
        
        # Step 3: Create SRT file
        print("Creating subtitles...")
        if not processor.create_srt_file(transcription, srt_path, include_arabic):
            return jsonify({'error': 'Failed to create subtitle file'}), 500
        
        # Step 4: Burn subtitles into video
        print("Adding subtitles to video...")
        if not processor.burn_subtitles(video_path, srt_path, output_path):
            return jsonify({'error': 'Failed to add subtitles to video'}), 500
        
        # Clean up temporary files
        try:
            os.remove(video_path)
            os.remove(srt_path)
        except:
            pass
        
        # Return download URL
        download_url = url_for('download_video', filename=output_filename)
        
        return jsonify({
            'success': True,
            'download_url': download_url,
            'message': 'Video processed successfully!' + (' Arabic translation included.' if include_arabic else '')
        })
        
    except Exception as e:
        print(f"Processing error: {e}")
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500

@app.route('/download/<filename>')
def download_video(filename):
    try:
        file_path = os.path.join(OUTPUT_FOLDER, filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True, download_name=f"subtitled_{filename}")
        else:
            return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/cleanup')
def cleanup_files():
    """Clean up old files (optional endpoint)"""
    try:
        # Remove files older than 1 hour
        import time
        current_time = time.time()
        
        for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER]:
            for filename in os.listdir(folder):
                file_path = os.path.join(folder, filename)
                if os.path.isfile(file_path):
                    file_age = current_time - os.path.getctime(file_path)
                    if file_age > 3600:  # 1 hour
                        os.remove(file_path)
        
        return jsonify({'message': 'Cleanup completed'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Check if required tools are available
    try:
        subprocess.run(['yt-dlp', '--version'], capture_output=True, check=True)
        subprocess.run([FFMPEG_PATH, '-version'], capture_output=True, check=True)
        print("✅ All required tools are available")
    except subprocess.CalledProcessError:
        print("❌ Missing required tools. Please install yt-dlp and ffmpeg")
    
    app.run(debug=True, host='0.0.0.0', port=5000)