"""
Project 2: ESP32 OTA Update Server
Author: Krithiga Ramesh (KrithiCircuitLab)

WHAT THIS DOES:
1. Serves firmware.bin to ESP32 over HTTP
2. Monitors ESP32 serial output during update
3. Detects success or failure automatically
4. Generates JSON report of the update

HOW TO USE:
1. Build v2.0.0 firmware (see instructions)
2. Copy build/ota_system.bin as firmware.bin here
3. Run: python ota_server.py
4. ESP32 auto-downloads and updates
"""

import http.server
import socketserver
import threading
import serial
import serial.tools.list_ports
import json
import time
import os
import socket
from datetime import datetime


# ═══════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════
SERVER_PORT  = 8070
SERIAL_PORT  = "COM3"
SERIAL_BAUD  = 115200
FIRMWARE_FILE = "firmware.bin"


def get_local_ip():
    """Get this laptop's WiFi IP address."""
    s = socket.socket(socket.AF_INET, 
                      socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


class SilentHTTPHandler(
        http.server.SimpleHTTPRequestHandler):
    """HTTP handler that serves files silently."""

    def log_message(self, format, *args):
        # Only log firmware requests
        if FIRMWARE_FILE in str(args):
            print(f"\n📦 ESP32 requesting firmware...")
            print(f"   Serving: {FIRMWARE_FILE}")

    def log_error(self, format, *args):
        pass


class OTAServer:
    """
    Complete OTA update server with monitoring.

    Architecture:
    ┌─────────────────────────────────────┐
    │  Thread 1: HTTP Server              │
    │  └── Serves firmware.bin to ESP32  │
    │                                     │
    │  Thread 2: Serial Monitor (main)   │
    │  └── Watches ESP32 output          │
    │  └── Detects OTA stages            │
    │  └── Generates report              │
    └─────────────────────────────────────┘
    """

    def __init__(self):
        self.local_ip   = get_local_ip()
        self.start_time = None
        self.ota_log    = []
        self.ota_done   = False

        self._print_banner()
        self._check_firmware()

    def _print_banner(self):
        print("\n" + "═" * 55)
        print("  ESP32 OTA Update Server")
        print("  Author: Krithiga Ramesh | KrithiCircuitLab")
        print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("═" * 55)
        print(f"\n💻 Your laptop IP: {self.local_ip}")
        print(f"🌐 Server URL:     http://{self.local_ip}:{SERVER_PORT}")
        print(f"📁 Firmware file:  {FIRMWARE_FILE}")
        print(f"📡 Serial port:    {SERIAL_PORT}")

    def _check_firmware(self):
        """Check firmware.bin exists before starting."""
        if not os.path.exists(FIRMWARE_FILE):
            print(f"\n❌ ERROR: {FIRMWARE_FILE} not found!")
            print(f"\nTo create it:")
            print(f"1. Change FIRMWARE_VERSION to '2.0.0' in C code")
            print(f"2. Run: idf.py build")
            print(f"3. Copy build\\ota_system.bin as firmware.bin")
            print(f"   here in this folder")
            raise FileNotFoundError(FIRMWARE_FILE)

        size = os.path.getsize(FIRMWARE_FILE)
        print(f"\n✅ firmware.bin found")
        print(f"   Size: {size:,} bytes ({size//1024} KB)")

    def start_http_server(self):
        """Start HTTP server in background thread."""
        handler = SilentHTTPHandler
        with socketserver.TCPServer(
                ("", SERVER_PORT), handler) as httpd:
            print(f"\n✅ HTTP server started on port {SERVER_PORT}")
            httpd.serve_forever()

    def _log_event(self, event, details=""):
        """Log an OTA event with timestamp."""
        entry = {
            "time":    datetime.now().strftime('%H:%M:%S'),
            "event":   event,
            "details": details
        }
        self.ota_log.append(entry)
        return entry

    def monitor_serial(self):
        """
        Monitor ESP32 serial output.

        Detects these stages:
        ┌─────────────────────────────────────────┐
        │ BOOT        → ESP32 started             │
        │ WIFI_OK     → Connected to WiFi         │
        │ OTA_START   → Download beginning        │
        │ DOWNLOADING → Firmware transferring     │
        │ OTA_SUCCESS → Download complete         │
        │ REBOOT      → Rebooting to new firmware │
        │ NEW_VERSION → v2.0.0 confirmed running  │
        └─────────────────────────────────────────┘
        """
        try:
            ser = serial.Serial(
                SERIAL_PORT, SERIAL_BAUD, timeout=1)
            print(f"✅ Connected to ESP32 on {SERIAL_PORT}")
            print(f"\n{'─'*55}")
            print(f"  Waiting for ESP32 output...")
            print(f"  (Press Ctrl+C to stop)")
            print(f"{'─'*55}\n")

            ota_success = False
            duration    = 0

            while True:
                try:
                    raw = ser.readline()
                    if not raw:
                        continue

                    line = raw.decode(
                        'utf-8', errors='ignore').strip()
                    if not line:
                        continue

                    # Print with timestamp
                    ts = datetime.now().strftime('%H:%M:%S')
                    print(f"[{ts}] {line}")

                    # ── Detect OTA stages ──────────────

                    # ESP32 booted
                    if "ESP32 OTA Update System" in line:
                        self._log_event("BOOT")
                        print(f"\n🔵 ESP32 BOOTED\n")

                    # WiFi connected
                    elif ("WiFi connected" in line or
                          "Got IP" in line):
                        self._log_event("WIFI_OK", line)
                        print(f"\n🟢 WIFI CONNECTED\n")

                    # OTA starting
                    elif "Starting OTA" in line:
                        self.start_time = time.time()
                        self._log_event("OTA_START")
                        print(f"\n🚀 OTA UPDATE STARTED\n")

                    # Downloading
                    elif "Downloading firmware" in line:
                        self._log_event("DOWNLOADING")
                        print(f"\n⬇️  DOWNLOADING FIRMWARE...")
                        print(f"   Please wait...\n")

                    # Success
                    elif "OTA download SUCCESS" in line:
                        ota_success = True
                        if self.start_time:
                            duration = time.time() - \
                                      self.start_time
                        self._log_event(
                            "OTA_SUCCESS",
                            f"Duration: {duration:.1f}s")
                        print(f"\n✅ OTA DOWNLOAD COMPLETE!")
                        print(f"   Duration: {duration:.1f}s")

                    # Rebooting
                    elif "Rebooting" in line:
                        self._log_event("REBOOT")
                        print(f"\n🔄 REBOOTING INTO NEW FIRMWARE...")
                        print(f"   Waiting for v2.0.0...\n")

                    # New version running
                    elif ("Version: 2.0.0" in line or
                          "version: 2.0.0" in line):
                        self._log_event(
                            "NEW_VERSION",
                            "v2.0.0 confirmed running")
                        print(f"\n🎉 v2.0.0 IS RUNNING!")
                        self.ota_done = True
                        self._generate_report(
                            True, duration)

                    # OTA failed
                    elif "OTA FAILED" in line:
                        self._log_event("OTA_FAILED", line)
                        print(f"\n❌ OTA FAILED!")
                        print(f"   {line}")
                        self._generate_report(
                            False, duration)

                except UnicodeDecodeError:
                    pass

        except serial.SerialException as e:
            print(f"\n❌ Serial error: {e}")
            print(f"   Make sure ESP32 is connected")
            print(f"   And no other program is using {SERIAL_PORT}")

    def _generate_report(self, success, duration):
        """Generate OTA update report."""
        report = {
            "timestamp":     datetime.now().isoformat(),
            "result":        "SUCCESS" if success else "FAILED",
            "duration_sec":  round(duration, 1),
            "firmware_from": "1.0.0",
            "firmware_to":   "2.0.0",
            "events":        self.ota_log
        }

        with open("ota_report.json", "w") as f:
            json.dump(report, f, indent=2)

        print(f"\n{'═'*55}")
        print(f"  OTA UPDATE REPORT")
        print(f"{'═'*55}")
        print(f"  Result:        {'SUCCESS ✅' if success else 'FAILED ❌'}")
        print(f"  From version:  1.0.0")
        print(f"  To version:    2.0.0")
        print(f"  Duration:      {duration:.1f} seconds")
        print(f"  Events logged: {len(self.ota_log)}")
        print(f"  Report saved:  ota_report.json")
        print(f"{'═'*55}\n")

    def run(self):
        """Start everything."""
        print(f"\n📋 STEPS TO RUN OTA UPDATE:")
        print(f"{'─'*55}")
        print(f"1. Make sure ESP32 is plugged in via USB")
        print(f"2. Make sure ESP32 has v1.0.0 flashed")
        print(f"3. Make sure firmware.bin (v2.0.0) is here")
        print(f"4. This server is now starting...")
        print(f"{'─'*55}\n")

        # Start HTTP server in background
        server_thread = threading.Thread(
            target=self.start_http_server,
            daemon=True
        )
        server_thread.start()

        # Small delay for server to start
        time.sleep(1)

        # Monitor serial in main thread
        self.monitor_serial()


# ── Run ───────────────────────────────────────────
if __name__ == "__main__":
    server = OTAServer()
    server.run()