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

# USAGE
# python stereo_face_detection.py [--input 0] [--width 640] [--height 480] [--detthreshold 0.55] [--nmsthreshold 0.35]

from ctypes import *
from typing import List
import cv2
import numpy as np
import vart
import pathlib
import xir
import os
import math
import threading
import time
import sys
import argparse
import sys

sys.path.append(os.path.abspath('../'))
sys.path.append(os.path.abspath('./'))
from u96v2_sbc_dualcam.dualcam import DualCam
from vitis_ai_vart.facedetect import FaceDetect
from vitis_ai_vart.facelandmark import FaceLandmark
from vitis_ai_vart.utils import get_child_subgraph_dpu


# construct the argument parse and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-i", "--input", required=False,
	help = "input camera identifier (default = 0)")
ap.add_argument("-W", "--width", required=False,
	help = "input width (default = 640)")
ap.add_argument("-H", "--height", required=False,
	help = "input height (default = 480)")
ap.add_argument("-d", "--detthreshold", required=False,
	help = "face detector softmax threshold (default = 0.55)")
ap.add_argument("-n", "--nmsthreshold", required=False,
	help = "face detector NMS threshold (default = 0.35)")
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

if not args.get("detthreshold",False):
  detThreshold = 0.55
else:
  detThreshold = float(args["detthreshold"])
print('[INFO] face detector - softmax threshold = ',detThreshold)

if not args.get("nmsthreshold",False):
  nmsThreshold = 0.35
else:
  nmsThreshold = float(args["nmsthreshold"])
print('[INFO] face detector - NMS threshold = ',nmsThreshold)

# Initialize Vitis-AI/DPU based face detector
densebox_xmodel = "/usr/share/vitis_ai_library/models/densebox_640_360/densebox_640_360.xmodel"
densebox_graph = xir.Graph.deserialize(densebox_xmodel)
densebox_subgraphs = get_child_subgraph_dpu(densebox_graph)
assert len(densebox_subgraphs) == 1 # only one DPU kernel
densebox_dpu = vart.Runner.create_runner(densebox_subgraphs[0],"run")
dpu_face_detector = FaceDetect(densebox_dpu,detThreshold,nmsThreshold)
dpu_face_detector.start()

# Initialize Vitis-AI/DPU based face landmark
landmark_xmodel = "/usr/share/vitis_ai_library/models/face_landmark/face_landmark.xmodel"
landmark_graph = xir.Graph.deserialize(landmark_xmodel)
landmark_subgraphs = get_child_subgraph_dpu(landmark_graph)
assert len(landmark_subgraphs) == 1 # only one DPU kernel
landmark_dpu = vart.Runner.create_runner(landmark_subgraphs[0],"run")
dpu_face_landmark = FaceLandmark(landmark_dpu)
dpu_face_landmark.start()

# Initialize the capture pipeline
print("[INFO] Initializing the capture pipeline ...")
dualcam = DualCam('ar0144_dual',inputId,width,height)

# inspired from cvzone.Utils.py
def cornerRect( img, bbox, l=20, t=5, rt=1, colorR=(255,0,255), colorC=(0,255,0)):

	#x1,y1,w,h = bbox
	#x2,y2 = x+w, y+h
	x1,y1,x2,y2 = bbox
	x1 = int(x1)
	x2 = int(x2)
	y1 = int(y1)
	y2 = int(y2)

	if rt != 0:
		cv2.rectangle(img,(x1,y1),(x2,y2),colorR,rt)

	# Top Left x1,y1
	cv2.line(img, (x1,y1), (x1+l,y1), colorC, t)
	cv2.line(img, (x1,y1), (x1,y1+l), colorC, t)
	# Top Right x2,y1
	cv2.line(img, (x2,y1), (x2-l,y1), colorC, t)
	cv2.line(img, (x2,y1), (x2,y1+l), colorC, t)
	# Top Left x1,y2
	cv2.line(img, (x1,y2), (x1+l,y2), colorC, t)
	cv2.line(img, (x1,y2), (x1,y2-l), colorC, t)
	# Top Left x2,y2
	cv2.line(img, (x2,y2), (x2-l,y2), colorC, t)
	cv2.line(img, (x2,y2), (x2,y2-l), colorC, t)

	return img

bUseLandmarks = False
nLandmarkId = 2

