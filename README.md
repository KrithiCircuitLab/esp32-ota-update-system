
![Status](https://img.shields.io/badge/Status-Complete-brightgreen)
![ESP32](https://img.shields.io/badge/Hardware-ESP32-blue)
![Python](https://img.shields.io/badge/Python-3.11-yellow)
![ESP-IDF](https://img.shields.io/badge/ESP--IDF-v5.5.4-red)

# ESP32 OTA Update System

Production-grade Over-The-Air firmware update 
system for ESP32 — built with ESP-IDF and FreeRTOS.

## What this demonstrates
- Safe OTA firmware updates over WiFi
- Dual partition system (app0/app1)
- Automatic rollback on failed update
- Python HTTP server for firmware serving
- Real-time serial monitoring during update
- JSON update report generation

## Architecture
ESP32 v1.0.0 (running)
│ HTTP request
▼
Python OTA Server (laptop)
│ firmware.bin (v2.0.0)
▼
ESP32 downloads to app1 partition
│ validates binary
▼
ESP32 reboots into v2.0.0
│ marks as valid
▼
ESP32 v2.0.0 confirmed running ✅


## How to run
### Flash v1.0.0
```bash
idf.py build && idf.py -p COM3 flash
```

### Build v2.0.0
Change VERSION to "2.0.0" → build only:
```bash
idf.py build
copy build\ota_system.bin firmware.bin
```

### Start OTA server
```bash
pip install pyserial
python ota_server.py
```

### Trigger update
Press EN/RESET on ESP32 → watch auto-update

## Tech Stack
- ESP32 / ESP-IDF v5.5.4
- FreeRTOS (tasks, event groups)
- Python 3.11 (HTTP server, serial monitor)
- C firmware (OTA, WiFi, partition management)

## Author
Krithiga Ramesh — Embedded Firmware Engineer  
Singapore 🇸🇬 | github.com/KrithiCircuitLab
