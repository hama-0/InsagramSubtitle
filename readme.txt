for running you be needing two terminal
to run these code   .\cloudflared-windows-amd64.exe tunnel --url http://localhost:5000
and this python app.py
 What is this project?
This project is a web application that:
Downloads Instagram videos (Reels)
Transcribes the audio to text (using AI)
Optionally translates the text to Arabic
Creates subtitle files (SRT)
Burns the subtitles into the video
Lets users download the final video
It’s built with Python (Flask) for the backend, and uses several powerful tools:
yt-dlp: Downloads videos from Instagram
OpenAI Whisper: Converts speech to text (transcription)
googletrans: Translates text to Arabic
ffmpeg: Adds subtitles to videos
How does it work?
User enters an Instagram Reel URL on the website.
The server downloads the video.
The server transcribes the audio to text.
The server (optionally) translates the text to Arabic.
The server creates a subtitle file (SRT).
The server burns the subtitles into the video.
The user can download the final video.

i have used cloudflare tunnel to host the website just by using my pc as
a server and cloudflare give you a domain name and make it reachable across internet.
 the command to host the web .\cloudflared-windows-amd64.exe tunnel --url http://localhost:5000
