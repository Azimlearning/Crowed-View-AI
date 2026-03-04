---
name: enforcing-project-constraints
description: Enforces the strict hard constraints and technical logic of the CrowdView AI prototype. Use when proposing architectures, planning tasks, or making technical decisions to avoid over-engineering.
---

# Enforcing Project Constraints

## When to use this skill
- When starting a new task, brainstorming features, or writing an implementation plan for the CrowdView AI project.
- When proposing technical solutions, new hardware, or architectural changes.
- When the user asks you to "Reference GEMINI.md for context" or keep the project simple.

## Workflow
- [ ] **1. Review Hard Constraints**: Verify the proposed solution does not require cloud infrastructure, respects the hardware limits (single USB webcam), and strictly complies with privacy constraints (no facial recognition, no storage).
- [ ] **2. Check Technical Logic**: Ensure the design adheres to the 60% seat overlap rule, 30-second occupancy confirmation, and 20-minute vacancy grace period.
- [ ] **3. Validate the Stack**: Ensure it relies strictly on the predefined stack (FastAPI, React/Vite, YOLOv8-Nano, Gemini 1.5 Flash).
- [ ] **4. Filter Over-engineering**: Actively strip out any "production-ready" suggestions (like external databases, complex auth, horizontal scaling) that push beyond a TRL 3 prototype or exceed the ~RM250 budget.
- [ ] **5. Proceed**: Once validated, proceed with implementation planning or coding.

## Instructions

Whenever you make a decision, plan a feature, or write code in this repository, you must act as a frugal technical co-founder building a **TRL 3 Proof of Concept**.

### Rule 1: Abide by the Hard Constraints (No-Go Zones)
You must **never** suggest or implement features that violate these boundaries:
- **Budget & Hardware**: Everything is processed locally on a laptop using a single plug-and-play USB webcam. Do not suggest AWS, Vercel, dedicated cloud servers, multi-camera stitching, or physical sensors (IR/pressure).
- **Privacy**: No video storage and absolutely no facial recognition (PDPA 2010 compliance). Frames must be processed in RAM and discarded immediately.
- **Deployment**: Localhost only. No cloud deployment required for the prototype.

### Rule 2: Enforce the Business & Technical Logic
Any occupancy or seating logic you touch must respect these predefined tracking rules:
- **Overlap Threshold**: A seat is considered occupied *only* if a person's bounding box overlaps >60% of the defined seat radius/area.
- **Sustained Occupancy (Stability)**: Must be sustained for 30 seconds before updating the seat status to "Red" (Occupied).
- **Vacancy Grace Period**: Once a person leaves, wait 20 minutes before flagging as "Orange" (Actionable) to account for bathroom or stretch breaks.
- **Detection Interval**: Scans run every 7 seconds by default.

### Rule 3: Maintain the Tech Stack
Stick exclusively to the existing tools:
- **Backend:** Python / FastAPI
- **Frontend:** React / Vite
- **Computer Vision:** YOLOv8-Nano
- **Generative AI:** Gemini 1.5 Flash API
*Do not introduce external relational databases (like PostgreSQL), message queues (like Redis/RabbitMQ), or heavy ORMs unless explicitly requested.*

### Rule 4: Focus on the "Definition of Done"
Ensure all work drives toward these prototype goals:
- A live camera feed with a 2D seat overlay.
- A functional dashboard showing Green (Empty), Red (Occupied), and Orange (Actionable) statuses.
- A modal pop-up that calls the Gemini API for operational suggestions when an Orange seat is clicked.
- A functional calibration tool to map seats (rectangles) to the camera view.

## Resources
- Reference the global system `<MEMORY[GEMINI.md]>` for JSON data schema rules or any explicit maintenance log updates.
