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

# Based on DualCam 2021.1 Design
#    reference : http://avnet.me/u96v2-dualcam-2020.2
    
import numpy as np
import cv2
import os
import glob
import subprocess

def get_media_dev_by_name(src):
    devices = glob.glob("/dev/media*")
    for dev in devices:
        proc = subprocess.run(['media-ctl','-d',dev,'-p'], capture_output=True, encoding='utf8')
        for line in proc.stdout.splitlines():
            if src in line:
                return dev

def get_video_dev_by_name(src):
    devices = glob.glob("/dev/video*")
    for dev in devices:
        proc = subprocess.run(['v4l2-ctl','-d',dev,'-D'], capture_output=True, encoding='utf8')
        for line in proc.stdout.splitlines():
            if src in line:
                return dev

def get_v4l_subdev_by_name(src):
    devices = glob.glob("/dev/media*")
    found_src = 0
    for dev in devices:
        proc = subprocess.run(['media-ctl','-d',dev,'-p'], capture_output=True, encoding='utf8')
        for line in proc.stdout.splitlines():
            if found_src == 0:
                if src in line:
                    found_src = 1
            if found_src == 1:
                if "v4l-subdev" in line:
                    words = line.split()
                    return words[-1]


class DualCam():
	  
  def __init__(self, cap_config='ar0144_dual', cap_width=1280, cap_height=800):
  
    self.cap_config = cap_config
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

    print("\n\r[DualCam] Looking for devices corresponding to AP1302")
    dev_video = get_video_dev_by_name("vcap_CAPTURE_PIPELINE_v_proc_ss")
    dev_media = get_media_dev_by_name("vcap_CAPTURE_PIPELINE_v_proc_ss")
    dev_ap1302_subdev = get_v4l_subdev_by_name("ap1302.4-003c (3 pads, 3 links)")
    print(dev_video)
    print(dev_media)
    print(dev_ap1302_subdev)
    self.dev_video = dev_video
    self.dev_media = dev_media
    self.dev_ap1302_subdev = dev_ap1302_subdev

    print("\n\r[DualCam] Initializing capture pipeline for ",self.cap_config,self.cap_width,self.cap_height)
            
    cmd = "media-ctl -d "+dev_media+" -V \"'ap1302.4-003c':2 [fmt:UYVY8_1X16/"+self.input_resolution+" field:none]\""
    print(cmd)
    os.system(cmd)

    cmd = "media-ctl -d "+dev_media+" -V \"'b0000000.mipi_csi2_rx_subsystem':0 [fmt:UYVY8_1X16/"+self.input_resolution+" field:none]\""
    print(cmd)
    os.system(cmd)
    cmd = "media-ctl -d "+dev_media+" -V \"'b0000000.mipi_csi2_rx_subsystem':1 [fmt:UYVY8_1X16/"+self.input_resolution+" field:none]\""
    print(cmd)
    os.system(cmd)

    cmd = "media-ctl -d "+dev_media+" -V \"'b0010000.v_proc_ss':0 [fmt:UYVY8_1X16/"+self.input_resolution+" field:none]\""
    print(cmd)
    os.system(cmd)
    cmd = "media-ctl -d "+dev_media+" -V \"'b0010000.v_proc_ss':1 [fmt:RBG24/"+self.input_resolution+" field:none]\""
    print(cmd)
    os.system(cmd)

    cmd = "media-ctl -d "+dev_media+" -V \"'b0040000.v_proc_ss':0 [fmt:RBG24/"+self.input_resolution+" field:none]\""
    print(cmd)
    os.system(cmd)
    cmd = "media-ctl -d "+dev_media+" -V \"'b0040000.v_proc_ss':1 [fmt:RBG24/"+self.output_resolution+" field:none]\""
    print(cmd)
    os.system(cmd)

    cmd = "v4l2-ctl -d "+dev_video+"  --set-fmt-video=width="+str(self.output_width)+",height="+str(self.output_height)+",pixelformat=BGR3"
    print(cmd)
    os.system(cmd)

    if cap_config == 'ar0144_dual' or cap_config == 'ar0144_single':
       print("\n\r[DualCam] Disabling Auto White Balance")
       cmd = "yavta --no-query -w '0x009a0914 0' "+dev_ap1302_subdev
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

    print("\n\r[DualCam] Opening cv2.VideoCapture for ",self.output_width,self.output_height)

    gst_pipeline = "v4l2src device="+dev_video+" io-mode=\"dmabuf\" ! video/x-raw, width="+str(self.output_width)+", height="+str(self.output_height)+", format=BGR, framerate=60/1 ! appsink" 
    print("GStreamer pipeline = "+gst_pipeline)
    self.cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)
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
  
    self.cap_dual = True
    self.cap_width = 0
    self.cap_height = 0

    self.input_resolution = 'WxH'
    self.output_width = 0
    self.output_height = 0
    self.output_resolution = 'WxH'

    self.dev_video = ""
    self.dev_media = ""
    
    del self.cap
    self.cap = None


