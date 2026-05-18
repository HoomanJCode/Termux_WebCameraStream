#!/usr/bin/env python3
"""
Settings Management Module
"""

import json
import os
import threading

class Settings:
    DEFAULT_SETTINGS = {
        'camera_id': 0,
        'width': 640,
        'height': 480,
        'fps': 15,
        'quality': 80,
        'mirror_h': False,
        'mirror_v': False,
        'rotation': 0,
        'zoom': 1.0,
        'flash': False,
        'show_timestamp': False,
        'show_grid': False,
        'motion_detection': False,
        'motion_threshold': 30,
        'theme': 'dark'
    }
    
    def __init__(self, settings_file='camera_settings.json'):
        self.settings_file = settings_file
        self.settings = self.DEFAULT_SETTINGS.copy()
        self.lock = threading.Lock()
        self.load()
    
    def load(self):
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    loaded = json.load(f)
                    with self.lock:
                        for key in self.DEFAULT_SETTINGS:
                            if key in loaded:
                                self.settings[key] = loaded[key]
        except Exception as e:
            print(f"Error loading settings: {e}")
    
    def save(self):
        try:
            with self.lock:
                with open(self.settings_file, 'w') as f:
                    json.dump(self.settings, f, indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    def get(self, key, default=None):
        with self.lock:
            return self.settings.get(key, default)
    
    def set(self, key, value):
        with self.lock:
            if key in self.DEFAULT_SETTINGS:
                self.settings[key] = value
    
    def update(self, new_settings):
        with self.lock:
            for key, value in new_settings.items():
                if key in self.DEFAULT_SETTINGS:
                    self.settings[key] = value
        self.save()
    
    def get_all(self):
        with self.lock:
            return self.settings.copy()
    
    def reset(self):
        with self.lock:
            self.settings = self.DEFAULT_SETTINGS.copy()
        self.save()