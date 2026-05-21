import time

import serial


PORT = "rfc2217://localhost:4000"


with serial.serial_for_url(PORT, baudrate=115200, timeout=1) as ser:
    ser.write(b"\x03")
    ser.flush()
    time.sleep(0.2)
    ser.write(b"\x01")
    ser.flush()
    time.sleep(0.5)
