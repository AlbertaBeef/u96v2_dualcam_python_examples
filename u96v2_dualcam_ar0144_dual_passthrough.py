'''
Copyright 2021 Avnet Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
'''

import numpy as np
import cv2
import argparse
import sys
import os

sys.path.append(os.path.abspath('../'))
sys.path.append(os.path.abspath('./'))
from u96v2_sbc_dualcam.dualcam import DualCam

# USAGE
# python dual_passthrough.py [--input 0] [--width 640] [--height 480]

# construct the argument parse and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-i", "--input", required=False,
	help = "input camera identifier (default = 0)")
ap.add_argument("-W", "--width", required=False,
	help = "input width (default = 640)")
ap.add_argument("-H", "--height", required=False,
	help = "input height (default = 480)")
args = vars(ap.parse_args())

if not args.get("input",False):
  inputId = 0
else:
  inputId = int(args["input"])
print('[INFO] input camera identifier = ',inputId)

if not args.get("width",False):
  width = 640
else:
  width = int(args["width"])
if not args.get("height",False):
  height = 480
else:
  height = int(args["height"])
print('[INFO] input resolution = ',width,'X',height)

# Initialize the capture pipeline
print("[INFO] Initializing the capture pipeline ...")
dualcam = DualCam('ar0144_dual',inputId,width,height)

while(True):
  # Capture input
  left,right = dualcam.capture_dual()

  # dual passthrough
  output = cv2.hconcat([left,right])

  # Display output
  cv2.imshow('u96v2_sbc_dualcam_ar0144 - dual passthrough',output)
  if cv2.waitKey(1) & 0xFF == ord('q'):
    break

# When everything done, release the capture
dualcam.release()
cv2.destroyAllWindows()

