import RPi.GPIO as GPIO
import time

# === Configuration ===
PIR_PIN = 22  # Adjust if your PIR is connected to a different GPIO

# === Setup ===
GPIO.setmode(GPIO.BCM)
GPIO.setup(PIR_PIN, GPIO.IN)

print("Monitoring PIR sensor state (CTRL+C to stop)...")
print("HIGH = motion detected | LOW = no motion\n")

try:
    while True:
        state = GPIO.input(PIR_PIN)
        print(f"PIR state: {'HIGH (Motion)' if state else 'LOW (No motion)'}")
        time.sleep(0.5)
except KeyboardInterrupt:
    print("\nExiting.")
finally:
    GPIO.cleanup()
