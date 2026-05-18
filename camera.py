#!/usr/bin/env python3
"""
Camera Capture Module for Termux
"""

import os
import time
import subprocess
import threading
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

class CameraCapture:
    def __init__(self, settings):
        self.settings = settings
        self.capturing = False
        self.frame_buffer = None
        self.lock = threading.Lock()
        self.capture_thread = None
        self.temp_dir = None
        self.frame_count = 0
        self.current_fps = 0
        self.last_fps_update = time.time()
        self.fps_frame_count = 0
        self.last_frame = None
        self.motion_detected = False
        
        prefix = os.environ.get('PREFIX', '/data/data/com.termux/files/usr')
        self.temp_dir = os.path.join(prefix, 'tmp', 'camera_app')
        os.makedirs(self.temp_dir, exist_ok=True)
        
        self.camera_available = self._check_camera()
        
    def _check_camera(self):
        try:
            result = subprocess.run(
                ['termux-camera-photo', '-c', '0', '/dev/null'],
                capture_output=True, timeout=3
            )
            return True
        except:
            return False
    
    def start(self):
        self.capturing = True
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()
        print("Camera capture started")
        
    def stop(self):
        self.capturing = False
        if self.capture_thread:
            self.capture_thread.join(timeout=2)
        print("Camera capture stopped")
        
    def update_settings(self, new_settings):
        self.settings.update(new_settings)
        self.last_frame = None
    
    def capture_frame(self):
        temp_file = os.path.join(self.temp_dir, f'frame_{int(time.time()*1000)}.jpg')
        
        try:
            camera_id = self.settings.get('camera_id', 0)
            cmd = ['termux-camera-photo', '-c', str(camera_id), temp_file]
            
            result = subprocess.run(cmd, capture_output=True, timeout=5)
            
            if result.returncode != 0 or not os.path.exists(temp_file):
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                return None
            
            if os.path.getsize(temp_file) > 0:
                processed_bytes = self._process_image(temp_file)
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                return processed_bytes
            
            if os.path.exists(temp_file):
                os.remove(temp_file)
            return None
                
        except Exception as e:
            print(f"Capture error: {e}")
            if os.path.exists(temp_file):
                os.remove(temp_file)
            return None
    
    def _process_image(self, image_path):
        try:
            img = Image.open(image_path)
            settings = self.settings.get_all()
            
            # Mirror
            if settings.get('mirror_h', False):
                img = img.transpose(Image.FLIP_LEFT_RIGHT)
            if settings.get('mirror_v', False):
                img = img.transpose(Image.FLIP_TOP_BOTTOM)
            
            # Rotation
            rotation = settings.get('rotation', 0)
            if rotation != 0:
                img = img.rotate(-rotation, expand=True)
            
            # Zoom
            zoom = settings.get('zoom', 1.0)
            if zoom != 1.0:
                width, height = img.size
                new_width = int(width / zoom)
                new_height = int(height / zoom)
                left = (width - new_width) // 2
                top = (height - new_height) // 2
                img = img.crop((left, top, left + new_width, top + new_height))
            
            # Resize
            target_width = settings.get('width', 640)
            target_height = settings.get('height', 480)
            img = img.resize((target_width, target_height), Image.LANCZOS)
            
            # Motion detection
            if settings.get('motion_detection', False):
                self._detect_motion(img)
            
            # Timestamp
            if settings.get('show_timestamp', False):
                draw = ImageDraw.Draw(img)
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                try:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
                except:
                    font = ImageFont.load_default()
                
                bbox = draw.textbbox((0, 0), timestamp, font=font)
                draw.rectangle([8, 8, bbox[2] + 16, bbox[3] + 16], fill=(0, 0, 0, 180))
                draw.text((12, 12), timestamp, fill=(255, 255, 0), font=font)
            
            # Grid
            if settings.get('show_grid', False):
                draw = ImageDraw.Draw(img)
                width, height = img.size
                for i in range(1, 3):
                    x = width * i // 3
                    draw.line([(x, 0), (x, height)], fill=(255, 255, 255, 80), width=1)
                    y = height * i // 3
                    draw.line([(0, y), (width, y)], fill=(255, 255, 255, 80), width=1)
            
            # Convert to JPEG
            quality = settings.get('quality', 80)
            buffer = BytesIO()
            img.save(buffer, format='JPEG', quality=quality)
            img.close()
            
            return buffer.getvalue()
            
        except Exception as e:
            print(f"Image processing error: {e}")
            return None
    
    def _detect_motion(self, current_img):
        try:
            if self.last_frame is None:
                self.last_frame = current_img.copy().convert('L')
                return
            
            current_gray = current_img.convert('L')
            diff_pixels = 0
            total_pixels = 0
            
            for y in range(0, current_gray.height, 2):
                for x in range(0, current_gray.width, 2):
                    try:
                        diff = abs(current_gray.getpixel((x, y)) - self.last_frame.getpixel((x, y)))
                        diff_pixels += diff
                        total_pixels += 1
                    except:
                        pass
            
            if total_pixels > 0:
                avg_diff = diff_pixels / total_pixels
                threshold = self.settings.get('motion_threshold', 30)
                self.motion_detected = avg_diff > threshold
            
            self.last_frame = current_gray
            
        except Exception as e:
            print(f"Motion detection error: {e}")
    
    def _capture_loop(self):
        while self.capturing:
            start_time = time.time()
            
            frame_data = self.capture_frame()
            
            if frame_data:
                with self.lock:
                    self.frame_buffer = frame_data
                    self.frame_count += 1
                    self.fps_frame_count += 1
            
            current_time = time.time()
            if current_time - self.last_fps_update >= 1.0:
                self.current_fps = self.fps_frame_count
                self.fps_frame_count = 0
                self.last_fps_update = current_time
            
            target_fps = self.settings.get('fps', 15)
            if target_fps > 0:
                elapsed = time.time() - start_time
                sleep_time = (1.0 / target_fps) - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)
    
    def get_frame(self):
        with self.lock:
            return self.frame_buffer
    
    def get_stats(self):
        return {
            'fps': self.current_fps,
            'frame_count': self.frame_count,
            'motion_detected': self.motion_detected,
            'camera_available': self.camera_available
        }
    
    def toggle_flash(self, state):
        try:
            if state:
                subprocess.run(['termux-torch', 'on'], timeout=3)
            else:
                subprocess.run(['termux-torch', 'off'], timeout=3)
        except Exception as e:
            print(f"Flash error: {e}")