#!/usr/bin/env python3
"""
Camera Streaming HTTP Server
"""

import os
import sys
import json
import time
import signal
import threading
import zipfile
from io import BytesIO
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from socketserver import ThreadingMixIn
import struct
import hashlib
import base64

from camera import CameraCapture
from settings import Settings

class WebSocketClient:
    def __init__(self, sock):
        self.sock = sock
        self.connected = True
    
    def send(self, data):
        try:
            if isinstance(data, str):
                data = data.encode('utf-8')
            frame = bytearray()
            frame.append(0x82)
            if len(data) < 126:
                frame.append(len(data))
            elif len(data) < 65536:
                frame.append(126)
                frame.extend(struct.pack('>H', len(data)))
            else:
                frame.append(127)
                frame.extend(struct.pack('>Q', len(data)))
            frame.extend(data)
            self.sock.sendall(bytes(frame))
        except:
            self.connected = False
    
    def close(self):
        self.connected = False
        try:
            self.sock.close()
        except:
            pass

class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    allow_reuse_address = True
    daemon_threads = True

# Global state
class AppState:
    def __init__(self):
        self.camera = None
        self.settings = None
        self.recording = False
        self.recording_frames = []
        self.static_dir = None
        self.ws_clients = []
        self.browser_frame = None
        self.use_browser_capture = False
        self.frame_lock = threading.Lock()
        self.current_fps = 0
        self.fps_counter = 0
        self.fps_timer = time.time()
        self.last_browser_frame_time = 0

app = AppState()

