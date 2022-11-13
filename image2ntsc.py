#!/usr/bin/env python3

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

def rgb2gray(rgb):
    return np.dot(rgb[...,:3], [0.299, 0.587, 0.114])

img = mpimg.imread('test.jpg')
gray = rgb2gray(img)
gray = gray / 255
img_mat = gray


# port from https://github.com/lscardoso/gr-ntsc-rc/blob/master/lib/transmitter_c_impl.cc

# -------------- NTSC SIGNAL TIMING (in sec.) ----------------
HORIZONTAL_SYNC_DURATION = 4.7 * 0.000001
BACK_PORCH_DURATION = 4.7  * 0.000001
VIDEO_DURATION = 52.6  * 0.000001
FRONT_PORCH_DURATION = 1.5 * 0.000001
LINE_DURATION = 63.5 * 0.000001

# ------------------- NTSC SIGNAL LEVELS ---------------------
BLACK_LEVEL = -0.02
WHITE_LEVEL = 0.06
HORIZONTAL_SYNC_THRESHOLD = -0.020
HORIZONTAL_SYNC_LEVEL = -0.04
BACK_PORCH_LEVEL = -0.015
FRONT_PORCH_LEVEL = -0.015
EQUALISING_LEVEL = -0.015
VERTICAL_SYNC_LEVEL = -0.04

# -------------------- NTSC LINES FEATURES -------------------
NBR_VIDEO_LINES = 240
NBR_EQUALISING_LINES = 3
NBR_VERTICAL_SYNC_LINES = 21
X_WIDTH = 360
Y_HEIGHT = 240

# -------------------- NTSC SIGNAL STATES -------------------
IDLE = 1
LINES_TRANSMISSION = 2
FRONT_PORCH = 3
HORIZONTAL_SYNC = 4
BACK_PORCH = 5
VIDEO = 6
VERTICAL_SYNC = 7
EQUALISING = 8
SERRATION = 9
BLANKING = 10
EVEN = 1
ODD = 0

d_samp_rate = 5*1000*1000
d_meta_state = VERTICAL_SYNC
d_sub_state = EQUALISING
d_frame_parity = EVEN
d_samples_cnt = 0
d_lines_cnt = 0

samples = 167432
out = [0] * samples

