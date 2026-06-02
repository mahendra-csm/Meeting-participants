# Zoom Meeting Bot Automation

This project uses Playwright and Python to automate joining a Zoom meeting through the Zoom Web Client using multiple browser instances.

## Features

* Automated Zoom Web Client joining
* Multiple participant simulation
* Sequential joining workflow
* Automatic microphone and camera permissions
* Meeting UI verification
* Screenshot capture on failures
* Configurable participant names
* Configurable stay duration

---

# Prerequisites

## 1. Python

Install Python 3.10 or later.

Verify installation:

```bash
python --version
```

or

```bash
python3 --version
```

---

## 2. Google Chrome / Chromium

Playwright launches a Chromium browser instance.

Install Google Chrome or Chromium on your system.

---

## 3. Virtual Environment (Recommended)

Create a virtual environment:

```bash
python -m venv venv
```

Activate it:

### Windows

```bash
venv\Scripts\activate
```

### Linux / macOS

```bash
source venv/bin/activate
```

---

# Installation

## Install Python Dependencies

```bash
pip install playwright
```

Install Playwright browsers:

```bash
playwright install chromium
```

or

```bash
python -m playwright install chromium
```

---

# Project Structure

```text
project/
│
├── zoom_bot.py
├── README.md
├── debug_*.png
└── venv/
```

---

# Configuration

Edit the following variables inside `zoom_bot.py`.

## Meeting URL

```python
MEETING_URL = "https://us05web.zoom.us/j/XXXXXXXXXXX"
```

## Bot Names

```python
BOT_NAMES = [
    "Alice Johnson",
    "Bob Smith",
    "Carol White"
]
```

## Stay Duration

Time each bot remains in the meeting:

```python
STAY_DURATION = 3600
```

(Default: 1 hour)

## Launch Delay

Delay before triggering the next participant:

```python
LAUNCH_DELAY = 0
```

---

# Running the Script

Start the automation:

```bash
python zoom_bot.py
```

---

# Expected Workflow

For each participant:

1. Open Zoom Web Client
2. Handle "Join from Browser" page
3. Enter meeting passcode (if required)
4. Fill participant name
5. Click Join
6. Join computer audio
7. Verify meeting interface loaded
8. Signal next participant to join
9. Remain connected for configured duration

---

# Debugging

If a participant fails to join:

* A screenshot is automatically saved:

```text
debug_Alice_Johnson.png
```

or

```text
debug_Alice_Johnson_join_fail.png
```

Review the screenshot to identify the issue.

---

# Common Issues

## Browser Not Installed

Error:

```text
Executable doesn't exist
```

Fix:

```bash
playwright install chromium
```

---

## Meeting Not Started

Possible Zoom message:

```text
Waiting for the host
```

The script will detect this and stop the join attempt.

---

## Invalid Meeting ID

Possible Zoom message:

```text
Meeting does not exist
```

Verify the meeting URL.

---

## Permission Issues on Linux

Install required system dependencies:

```bash
playwright install-deps
```

---

# Notes

* Zoom frequently changes its web interface and selectors.
* The automation may require updates if Zoom modifies its UI.
* Browser automation can be detected by Zoom despite the included stealth settings.
* Meeting hosts may still remove automated participants.

---

# Dependencies

```text
Python >= 3.10
playwright >= 1.40
Chromium Browser
```

---

# Install Everything Quickly

```bash
pip install playwright
playwright install chromium
python zoom_bot.py
```
