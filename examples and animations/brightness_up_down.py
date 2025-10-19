import serial
import time

# Configuration
PORT = "COM4"
BAUDRATE = 115200

def main():
    ser = serial.Serial(PORT, BAUDRATE, timeout=1)
    num = 0
    direction = 1  # 1 = increasing, -1 = decreasing

    try:
        while True:
            # Send 'I' and number as two bytes
            data = bytes([ord('I'), num])
            ser.write(data)
            print(f"Sent: I {num}")

            # Wait for 'A' acknowledgment
            ack = ser.read(1)
            if ack == b'A':
                print("Received ACK")
                num += direction
                # Reverse direction at limits
                if num >= 128:
                    direction = -1
                elif num <= 0:
                    direction = 1
                
                time.sleep(0.05)
            else:
                print("No ACK received, retrying...")
                time.sleep(0.1)
    except KeyboardInterrupt:
        print("Stopped by user.")
    finally:
        ser.close()

if __name__ == "__main__":
    main()
