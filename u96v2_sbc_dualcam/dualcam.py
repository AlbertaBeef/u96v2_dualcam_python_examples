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

# Based on DualCam 2020.2 Design
#    reference : http://avnet.me/u96v2-dualcam-2020.2
    
import numpy as np
import cv2
import os


class DualCam():
	  
  def __init__(self, cap_config='ar0144_dual', cap_id=0, cap_width=1280, cap_height=800):
  
    self.cap_config = cap_config
    self.cap_id = cap_id
    self.cap_width = cap_width
    self.cap_height = cap_height
    
    self.input_resolution = 'WxH'
    self.output_width = 0
    self.output_height = 0
    self.output_resolution = 'WxH'

    if cap_config == 'ar0144_dual':
      self.input_resolution = '2560x800'
      self.output_width = self.cap_width*2
      self.output_height = self.cap_height
      self.output_resolution = str(self.output_width)+'x'+str(self.output_height)
    elif cap_config == 'ar0144_single':
      self.input_resolution = '1280x800'
      self.output_width = self.cap_width
      self.output_height = self.cap_height
      self.output_resolution = str(self.output_width)+'x'+str(self.output_height)
    elif cap_config == 'ar1335_single':
      self.input_resolution = '3840x2160'
      self.output_width = self.cap_width
      self.output_height = self.cap_height
      self.output_resolution = str(self.output_width)+'x'+str(self.output_height)
    else:
      print("[DualCam] Invalid cap_config = ",cap_config," !  (must be ar0144_dual|ar0144_single|ar1335_single)")
      return None

    print("\n\r[DualCam] Initializing capture pipeline for ",self.cap_config,self.cap_id,self.cap_width,self.cap_height)
            
    cmd = "media-ctl -d /dev/media0 -V \"'ap1302.4-003c':2 [fmt:UYVY8_1X16/"+self.input_resolution+" field:none]\""
    print(cmd)
    os.system(cmd)

    cmd = "media-ctl -d /dev/media0 -V \"'b0000000.mipi_csi2_rx_subsystem':0 [fmt:UYVY8_1X16/"+self.input_resolution+" field:none]\""
    print(cmd)
    os.system(cmd)
    cmd = "media-ctl -d /dev/media0 -V \"'b0000000.mipi_csi2_rx_subsystem':1 [fmt:UYVY8_1X16/"+self.input_resolution+" field:none]\""
    print(cmd)
    os.system(cmd)

    cmd = "media-ctl -d /dev/media0 -V \"'b0010000.v_proc_ss':0 [fmt:UYVY8_1X16/"+self.input_resolution+" field:none]\""
    print(cmd)
    os.system(cmd)
    cmd = "media-ctl -d /dev/media0 -V \"'b0010000.v_proc_ss':1 [fmt:RBG24/"+self.input_resolution+" field:none]\""
    print(cmd)
    os.system(cmd)

    cmd = "media-ctl -d /dev/media0 -V \"'b0040000.v_proc_ss':0 [fmt:RBG24/"+self.input_resolution+" field:none]\""
    print(cmd)
    os.system(cmd)
    cmd = "media-ctl -d /dev/media0 -V \"'b0040000.v_proc_ss':1 [fmt:RBG24/"+self.output_resolution+" field:none]\""
    print(cmd)
    os.system(cmd)

    cmd = "v4l2-ctl -d /dev/video0  --set-fmt-video=width="+str(self.output_width)+",height="+str(self.output_height)+",pixelformat=BGR3"
    print(cmd)
    os.system(cmd)

    if cap_config == 'ar0144_dual':
      print("\n\r[DualCam] Configuring AP1302 for left-right side-by-side configuration")

      cmd = "i2cset -f -y 4 0x3c 0x10 0x0C 0x00 0x04 i"
      print(cmd)
      os.system(cmd)

    if cap_config == 'ar1335_single':
      print("\n\r[DualCam] Configuring AP1302 for no horizontal/vertical flip")

      cmd = "i2cset -f -y 4 0x3c 0x10 0x0C 0x00 0x00 i"
      print(cmd)
      os.system(cmd)

      print("\n\r[DualCam] Configuring AP1302 to enable auto-focus")

      cmd = "i2cset -f -y 4 0x3c 0x50 0x58 0x11 0x86 i"
      print(cmd)
      os.system(cmd)

    print("\n\r[DualCam] Opening cv2.VideoCapture for ",self.cap_id,self.output_width,self.output_height)

    self.cap = cv2.VideoCapture(self.cap_id)
    self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,self.output_width)
    self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT,self.output_height)

    print("\n\r")

  def capture(self):
    
    if not (self.cap.grab()):
      print("[DualCam] No more frames !")
      return None

    _, frame = self.cap.retrieve()
    
    return frame
  

  def capture_dual(self):
    
    if not (self.cap.grab()):
      print("[DualCam] No more frames !")
      return None

    _, frame = self.cap.retrieve()
    
    left  = frame[:,1:(self.cap_width)+1,:]
    right = frame[:,(self.cap_width):(self.cap_width*2)+1,:]    
    
    return left,right    
  

  def release(self):
  
    self.cap_id = 0
    self.cap_dual = True
    self.cap_width = 0
    self.cap_height = 0

    self.input_resolution = 'WxH'
    self.output_width = 0
    self.output_height = 0
    self.output_resolution = 'WxH'
    
    del self.cap
    self.cap = None