for i in range(samples):
    d_samples_cnt += 1

    # ------------------- META STATE MACHINE -----------------
    if d_meta_state == LINES_TRANSMISSION:

        # ---------------------- SUB STATE MACHINE -----------------

        # *** HORIZONTAL SYNCHRONISATION ***
        if d_sub_state == HORIZONTAL_SYNC:
            out[i] = HORIZONTAL_SYNC_LEVEL

            # Time for Back Porch
            if d_samples_cnt > HORIZONTAL_SYNC_DURATION * d_samp_rate:
                d_sub_state = BACK_PORCH
                d_samples_cnt = 0

        # *** BACK PORCH ***
        if d_sub_state == BACK_PORCH:
            out[i] = BACK_PORCH_LEVEL

            # Time for Active Video
            if d_samples_cnt > BACK_PORCH_DURATION * d_samp_rate:
                d_sub_state = VIDEO;
                d_samples_cnt = 0;

        # *** ACTIVE VIDEO ***
        if d_sub_state == VIDEO:
            # Transmit pixel's black and white level from img_mat in image_matrix.h
            out[i] = BLACK_LEVEL + (WHITE_LEVEL - BLACK_LEVEL) * img_mat[int(d_lines_cnt)][int(358 * d_samples_cnt / (d_samp_rate * VIDEO_DURATION))]

            # Time for Front Porch
            if d_samples_cnt > VIDEO_DURATION * d_samp_rate:
                d_sub_state = FRONT_PORCH
                d_samples_cnt = 0


        # *** FRONT PORCH ***
        if d_sub_state == FRONT_PORCH:
            out[i] = FRONT_PORCH_LEVEL

            # Time for Horizontal Sync
            if d_samples_cnt > FRONT_PORCH_DURATION * d_samp_rate:
                d_sub_state = HORIZONTAL_SYNC
                d_samples_cnt = 0
                d_lines_cnt += 1

        # Exit to  Vertical Sync
        if d_lines_cnt == NBR_VIDEO_LINES:
            d_meta_state = VERTICAL_SYNC
            d_sub_state = EQUALISING
            d_samples_cnt = 0
            d_lines_cnt = 0
            print("samples: " + str(i))

    # ------------------- META STATE MACHINE -----------------
    if d_meta_state == VERTICAL_SYNC:

        # ---------------------- SUB STATE MACHINE -----------------

        # *** EQUALISING_PULSES ***
        if d_sub_state == EQUALISING:

            # Set the Right Output
            if d_samples_cnt < HORIZONTAL_SYNC_DURATION * d_samp_rate:
                out[i] = HORIZONTAL_SYNC_LEVEL
            else:
                out[i] = EQUALISING_LEVEL

            # New Equalising Line
            if d_samples_cnt > 0.5 * LINE_DURATION * d_samp_rate:
                d_samples_cnt = 0
                d_lines_cnt += 0.5

            # Exit to Serration Lines for pre-equalising
            if d_lines_cnt == NBR_EQUALISING_LINES:
                d_sub_state = SERRATION
                d_samples_cnt = 0

            # Exit to SERRATION LINES for post-equalising
            if (d_lines_cnt == 3 * NBR_EQUALISING_LINES and d_frame_parity == ODD) or (d_lines_cnt == 3 * NBR_EQUALISING_LINES - 0.5 and d_frame_parity == EVEN):
                d_sub_state = BLANKING
                d_samples_cnt = 0

        # *** SERRATION PULSES ***
        if d_sub_state == SERRATION:

            # Set Right Output
            if d_samples_cnt > (0.5 * LINE_DURATION - HORIZONTAL_SYNC_DURATION) * d_samp_rate:
                out[i] = EQUALISING_LEVEL
            else:
                out[i] = HORIZONTAL_SYNC_LEVEL

            # New Serration Line
            if d_samples_cnt > 0.5 * LINE_DURATION * d_samp_rate:
                d_samples_cnt = 0
                d_lines_cnt += 0.5

            # Exit to Equalising Lines
            if d_lines_cnt == 2 * NBR_EQUALISING_LINES:
                d_sub_state = EQUALISING
                d_samples_cnt = 0

        # *** BLANKING PULSES ***
        if d_sub_state == BLANKING:

            # Set Right Output
            if d_samples_cnt < HORIZONTAL_SYNC_DURATION * d_samp_rate:
                out[i] = HORIZONTAL_SYNC_LEVEL
            else:
                out[i] = EQUALISING_LEVEL

            # New Blanking Line
            if d_samples_cnt > LINE_DURATION * d_samp_rate:
                d_samples_cnt = 0
                d_lines_cnt += 1

            # Exit VERTICAL_SYNC YYY
            if (d_lines_cnt == NBR_VERTICAL_SYNC_LINES and d_frame_parity == ODD) or (d_lines_cnt == NBR_VERTICAL_SYNC_LINES + 1.5 and d_frame_parity == EVEN):
                d_meta_state = LINES_TRANSMISSION
                d_sub_state = HORIZONTAL_SYNC
                if d_frame_parity == EVEN:
                    d_frame_parity = ODD
                else:
                    d_frame_parity = EVEN
                d_samples_cnt = 0
                d_lines_cnt = 0

minv = min(out)
maxv = max(out)
d = maxv - minv
for i in range(len(out)):
    out[i] = int((out[i] - minv) / d * 255)

for i in range(len(out)):
    print("0x%02x, " % out[i], end='')
    if i % 16 == 0:
        print()
print()
