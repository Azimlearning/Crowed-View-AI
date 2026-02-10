"""
System test tool for Venue Intelligence AI.
Tests dependencies, camera access, model loading, and configuration.
"""
import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test if all required packages are installed."""
    print("=" * 60)
    print("Testing Python Package Dependencies")
    print("=" * 60)
    
    required_packages = {
        'cv2': 'opencv-python',
        'ultralytics': 'ultralytics',
        'fastapi': 'fastapi',
        'pydantic': 'pydantic',
        'google.generativeai': 'google-generativeai',
        'dotenv': 'python-dotenv',
        'uvicorn': 'uvicorn',
    }
    
    missing = []
    for module_name, package_name in required_packages.items():
        try:
            __import__(module_name)
            print(f"[OK] {package_name:30s} - OK")
        except ImportError:
            print(f"[X] {package_name:30s} - MISSING")
            missing.append(package_name)
    
    if missing:
        print(f"\nMissing packages: {', '.join(missing)}")
        print("Install with: pip install " + " ".join(missing))
        return False
    else:
        print("\nAll required packages are installed!")
        return True


def test_camera():
    """Test camera access."""
    print("\n" + "=" * 60)
    print("Testing Camera Access")
    print("=" * 60)
    
    try:
        import cv2
        
        # Try to open camera
        camera_indices = [0, 1, 2]
        opened = False
        
        for idx in camera_indices:
            cap = cv2.VideoCapture(idx)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    height, width = frame.shape[:2]
                    print(f"[OK] Camera {idx} opened successfully")
                    print(f"  Resolution: {width}x{height}")
                    cap.release()
                    opened = True
                    break
                cap.release()
        
        if not opened:
            print("[X] No camera found or accessible")
            print("  Try closing other apps using the camera")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Camera test failed: {e}")
        return False


def test_yolo_model():
    """Test YOLOv8 model loading."""
    print("\n" + "=" * 60)
    print("Testing YOLOv8 Model")
    print("=" * 60)
    
    try:
        # PyTorch 2.6+ compatibility fix
        import torch
        _torch_load = torch.load
        def _torch_load_weights_only_false(*args, **kwargs):
            if "weights_only" not in kwargs:
                kwargs["weights_only"] = False
            return _torch_load(*args, **kwargs)
        torch.load = _torch_load_weights_only_false
        
        from ultralytics import YOLO
        
        print("Loading YOLOv8-Nano model...")
        model = YOLO('yolov8n.pt')
        print("[OK] YOLOv8-Nano model loaded successfully")
        
        # Test inference on dummy image
        import numpy as np
        dummy_image = np.zeros((480, 640, 3), dtype=np.uint8)
        results = model(dummy_image, verbose=False)
        print("[OK] Model inference test passed")
        
        return True
        
    except Exception as e:
        print(f"✗ YOLO model test failed: {e}")
        return False


def test_configuration():
    """Test configuration files."""
    print("\n" + "=" * 60)
    print("Testing Configuration Files")
    print("=" * 60)
    
    try:
        import json
        from pathlib import Path
        
        BASE_DIR = Path(__file__).parent.parent
        CONFIG_PATH = BASE_DIR / "data" / "config.json"
        SEATING_MAP_PATH = BASE_DIR / "data" / "seating_map.json"
        
        # Test config.json
        if not CONFIG_PATH.exists():
            print(f"✗ Config file not found: {CONFIG_PATH}")
            return False
        
        with open(CONFIG_PATH, 'r') as f:
            config_data = json.load(f)
        
        required_config_keys = ['event_type', 'zones', 'detection_interval_seconds', 
                                'stability_required_scans', 'seat_detection_radius_pixels']
        missing_keys = [k for k in required_config_keys if k not in config_data]
        
        if missing_keys:
            print(f"[X] Missing config keys: {', '.join(missing_keys)}")
            return False
        
        print(f"[OK] config.json loaded successfully")
        print(f"  Event type: {config_data.get('event_type')}")
        print(f"  Zones: {len(config_data.get('zones', []))}")
        
        # Test seating_map.json
        if not SEATING_MAP_PATH.exists():
            print(f"[X] Seating map file not found: {SEATING_MAP_PATH}")
            return False
        
        with open(SEATING_MAP_PATH, 'r') as f:
            seating_data = json.load(f)
        
        if 'zones' not in seating_data:
            print("[X] seating_map.json missing 'zones' key")
            return False
        
        total_seats = sum(len(zone.get('seats', [])) for zone in seating_data['zones'])
        print(f"[OK] seating_map.json loaded successfully")
        print(f"  Zones: {len(seating_data['zones'])}")
        print(f"  Total seats: {total_seats}")
        
        return True
        
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_vision_engine():
    """Test vision engine initialization."""
    print("\n" + "=" * 60)
    print("Testing Vision Engine")
    print("=" * 60)
    
    try:
        from pathlib import Path
        from vision_engine import VisionEngine
        
        BASE_DIR = Path(__file__).parent.parent
        SEATING_MAP_PATH = BASE_DIR / "data" / "seating_map.json"
        CONFIG_PATH = BASE_DIR / "data" / "config.json"
        
        print("Initializing VisionEngine...")
        engine = VisionEngine(str(SEATING_MAP_PATH), str(CONFIG_PATH))
        
        print(f"[OK] VisionEngine initialized")
        print(f"  Seats loaded: {len(engine.seats)}")
        print(f"  Zones loaded: {len(engine.zones)}")
        
        # Cleanup
        engine.cleanup()
        
        return True
        
    except Exception as e:
        print(f"✗ Vision engine test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_connectivity():
    """Test API connectivity (if backend is running)."""
    print("\n" + "=" * 60)
    print("Testing API Connectivity")
    print("=" * 60)
    
    try:
        import requests
        
        base_url = "http://localhost:8000"
        
        # Test root endpoint
        try:
            response = requests.get(f"{base_url}/", timeout=2)
            if response.status_code == 200:
                print(f"[OK] Backend API is running at {base_url}")
                return True
        except requests.exceptions.ConnectionError:
            print("[!] Backend API is not running")
            print("  Start it with: python backend/app.py")
            return None  # Not a failure, just not running
        except Exception as e:
            print(f"[X] API test failed: {e}")
            return False
            
    except ImportError:
        print("[!] requests package not installed (optional for API test)")
        return None


def test_environment():
    """Test environment variables."""
    print("\n" + "=" * 60)
    print("Testing Environment Variables")
    print("=" * 60)
    
    from dotenv import load_dotenv
    load_dotenv()
    
    gemini_key = os.getenv('GEMINI_API_KEY')
    camera_index = os.getenv('CAMERA_INDEX')
    
    if gemini_key:
        if gemini_key == 'your_gemini_api_key_here':
            print("[!] GEMINI_API_KEY is set to placeholder value")
        else:
            print("[OK] GEMINI_API_KEY is configured")
    else:
        print("[!] GEMINI_API_KEY not set (required for AI suggestions)")
    
    if camera_index:
        print(f"[OK] CAMERA_INDEX is set to {camera_index}")
    else:
        print("[INFO] CAMERA_INDEX not set (will try indices 0, 1, 2)")
    
    return True


def main():
    """Run all system tests."""
    print("\n" + "=" * 60)
    print("Venue Intelligence AI - System Test")
    print("=" * 60)
    
    results = {
        'imports': test_imports(),
        'camera': test_camera(),
        'yolo': test_yolo_model(),
        'config': test_configuration(),
        'vision_engine': test_vision_engine(),
        'api': test_api_connectivity(),
        'environment': test_environment(),
    }
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    critical_tests = ['imports', 'camera', 'yolo', 'config', 'vision_engine']
    all_passed = True
    
    for test_name, result in results.items():
        if result is True:
            status = "[PASS]"
        elif result is False:
            status = "[FAIL]"
            if test_name in critical_tests:
                all_passed = False
        else:
            status = "[SKIP]"
        
        print(f"{status:8s} - {test_name}")
    
    print("\n" + "=" * 60)
    if all_passed:
        print("[OK] All critical tests passed! System is ready to use.")
        return 0
    else:
        print("[X] Some critical tests failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