class CameraHandler(BaseHTTPRequestHandler):
    
    def _send_response(self, code, content_type='text/html', body=None, headers=None):
        try:
            self.send_response(code)
            self.send_header('Content-Type', content_type)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            
            if headers:
                for key, value in headers.items():
                    self.send_header(key, value)
            
            if body:
                if isinstance(body, str):
                    body = body.encode('utf-8')
                self.send_header('Content-Length', len(body))
            
            self.end_headers()
            
            if body:
                self.wfile.write(body)
                self.wfile.flush()
        except:
            pass
    
    def _read_body(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                return self.rfile.read(content_length)
        except:
            pass
        return b'{}'
    
    def _handle_websocket_upgrade(self):
        try:
            key = self.headers.get('Sec-WebSocket-Key', '')
            if not key:
                return False
            
            magic = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
            accept_key = base64.b64encode(
                hashlib.sha1((key + magic).encode()).digest()
            ).decode()
            
            self.send_response(101)
            self.send_header('Upgrade', 'websocket')
            self.send_header('Connection', 'Upgrade')
            self.send_header('Sec-WebSocket-Accept', accept_key)
            self.end_headers()
            
            client = WebSocketClient(self.request)
            app.ws_clients.append(client)
            
            while client.connected:
                try:
                    header = self.request.recv(2)
                    if not header or len(header) < 2:
                        break
                    
                    opcode = header[0] & 0x0F
                    if opcode == 0x8:
                        break
                    
                    masked = header[1] & 0x80
                    length = header[1] & 0x7F
                    
                    if length == 126:
                        length = struct.unpack('>H', self.request.recv(2))[0]
                    elif length == 127:
                        length = struct.unpack('>Q', self.request.recv(8))[0]
                    
                    if masked:
                        mask_key = self.request.recv(4)
                        data = self.request.recv(length)
                        data = bytes(b ^ mask_key[i % 4] for i, b in enumerate(data))
                    else:
                        data = self.request.recv(length)
                    
                    if data and app.use_browser_capture:
                        # Store frame directly without processing for speed
                        with app.frame_lock:
                            app.browser_frame = data
                            app.last_browser_frame_time = time.time()
                        
                        # Update FPS
                        app.fps_counter += 1
                        now = time.time()
                        if now - app.fps_timer >= 1.0:
                            app.current_fps = app.fps_counter
                            app.fps_counter = 0
                            app.fps_timer = now
                        
                        if app.recording:
                            app.recording_frames.append(data)
                    
                except Exception as e:
                    break
            
            if client in app.ws_clients:
                app.ws_clients.remove(client)
            client.close()
            return True
            
        except Exception as e:
            print(f"WebSocket error: {e}")
            return False
    
    def log_message(self, format, *args):
        # Reduced logging
        if '/stream' not in self.path and '/api/stats' not in self.path:
            print(f"[{self.log_date_time_string()}] {self.path}")
    
    def do_OPTIONS(self):
        self._send_response(200)
    
    def do_GET(self):
        try:
            if self.headers.get('Upgrade', '').lower() == 'websocket':
                if self._handle_websocket_upgrade():
                    return
            
            parsed = urlparse(self.path)
            path = parsed.path
            
            if path == '/api/settings':
                self._handle_get_settings()
            elif path == '/api/stats':
                self._handle_get_stats()
            elif path == '/stream':
                self._handle_stream()
            elif path == '/snapshot':
                self._handle_snapshot()
            elif path == '/recording/start':
                self._handle_recording_start()
            elif path == '/recording/stop':
                self._handle_recording_stop()
            elif path == '/download/zip':
                self._handle_download_zip()
            elif path == '/' or path == '':
                self._serve_file('index.html')
            elif path == '/capture':
                self._serve_file('capture.html')
            elif path.startswith('/'):
                self._serve_file(path[1:])
            else:
                self._send_response(404, body='Not Found')
                
        except Exception as e:
            print(f"GET Error: {e}")
    
    def do_POST(self):
        try:
            parsed = urlparse(self.path)
            path = parsed.path
            body = self._read_body()
            
            try:
                data = json.loads(body)
            except:
                data = {}
            
            if path == '/api/settings':
                self._handle_post_settings(data)
            elif path == '/api/command':
                self._handle_command(data)
            else:
                self._send_response(404, body='Not Found')
                
        except Exception as e:
            print(f"POST Error: {e}")
    
    def _serve_file(self, filename):
        try:
            filename = filename.split('?')[0]
            filename = os.path.basename(filename)
            if not filename:
                filename = 'index.html'
            
            filepath = os.path.join(app.static_dir, filename)
            
            if not os.path.exists(filepath):
                self._send_response(404, body='Not Found')
                return
            
            content_types = {
                '.html': 'text/html; charset=utf-8',
                '.css': 'text/css; charset=utf-8',
                '.js': 'application/javascript; charset=utf-8',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.ico': 'image/x-icon',
                '.svg': 'image/svg+xml',
                '.json': 'application/json'
            }
            
            ext = os.path.splitext(filename)[1].lower()
            content_type = content_types.get(ext, 'application/octet-stream')
            
            with open(filepath, 'rb') as f:
                content = f.read()
            
            headers = {}
            if ext in ['.jpg', '.jpeg', '.png', '.gif', '.ico', '.svg']:
                headers['Cache-Control'] = 'public, max-age=3600'
            else:
                headers['Cache-Control'] = 'no-cache'
            
            self._send_response(200, content_type, content, headers)
            
        except Exception as e:
            print(f"File error: {e}")
    
    def _handle_get_settings(self):
        if app.settings:
            settings = app.settings.get_all()
            self._send_response(200, 'application/json', json.dumps(settings))
        else:
            self._send_response(200, 'application/json', '{}')
    
    def _handle_get_stats(self):
        fps = app.current_fps if app.use_browser_capture else (app.camera.current_fps if app.camera else 0)
        stats = {
            'fps': fps,
            'recording': app.recording,
            'use_browser_capture': app.use_browser_capture,
            'ws_clients': len(app.ws_clients)
        }
        self._send_response(200, 'application/json', json.dumps(stats))
    
    def _handle_post_settings(self, data):
        if app.settings and data:
            # Remove fps from settings if present (we don't control it)
            data.pop('fps', None)
            app.settings.update(data)
            if app.camera:
                app.camera.update_settings(data)
        self._send_response(200, 'application/json', json.dumps({'status': 'ok'}))
    
    def _handle_command(self, data):
        command = data.get('command', '')
        
        if command == 'flash_on':
            if app.camera:
                app.camera.toggle_flash(True)
        elif command == 'flash_off':
            if app.camera:
                app.camera.toggle_flash(False)
        elif command == 'switch_capture':
            mode = data.get('mode', 'termux')
            app.use_browser_capture = (mode == 'browser')
            if not app.use_browser_capture:
                with app.frame_lock:
                    app.browser_frame = None
            print(f"Capture mode switched to: {mode}")
            self._send_response(200, 'application/json', 
                              json.dumps({'status': 'ok', 'mode': mode}))
            return
        else:
            self._send_response(400, 'application/json', 
                              json.dumps({'error': f'Unknown command: {command}'}))
            return
        
        self._send_response(200, 'application/json', json.dumps({'status': 'ok'}))
    
    def _handle_stream(self):
        try:
            self.send_response(200)
            self.send_header('Content-Type', 
                           'multipart/x-mixed-replace; boundary=frame')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Connection', 'close')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Pragma', 'no-cache')
            self.end_headers()
            
            last_frame = None
            
            while True:
                frame = None
                
                if app.use_browser_capture:
                    with app.frame_lock:
                        frame = app.browser_frame
                elif app.camera:
                    frame = app.camera.get_frame()
                
                # Only send if frame is new
                if frame and frame != last_frame:
                    try:
                        self.wfile.write(b'--frame\r\n')
                        self.wfile.write(b'Content-Type: image/jpeg\r\n')
                        self.wfile.write(f'Content-Length: {len(frame)}\r\n'.encode())
                        self.wfile.write(b'\r\n')
                        self.wfile.write(frame)
                        self.wfile.write(b'\r\n')
                        self.wfile.flush()
                        last_frame = frame
                    except:
                        break
                
                # Faster sleep for browser mode
                if app.use_browser_capture:
                    time.sleep(0.001)  # Minimal delay
                else:
                    time.sleep(0.05)
                
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            print(f"Stream error: {e}")
    
    def _handle_snapshot(self):
        frame = None
        
        if app.use_browser_capture:
            with app.frame_lock:
                frame = app.browser_frame
        elif app.camera:
            frame = app.camera.get_frame()
        
        if frame:
            self._send_response(200, 'image/jpeg', frame, {
                'Content-Disposition': 'attachment; filename="snapshot.jpg"'
            })
        else:
            self._send_response(404, body='No frame')
    
    def _handle_recording_start(self):
        app.recording = True
        app.recording_frames = []
        self._send_response(200, 'application/json', 
                          json.dumps({'status': 'recording_started'}))
    
    def _handle_recording_stop(self):
        app.recording = False
        
        os.makedirs('recordings', exist_ok=True)
        filename = f'recording_{int(time.time())}.mjpeg'
        filepath = os.path.join('recordings', filename)
        
        with open(filepath, 'wb') as f:
            for frame in app.recording_frames:
                f.write(b'--frame\r\n')
                f.write(b'Content-Type: image/jpeg\r\n')
                f.write(f'Content-Length: {len(frame)}\r\n'.encode())
                f.write(b'\r\n')
                f.write(frame)
                f.write(b'\r\n')
        
        self._send_response(200, 'application/json', json.dumps({
            'status': 'recording_stopped',
            'filename': filename,
            'frames': len(app.recording_frames)
        }))
    
    def _handle_download_zip(self):
        try:
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                if os.path.exists('recordings'):
                    for f in os.listdir('recordings'):
                        filepath = os.path.join('recordings', f)
                        if os.path.isfile(filepath):
                            zf.write(filepath, f)
            
            zip_buffer.seek(0)
            self._send_response(200, 'application/zip', zip_buffer.getvalue(), {
                'Content-Disposition': 'attachment; filename="recordings.zip"'
            })
        except Exception as e:
            print(f"ZIP error: {e}")
            self._send_response(500, body='Error')

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Termux Camera Stream Server')
    parser.add_argument('-p', '--port', type=int, default=8080, help='Port (default: 8080)')
    args = parser.parse_args()
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    app.static_dir = os.path.join(base_dir, 'static')
    
    os.makedirs(app.static_dir, exist_ok=True)
    os.makedirs('recordings', exist_ok=True)
    
    app.settings = Settings()
    app.camera = CameraCapture(app.settings)
    
    app.camera.start()
    
    # Use serve_forever in a way that allows Ctrl+C
    server = ThreadingHTTPServer(('', args.port), CameraHandler)
    
    print("=" * 50)
    print("  Termux Camera Streaming Server")
    print("=" * 50)
    print(f"\n📡 Server running on port {args.port}")
    print(f"📱 Phone capture: http://localhost:{args.port}/capture")
    print(f"🖥️  PC viewer: http://localhost:{args.port}")
    print(f"\nPress Ctrl+C to stop\n")
    
    # Run server in a way that allows clean exit
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    
    try:
        # Keep main thread alive but responsive to Ctrl+C
        while server_thread.is_alive():
            server_thread.join(1)
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        app.camera.stop()
        server.shutdown()
        server.server_close()
        print("Server stopped. Goodbye!")
        sys.exit(0)

if __name__ == '__main__':
    main()