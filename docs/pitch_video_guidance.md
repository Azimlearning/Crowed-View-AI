# Venue Intelligence AI: Comprehensive 4-Minute Pitch & Demo Production Guide

**Prepared by:** Technical Product Manager & Video Director  
**Project Status:** Operational Prototype (TRL 3)  
**Target Output:** 4-minute maximum, 1080p 60fps video split-screen presentation  

This document serves as the absolute source of truth for planning, recording, and editing the CrowdView AI final presentation. 

---

## 🏗️ 1. Core Technical Foundations (Truth Assets)
Your presentation must be rooted entirely in functional reality. Do not promise or mention theoretical hardware or unwritten components. Ensure your script highlights the following operational stack:

*   **Computer Vision Engine:** **YOLOv8-Nano**. Chosen specifically for its efficiency, allowing it to run entirely on local CPU resources rather than requiring expensive cloud GPUs. It identifies \"Class 0\" (Persons) in real-time.
*   **The Backend Brain:** A **FastAPI** server that ingests vision data every 7 seconds and processes the core \"Stability Logic\". It handles state transitions and communicates with the frontend via API polling.
*   **The Digital Twin Dashboard:** A highly responsive **React** frontend rendering a 2D spatial map of the venue. The UI shifts seat statuses through three primary states: 
    *   `Green` (Empty)
    *   `Red` (Occupied)
    *   `Orange` (Actionable)
*   **The Intelligence Layer:** **Google Gemini 1.5 Flash API**. This is what turns raw data into intelligence. By feeding Gemini the state of the room, it returns hyper-contextual operational suggestions for staff.

---

## ⏱️ 2. Detailed 4-Minute Beat Sheet
To ensure a perfect 4-minute runtime, adhere to this timing structure when recording your script.

| Time Range | Duration | Topic Area | Key Goal |
| :--- | :--- | :--- | :--- |
| **0:00 - 0:30** | 30s | **The Hook & Problem Space** | Address the \"invisible loss\" of premium empty seats. Establish the chaos, miscommunication, and slow radio protocols of manual human monitoring. |
| **0:30 - 1:15** | 45s | **The Solution & Live Vision Engine** | Introduce YOLOv8-Nano. Visually prove it's working by showing cyan bounding boxes on the live feed paired with the React dashboard turning a seat Red. |
| **1:15 - 2:15** | 60s | **The 60% Stability Logic** | This is the technical centerpiece. Prove that the system handles noise. The presenter leaves the seat, but the system waits 30 seconds before flipping it to Green to ensure no false positives. |
| **2:15 - 3:00** | 45s | **The \"Decision Moment\" (Actionable State)** | Fast-forward the vacancy grace period. Visually hit the \"Orange\" state. Request the Gemini AI suggestion. Frame it as giving a superpower to your staff. |
| **3:00 - 3:45** | 45s | **Bonds of Harmony: AI + Human** | Reassure stakeholders. The AI advises; the human executes. Show how this dynamic shifts manpower from "monitoring" to "taking action." |
| **3:45 - 4:00** | 15s | **Impact & Call to Action (Outro)** | Rapidly list the three value props: Revenue Recovery, Peak Operational Efficiency, and Brand Protection. End the video confident and strong. |

---

## 🛠️ 3. Pre-Production & Screen Recording Setup

To achieve the "split-screen" aesthetic required for the script, you must configure your local environment correctly.

### Checking the Configuration Files
Before hitting record, modify your `data/config.json` on the backend:
1.  **Set `debug_detection: true`:** This ensures that the cyan YOLO bounding boxes and circular detection radii are visible over your camera feed. This is visual proof to the judges that the computer vision is active and calculating.
2.  **Adjust the Grace Period (Simulation):** To avoid having to sit and record for 20 minutes waiting for a seat to turn Orange, temporarily adjust your `config.json` to make the vacancy threshold incredibly short (e.g., 1 minute), OR use `testing_mode: true` if available in your config to bypass long waits. 
3.  **Ensure Stability Counters are set:** Leave `stability_required_scans` at the default `3` to accurately demonstrate the 30-second temporal confirmation rule.

### Tooling Requirements
*   **Screen Recording Software:** OBS Studio (Open Broadcaster Software). Create a "Split-Screen" scene layout.
*   **Browser Window 1 (Left):** Point this window to `http://localhost:8000/api/debug-seat-map` to capture the live camera feed and the bounding boxes.
*   **Browser Window 2 (Right):** Point this to `http://localhost:5173` to capture the sleek, interactive React Digital Twin dashboard.

### Scene Directives
*   **Lighting:** Ensure your testing space (the mock venue) is well lit so the webcam can reliably feed YOLOv8 high-contrast imagery.
*   **Seat Placement:** Map the seats accurately using the calibration tool before recording so the green/red circles overlap your actual chairs perfectly.

---

## 👔 4. Presenter Tone, Attire, and Delivery

*   **Attire:** You are pitching to a high-level panel for a university/commercial presentation. Wear professional, sharp attire. The UTP standard demands a polished look. Even if filming at home, structure the background cleanly.
*   **Audio Rig:** The most common mistake in technical pitches is poor audio. Do not use a laptop microphone. Use a dedicated lapel or a high-quality boom microphone. The audio format should be normalized and free from room echo.
*   **Pacing & Cadence:** Speak deliberately. When a technical transition happens on screen (like the seat turning Green after 30 seconds), pause briefly to let the audience *see* it happen. Don't rush your lines over the visual evidence.
*   **The Narrative Hook:** Continually bring the conversation back to "Bonds of Harmony." The technology is impressive, but the psychological safety you offer venue staff—partnering AI with human intuition rather than replacing humans—is the ultimate selling point.
