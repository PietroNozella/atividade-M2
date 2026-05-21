import sys
import time
from pathlib import Path

import serial


PORT = "rfc2217://localhost:4000"
FILES = ("main.py", "ssd1306.py")
CHUNK_SIZE = 96


def read_available(ser):
    data = bytearray()
    while True:
        chunk = ser.read(1024)
        if not chunk:
            break
        data.extend(chunk)
    return bytes(data)


def wait_prompt(ser, timeout=5):
    deadline = time.time() + timeout
    data = bytearray()

    while time.time() < deadline:
        chunk = ser.read(1024)
        if chunk:
            data.extend(chunk)
            if data.rstrip().endswith((b">>>", b"...")):
                return bytes(data)
        else:
            time.sleep(0.05)

    raise TimeoutError("Prompt do MicroPython nao respondeu.")


def send_line(ser, line, timeout=5):
    ser.write(line.encode("utf-8") + b"\r\n")
    ser.flush()
    return wait_prompt(ser, timeout)


def stop_program(ser):
    ser.write(b"\x03")
    ser.flush()
    time.sleep(0.3)
    ser.write(b"\r\n")
    ser.flush()
    wait_prompt(ser)


def upload_file(ser, path):
    data = Path(path).read_bytes()
    remote_name = Path(path).name

    print(f"Enviando {remote_name} ({len(data)} bytes)...")
    send_line(ser, f"f = open({remote_name!r}, 'wb')")

    for index in range(0, len(data), CHUNK_SIZE):
        chunk = data[index : index + CHUNK_SIZE]
        send_line(ser, f"f.write({chunk!r})")

    send_line(ser, "f.close()")
    print(f"{remote_name} enviado.")


def run_main(ser):
    print("Executando main.py...")
    ser.write(b"exec(open('main.py').read())\r\n")
    ser.flush()


def main():
    for file_name in FILES:
        if not Path(file_name).exists():
            print(f"Arquivo nao encontrado: {file_name}", file=sys.stderr)
            return 1

    with serial.serial_for_url(PORT, baudrate=115200, timeout=0.5) as ser:
        read_available(ser)
        stop_program(ser)

        for file_name in FILES:
            upload_file(ser, file_name)

        run_main(ser)

    print("Arquivos enviados e main.py iniciado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
