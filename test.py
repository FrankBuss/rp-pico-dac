#!/usr/bin/env python3

import serial
import random

def write_samples(buf):
    with serial.Serial('/dev/ttyACM0', 115200, timeout=0.1) as ser:
        data = "s"
        for b in buf:
            data += "%02x" % (b & 0xff)
        data += "."
        ser.write(bytes(data, "ascii"))
        ser.flush()
        print(ser.readline())

buf = bytes(200000)
write_samples(buf)
