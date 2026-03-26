"""
RTSP Camera Connection Tester for Imou Ranger 2.
Run from project root: python backend/rtsp_test.py [--url RTSP_URL]
"""
import os, sys, time, socket, argparse
from dotenv import load_dotenv
from urllib.parse import urlparse
load_dotenv()

def check_port_open(host, port, timeout=2):
    """Check if the RTSP port is reachable over TCP."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        s.close()
        return True
    except:
        return False

def test_rtsp():
    parser = argparse.ArgumentParser(description="Test RTSP connection")
    parser.add_argument("--url", type=str, help="RTSP URL to test (overrides .env)")
    args = parser.parse_args()

    rtsp_url = args.url or os.getenv("RTSP_URL")
    if not rtsp_url:
        print("[!] RTSP_URL not set in .env and no --url provided.")
        print("    Format: rtsp://admin:<SAFETY_CODE>@<CAMERA_IP>:554/cam/realmonitor?channel=1&subtype=1")
        sys.exit(1)
    
    # Redact password for display
    try:
        parsed = urlparse(rtsp_url)
        safe_url = rtsp_url.replace(f":{parsed.password}@", ":***@") if parsed.password else rtsp_url
        host = parsed.hostname
        port = parsed.port or 554
    except Exception:
        safe_url = rtsp_url[:40] + "..."
        host = None
        port = 554
        
    print(f"Testing RTSP: {safe_url}")
    
    if host:
        print(f"[*] Checking TCP port {port} on {host}...")
        if check_port_open(host, port):
            print(f"[OK] Port {port} is reachable.")
        else:
            print(f"[FAIL] Port {port} is closed or host is unreachable.")
            print("       - Is the camera powered on?")
            print("       - Is the laptop on the EXACT SAME Wi-Fi network?")
            return False

    import cv2
    print("[*] Attempting OpenCV FFMPEG connection (TCP)...")
    
    # Try TCP transport first (usually required for Imou/Dahua on WiFi)
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
    cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
    
    if cap.isOpened():
        ret, frame = cap.read()
        if ret and frame is not None:
            h, w = frame.shape[:2]
            print(f"[OK] Stream opened via TCP! Resolution: {w}x{h}")
            cap.release()
            return True
        cap.release()
        
    print("[*] TCP failed. Attempting UDP fallback...")
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;udp"
    cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
    
    if cap.isOpened():
        ret, frame = cap.read()
        if ret and frame is not None:
            h, w = frame.shape[:2]
            print(f"[OK] Stream opened via UDP! Resolution: {w}x{h}")
            cap.release()
            return True
        cap.release()

    print("\n[FAIL] Could not read video stream. Troubleshoot:")
    print("  1. Wrong safety code? It is the sticker under the camera (case-sensitive).")
    print("  2. Test in VLC Media Player: Media > Open Network Stream > paste URL.")
    print("  3. Try subtype=0 (Main Stream) instead of subtype=1 (Sub Stream).")
    return False

if __name__ == "__main__":
    test_rtsp()
