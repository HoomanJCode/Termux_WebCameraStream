# 📸 Termux_WebCameraStream

**Stream your Android phone's camera to any device over WiFi with real-time controls.**

Turn your old Android phone into a wireless IP camera! This project creates a web-based camera streaming server that runs entirely in [Termux](https://termux.dev/), allowing you to view and control your phone's camera from any browser on your local network.

---

## ✨ Features

- **🌐 Web-Based Interface** - View and control from any device (PC, tablet, another phone)
- **📱 Browser Capture Mode** - High FPS streaming (20-30 FPS) using the phone's native camera API
- **📷 Termux Capture Mode** - Fallback mode using `termux-camera-photo` (lower FPS but always works)
- **⚡ Real-Time Settings** - Change quality, resolution, zoom, rotation, and mirror on the fly
- **🌓 Dark/Light Theme** - Easy on the eyes, day or night
- **🎥 Recording** - Save streams as MJPEG files
- **📸 Snapshots & Burst** - Capture still images with one click
- **⌨️ Keyboard Shortcuts** - Space for snapshot, F for fullscreen
- **📦 Download ZIP** - Download all recordings at once
- **📱 Mobile Responsive** - Works great on phones and desktops

---

## 🚀 Quick Start

### Prerequisites

1. **Install Termux** from [F-Droid](https://f-droid.org/en/packages/com.termux/) (NOT Google Play - that version is outdated)
2. **Install Termux:API** from [F-Droid](https://f-droid.org/en/packages/com.termux.api/)

### Installation

```bash
# Update packages
pkg update && pkg upgrade -y

# Install required packages
pkg install python termux-api -y

# Install Python dependencies
pip install Pillow

# Clone the repository
git clone https://github.com/HoomanJCode/Termux_WebCameraStream.git
cd Termux_WebCameraStream

# Run the server
python server.py
```

### Usage

1. **Start the server** on your phone:
   ```bash
   python server.py
   ```

2. **Option A: High FPS Browser Mode** (Recommended)
   - On your **phone's browser**, open: `http://localhost:8080/capture`
   - Grant camera permission when prompted
   - On your **PC browser**, open: `http://[PHONE_IP]:8080`
   - Switch capture mode to "Browser Camera" in the sidebar
   - Enjoy 20-30 FPS streaming!

3. **Option B: Termux Mode** (Fallback)
   - Just open `http://[PHONE_IP]:8080` on any device
   - Uses `termux-camera-photo` (~1 FPS but no browser needed on phone)

### Finding Your Phone's IP

```bash
# In Termux:
ifconfig wlan0 | grep 'inet ' | awk '{print $2}'
```

---

## 🎮 Controls

### Web Interface

| Control | Description |
|---------|-------------|
| **Capture Mode** | Switch between Browser (fast) and Termux (compatible) |
| **Resolution** | 320x240 to 1280x720 (higher = more detail, slower) |
| **Quality** | JPEG compression 10-100% (lower = faster, higher = better) |
| **Zoom** | Digital zoom 1.0x - 5.0x |
| **Rotation** | 0°, 90°, 180°, 270° |
| **Mirror H/V** | Flip image horizontally/vertically |
| **Flash** | Toggle flashlight (Termux mode only) |

### Action Buttons

| Button | Action |
|--------|--------|
| 📷 Snapshot | Save current frame as JPEG |
| 📸 Burst (5) | Take 5 rapid snapshots |
| ⏺ Record | Start recording MJPEG video |
| ⏹ Stop | Stop recording and save |
| 💡 Flash | Toggle LED flash |
| ⛶ Fullscreen | Enter fullscreen mode |
| 🌓 Theme | Switch dark/light theme |
| 📦 Download ZIP | Download all recordings |

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Space` | Take snapshot |
| `F` | Toggle fullscreen |

---

## 📁 Project Structure

```
Termux_WebCameraStream/
├── server.py              # Main HTTP server with WebSocket support
├── camera.py              # Termux camera capture module
├── settings.py            # JSON-based settings management
├── static/
│   ├── index.html         # Main web interface (PC viewer)
│   ├── capture.html       # Phone camera capture page
│   ├── style.css          # Dark/light theme styles
│   └── script.js          # Client-side logic & API calls
├── camera_settings.json   # Persistent settings file
└── recordings/            # Saved MJPEG recordings
```

---

## 🔧 Configuration

### Command Line Options

```bash
python server.py -p 8080        # Custom port (default: 8080)
python server.py -s myconf.json  # Custom settings file
```

### Default Settings

Settings are stored in `camera_settings.json` and can be edited manually:

```json
{
    "camera_id": 0,
    "width": 640,
    "height": 480,
    "quality": 80,
    "rotation": 0,
    "zoom": 1.0,
    "mirror_h": false,
    "mirror_v": false,
    "show_timestamp": false,
    "show_grid": false,
    "motion_detection": false,
    "motion_threshold": 30
}
```

---

## 🐛 Known Issues

### ⚠️ Black Screen Flicker in Browser Mode

**Status:** Open - Help Wanted!

When changing the quality setting in Browser mode, the video stream sometimes shows a black screen or flickers. This issue is being actively investigated.

**What we know:**
- Only occurs in Browser capture mode
- Triggered by quality setting changes
- May be related to canvas rendering or JPEG encoding timing
- The stream recovers after a few seconds

**If you can help fix this:**
- Check `static/capture.html` - the `captureFrame()` function
- The issue may be in how `toBlob()` or `toDataURL()` handles quality changes
- Could be a race condition between canvas updates and WebSocket sending
- PRs are welcome! Please test on multiple Android versions

**Workaround:** Avoid changing quality while streaming, or refresh the `/capture` page after changing settings.

---

## 🤝 Contributing

This project was created through **vibe coding** with [DeepSeek](https://deepseek.ai/) - an AI-assisted development process. We welcome contributions from humans and AIs alike!

### How to Contribute

1. **Report bugs** - Open an issue with:
   - Android version
   - Termux version
   - Steps to reproduce
   - Console logs (F12 in browser)

2. **Fix the black screen bug** - See [Known Issues](#-known-issues) above

3. **Add features** - Ideas welcome:
   - Audio streaming
   - PTZ controls
   - Motion detection alerts
   - Multiple camera support
   - RTSP/RTMP output
   - Docker support
   - Home Assistant integration

4. **Improve documentation** - Better install guides, troubleshooting, etc.

### Development Setup

```bash
# Fork and clone
git clone https://github.com/HoomanJCode/Termux_WebCameraStream.git
cd Termux_WebCameraStream

# Create a test environment
python -m venv venv
source venv/bin/activate  # On Termux, just use system python
pip install Pillow

# Run in debug mode
python server.py
```

---

## 📜 Disclaimer

### Privacy & Security

⚠️ **This server has NO authentication.** Anyone on your local network can:
- View your camera stream
- Change camera settings
- Take snapshots and recordings

**Do NOT expose this server to the internet.** Only use it on trusted local networks. The server binds to `0.0.0.0` by default, meaning it's accessible to all devices on your WiFi.

### Legal

- **Respect privacy laws** in your jurisdiction
- **Do not use for surveillance** without consent
- **You are responsible** for how you use this software
- This project is provided **AS IS** without warranty

### Compatibility

- Tested on Android 10-14 with Termux from F-Droid
- Browser capture requires a modern browser (Chrome/Firefox)
- Termux capture mode requires `termux-camera-photo` from Termux:API
- Not all Android devices support all camera features

---

## 🎯 Use Cases

- **Baby monitor** - Keep an eye on your little one
- **Pet cam** - Watch your pets while away
- **Security camera** - Monitor your room/garage
- **3D printer monitor** - Check your prints remotely
- **Timelapse photography** - Record long processes
- **Webcam for PC** - Use your phone as a high-quality webcam
- **IoT integration** - Stream to Home Assistant, Node-RED, etc.

---

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **DeepSeek AI** - Primary development assistant (vibe coding 🤖)
- **Termux Team** - Amazing terminal emulator for Android
- **Pillow** - Python imaging library
- **All contributors** - Those who help fix bugs and add features

---

## 🌟 Star History

If this project helps you, please ⭐ star it on GitHub! It helps others find it and motivates further development.

---

**Made with ❤️ and ☕ in Termux, powered by DeepSeek AI**

*"Vibe coding is real, and it's spectacular"* - Someone, probably