# loop over the frames from the video stream
while True:
	# Capture image from camera
	left_frame,right_frame = dualcam.capture_dual()

	# Make copies of left/right images for graphical annotations and display
	frame1 = left_frame.copy()
	frame2 = right_frame.copy()

	# Vitis-AI/DPU based face detector
	left_faces = dpu_face_detector.process(left_frame)
	right_faces = dpu_face_detector.process(right_frame)

	# if one face detected in each image, calculate the centroids to detect distance range
	distance_valid = False
	if (len(left_faces) == 1) & (len(right_faces) == 1):

		# loop over the left faces
		for i,(left,top,right,bottom) in enumerate(left_faces):
			cornerRect(frame2,(left,top,right,bottom),colorR=(255,255,255),colorC=(255,255,255))
 
			# centroid
			if bUseLandmarks == False:  
				x = int((left+right)/2)
				y = int((top+bottom)/2)
				cv2.circle(frame2,(x,y),4,(255,255,255),-1)
			# get left coordinate (keep float, for full precision)  
			left_cx = (left+right)/2
			left_cy = (top+bottom)/2

			# get face landmarks
			startX = int(left)
			startY = int(top)
			endX   = int(right)
			endY   = int(bottom)      
			face = left_frame[startY:endY, startX:endX]
			landmarks = dpu_face_landmark.process(face)
			if bUseLandmarks == True:  
				for i in range(5):
					x = startX + int(landmarks[i,0] * (endX-startX))
					y = startY + int(landmarks[i,1] * (endY-startY))
					cv2.circle( frame2, (x,y), 3, (255,255,255), 2)
				x = startX + int(landmarks[nLandmarkId,0] * (endX-startX))
				y = startY + int(landmarks[nLandmarkId,1] * (endY-startY))
				cv2.circle( frame2, (x,y), 4, (255,255,255), -1)
			# get left coordinate (keep float, for full precision)  
			left_lx = left   + (landmarks[nLandmarkId,0] * (right-left))
			left_ly = bottom + (landmarks[nLandmarkId,1] * (bottom-top))  

		# loop over the right faces
		for i,(left,top,right,bottom) in enumerate(right_faces): 
			cornerRect(frame2,(left,top,right,bottom),colorR=(255,255,0),colorC=(255,255,0))

			# centroid
			if bUseLandmarks == False:  
				x = int((left+right)/2)
				y = int((top+bottom)/2)
				cv2.circle(frame2,(x,y),4,(255,255,0),-1)
			# get right coordinate (keep float, for full precision)  
			right_cx = (left+right)/2
			right_cy = (top+bottom)/2

			# get face landmarks
			startX = int(left)
			startY = int(top)
			endX   = int(right)
			endY   = int(bottom)      
			face = right_frame[startY:endY, startX:endX]
			landmarks = dpu_face_landmark.process(face)
			if bUseLandmarks == True:  
				for i in range(5):
					x = startX + int(landmarks[i,0] * (endX-startX))
					y = startY + int(landmarks[i,1] * (endY-startY))
					cv2.circle( frame2, (x,y), 3, (255,255,0), 2)  
				x = startX + int(landmarks[nLandmarkId,0] * (endX-startX))
				y = startY + int(landmarks[nLandmarkId,1] * (endY-startY))
				cv2.circle( frame2, (x,y), 4, (255,255,0), -1)  
			# get right coordinate (keep float, for full precision)  
			right_lx = left   + (landmarks[nLandmarkId,0] * (right-left))
			right_ly = bottom + (landmarks[nLandmarkId,1] * (bottom-top))  

		delta_cx = abs(left_cx - right_cx)
		delta_cy = abs(right_cy - left_cy)
		message1 = "delta_cx="+str(int(delta_cx))

		delta_lx = abs(left_lx - right_lx)
		delta_ly = abs(right_ly - left_ly)
		message2 = "delta_lx="+str(int(delta_lx))

		if bUseLandmarks == False:  
			delta_x = delta_cx
			delta_y = delta_cy
			cv2.putText(frame2,message1,(20,20),cv2.FONT_HERSHEY_SIMPLEX,0.75,(255,255,0),2)
			cv2.putText(frame2,message2,(20,40),cv2.FONT_HERSHEY_SIMPLEX,0.75,(255,255,255),2)

		if bUseLandmarks == True:  
			delta_x = delta_lx
			delta_y = delta_ly
			cv2.putText(frame2,message1,(20,20),cv2.FONT_HERSHEY_SIMPLEX,0.75,(255,255,255),2)
			cv2.putText(frame2,message2,(20,40),cv2.FONT_HERSHEY_SIMPLEX,0.75,(255,255,0),2)

		# distance = (baseline * focallength) / disparity
		#    ref : https://learnopencv.com/introduction-to-epipolar-geometry-and-stereo-vision/
		#
		# baseline = 50 mm (measured)
		# focal length = 2.48mm * (1 pixel / 0.003mm) = 826.67 pixels => gives better results
		# focal length = 2.48mm * (1280 pixels / 5.565mm) = 570 pixels => 
		#    ref: http://avnet.me/ias-ar0144-datasheet
		#
		disparity = delta_x * (1280 / width) # scale back to active array
		distance = (50 * 827) / (disparity)
		#distance = (50 * 570) / (disparity)
		message1 = "disparity : "+str(int(disparity))+" pixels"
		message2 = "distance : "+str(int(distance))+" mm"
		cv2.putText(frame1,message1,(20,20),cv2.FONT_HERSHEY_SIMPLEX,0.75,(255,255,255),2)
		cv2.putText(frame1,message2,(20,40),cv2.FONT_HERSHEY_SIMPLEX,0.75,(255,255,255),2)

		if ( (distance > 500) & (distance < 1000) ):
			distance_valid = True
                    
	# loop over the left faces
	for i,(left,top,right,bottom) in enumerate(left_faces): 

		if distance_valid == True:
			cornerRect(frame1,(left,top,right,bottom),colorR=(0,255,0),colorC=(0,255,0))
		if distance_valid == False:
			cornerRect(frame1,(left,top,right,bottom),colorR=(0,0,255),colorC=(0,0,255))


	# Display the processed image
	display_frame = cv2.hconcat([frame1, frame2])
	cv2.imshow("Stereo Face Detection", display_frame)
	key = cv2.waitKey(1) & 0xFF

	if key == ord("d"):
		bUseLandmarks = not bUseLandmarks
		print("bUseLandmarks = ",bUseLandmarks);

	if key == ord("l"):
		nLandmarkId = nLandmarkId + 1
		if nLandmarkId >= 5:
			nLandmarkId = 0
		print("nLandmarkId = ",nLandmarkId);
  

	# if the `q` key was pressed, break from the loop
	if key == ord("q"):
		break

# Stop the face detector
dpu_face_detector.stop()
del densebox_dpu

# Stop the landmark detector
dpu_face_landmark.stop()
del landmark_dpu

# Cleanup
cv2.destroyAllWindows()
