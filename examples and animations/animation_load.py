#!/usr/bin/env python3
import serial
import sys
import time

def send_file_to_device(port, file_path):
    baudrate = 115200  # fixed baudrate
    chunk_size = 8      # now 8 bytes per frame
    trycount = 1000
    
    try:
        with open(file_path, "rb") as f:
            data = f.read()
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return

    total_chunks = (len(data) + chunk_size - 1) // chunk_size

    with serial.Serial(port, baudrate, timeout=1) as ser:
        print(f"Opened serial port {port} at {baudrate} bps")
        ser.write(b'R')
        ser.flush()
        time.sleep(0.5)
        ser.write(b'D')
        ser.flush()
        i = 0
        #for i in range(total_chunks):
        while(i < total_chunks):
            # Send start handshake
            
            # Wait for acknowledgement
            ack = ser.read(1)
            
            while ack != b'A':
                if 0 == trycount:
                    print(f"Did not receive ACK for chunk {i+1}, received: {ack}")
                    return
                else:
                    print(ack)
                    trycount -= 1
                    # Optional small delay
                    ser.write(b'R')
                    ser.flush()
                    time.sleep(0.5)
                    ser.write(b'D')
                    ack = ser.read(1)
                    i = 0
                    
            
            trycount = 1000
            
            # Send next 8-byte chunk
            start = i * chunk_size
            end = min(start + chunk_size, len(data))
            chunk = data[start:end]

            # Pad the last chunk with 0xFF if needed
            if len(chunk) < chunk_size:
                chunk += b'\xFF' * (chunk_size - len(chunk))

            ser.write(chunk)
            ser.flush()

            print(f"Sent chunk {i+1}/{total_chunks} ({len(chunk)} bytes)")

            # Optional small delay
            i += 1
            time.sleep(0.0001)

        print("File transmission complete.")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python send_file.py <serial_port> <binary_file>")
        sys.exit(1)

    serial_port = sys.argv[1]
    binary_file = sys.argv[2]

    send_file_to_device(serial_port, binary_file)
