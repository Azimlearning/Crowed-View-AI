"""
RTSP Camera Connection Tester for Imou Ranger 2.
Run from project root: python backend/rtsp_test.py
"""
import os, sys, time
from dotenv import load_dotenv
load_dotenv()

def test_rtsp():
    import cv2
    rtsp_url = os.getenv("RTSP_URL")
    if not rtsp_url:
        print("[!] RTSP_URL not set in .env — set it first")
        sys.exit(1)
    
    print(f"Testing RTSP: {rtsp_url[:40]}...")
    
    # Try CAP_FFMPEG first
    cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
    if cap.isOpened():
        ret, frame = cap.read()
        if ret and frame is not None:
            h, w = frame.shape[:2]
            print(f"[OK] Stream opened! Resolution: {w}x{h}")
            cap.release()
            return True
        cap.release()

    # Fallback
    cap = cv2.VideoCapture(rtsp_url)
    if cap.isOpened():
        ret, frame = cap.read()
        if ret and frame is not None:
            h, w = frame.shape[:2]
            print(f"[OK] Stream opened (fallback)! Resolution: {w}x{h}")
            cap.release()
            return True
        cap.release()

    print("[FAIL] Could not connect. Troubleshoot:")
    print("  1. Is your laptop on the SAME WiFi as the camera?")
    print("  2. Test in VLC first: Media > Open Network Stream > paste URL")
    print("  3. Wrong safety code? Check sticker under camera")
    print("  4. Try subtype=0 instead of subtype=1 in the URL")
    return False

if __name__ == "__main__":
    test_rtsp()
