################################################################################
# The MIT License
#
# Copyright (c) 2019-2023, Prominence AI, Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.
################################################################################

# ````````````````````````````````````````````````````````````````````````````````````
# This example demonstrates the use of a Smart-Record Sink and how
# a recording session can be started on user demand - in this case
# by pressing the 'S' key.  The xwindow_key_event_handler calls
# dsl_sink_record_session_start with:
#   start-time = the seconds before the current time (i.e.the amount of 
#                cache/history to include.
#   duration =  the seconds after the start of recording.
# Therefore, a total of startTime + duration seconds of data will be recorded.
# 

#!/usr/bin/env python

import sys
from dsl import *

# RTSP Source URI for AMCREST Camera    
amcrest_rtsp_uri = 'rtsp://username:password@192.168.1.108:554/cam/realmonitor?channel=1&subtype=0'    

# RTSP Source URI for HIKVISION Camera    
hikvision_rtsp_uri = 'rtsp://admin:Segvisual44@192.168.1.64:554/Streaming/Channels/101'    

# Filespecs for the Primary GIE
primary_infer_config_file = \
    '/opt/nvidia/deepstream/deepstream/samples/configs/deepstream-app/config_infer_primary_nano.txt'
primary_model_engine_file = \
    '/opt/nvidia/deepstream/deepstream/samples/models/Primary_Detector/resnet10.caffemodel_b8_gpu0_fp16.engine'

# Filespec for the IOU Tracker config file
iou_tracker_config_file = \
    '/opt/nvidia/deepstream/deepstream/samples/configs/deepstream-app/config_tracker_IOU.yml'

PGIE_CLASS_ID_VEHICLE = 0
PGIE_CLASS_ID_BICYCLE = 1
PGIE_CLASS_ID_PERSON = 2
PGIE_CLASS_ID_ROADSIGN = 3

TILER_WIDTH = DSL_STREAMMUX_DEFAULT_WIDTH
TILER_HEIGHT = DSL_STREAMMUX_DEFAULT_HEIGHT
WINDOW_WIDTH = TILER_WIDTH
WINDOW_HEIGHT = TILER_HEIGHT

## 
# Function to be called on XWindow KeyRelease event
## 
def xwindow_key_event_handler(key_string, client_data):
    print('key released = ', key_string)
    if key_string.upper() == 'S':
        retval = dsl_sink_record_session_start(
            'record-sink', 20, 20, None)
    if key_string.upper() == 'P':
        dsl_pipeline_pause('pipeline')
    elif key_string.upper() == 'R':
        dsl_pipeline_play('pipeline')
    elif key_string.upper() == 'Q' or key_string == '' or key_string == '':
        dsl_pipeline_stop('pipeline')
        dsl_main_loop_quit()
 
## 
# Function to be called on XWindow Delete event
## 
def xwindow_delete_event_handler(client_data):
    print('delete window event')
    dsl_pipeline_stop('pipeline')
    dsl_main_loop_quit()

## 
# Function to be called on End-of-Stream (EOS) event
## 
def eos_event_listener(client_data):
    print('Pipeline EOS event')
    dsl_pipeline_stop('pipeline')
    dsl_main_loop_quit()

## 
# Function to be called on every change of Pipeline state
## 
def state_change_listener(old_state, new_state, client_data):
    print('previous state = ', old_state, ', new state = ', new_state)
    if new_state == DSL_STATE_PLAYING:
        dsl_pipeline_dump_to_dot('pipeline', "state-playing")

## 
# Function to be called on recording complete
## 
def record_complete_listener(session_info_ptr, client_data):
    print(' ***  Recording Event  *** ')
    
    session_info = session_info_ptr.contents

    print('session_id: ', session_info.session_id)
    
    # If we're starting a new recording for this source
    if session_info.recording_event == DSL_RECORDING_EVENT_START:
        print('event:      ', 'DSL_RECORDING_EVENT_START')

        # enable the always trigger showing the metadata for "recording in session" 
        retval = dsl_ode_trigger_enabled_set('rec-on-trigger', enabled=True)
        if (retval != DSL_RETURN_SUCCESS):
            print('Enable always trigger failed with error: ', 
                dsl_return_value_to_string(retval))

    # Else, the recording session has ended for this source
    else:
        print('event:      ', 'DSL_RECORDING_EVENT_END')
        print('filename:   ', session_info.filename)
        print('dirpath:    ', session_info.dirpath)
        print('duration:   ', session_info.duration)
        print('container:  ', session_info.container_type)
        print('width:      ', session_info.width)
        print('height:     ', session_info.height)

        # disable the always trigger showing the metadata for "recording in session" 
        retval = dsl_ode_trigger_enabled_set('rec-on-trigger', enabled=False)
        if (retval != DSL_RETURN_SUCCESS):
            print('Enable always trigger failed with error: ', 
                dsl_return_value_to_string(retval))

def main(args):

    # Since we're not using args, we can Let DSL initialize GST on first call
    while True:

        # ````````````````````````````````````````````````````````````````````````````
        # New Record-Sink that will buffer encoded video while waiting for the 
        # ODE trigger/action, defined below, to start a new session on first 
        # occurrence of a bicycle. The default 'cache-size' and 'duration' are 
        # defined in DslApi.h Setting the bit rate to 0 to not change from the default.
        retval = dsl_sink_record_new('record-sink', outdir="./", codec=DSL_CODEC_H264, 
            container=DSL_CONTAINER_MP4, bitrate=0, interval=0, 
            client_listener=record_complete_listener)
        if retval != DSL_RETURN_SUCCESS:
            break

        # IMPORTANT: Best to set the default cache-size to the maximum value we 
        # intend to use (see the xwindow_key_event_handler callback above). 
#        retval = dsl_sink_record_cache_size_set('record-sink', 30)
        if retval != DSL_RETURN_SUCCESS:
            break

        # Since the Record-Sink is derived from the Encode-Sink, we can use the 
        # dsl_sink_encode_dimensions_set service to change the recording dimensions 
        # at the input to the encoder. Note: the dimensions can also be controlled
        # after the video encoder by calling dsl_sink_record_dimensions_set
        retval = dsl_sink_encode_dimensions_set('record-sink', width=640, height=360)
        if retval != DSL_RETURN_SUCCESS:
            break
            
        # ````````````````````````````````````````````````````````````````````````````
        # Create new RGBA color types
        retval = dsl_display_type_rgba_color_custom_new('opaque-red', 
            red=1.0, blue=0.5, green=0.5, alpha=0.7)
        if retval != DSL_RETURN_SUCCESS:
            break
        retval = dsl_display_type_rgba_color_custom_new('full-red', 
            red=1.0, blue=0.0, green=0.0, alpha=1.0)
        if retval != DSL_RETURN_SUCCESS:
            break
        retval = dsl_display_type_rgba_color_custom_new('full-white', 
            red=1.0, blue=1.0, green=1.0, alpha=1.0)
        if retval != DSL_RETURN_SUCCESS:
            break
        retval = dsl_display_type_rgba_color_custom_new('opaque-black', 
            red=0.0, blue=0.0, green=0.0, alpha=0.8)
        if retval != DSL_RETURN_SUCCESS:
            break
        retval = dsl_display_type_rgba_font_new('impact-20-white', 
            font='impact', size=20, color='full-white')
        if retval != DSL_RETURN_SUCCESS:
            break
            
        # Create a new Text type object that will be used to show 
        # the recording in progress
        retval = dsl_display_type_rgba_text_new('rec-text', 
            'REC    ', x_offset=10, y_offset=30, font='impact-20-white', 
            has_bg_color=True, bg_color='opaque-black')
        if retval != DSL_RETURN_SUCCESS:
            break
        # A new RGBA Circle to be used to simulate a red LED light 
        # for the recording in progress.
        retval = dsl_display_type_rgba_circle_new('red-led', 
        x_center=94, y_center=52, radius=8, 
            color='full-red', has_bg_color=True, bg_color='full-red')
        if retval != DSL_RETURN_SUCCESS:
            break
            
        # Create a new Action to display the "recording in-progress" text
        retval = dsl_ode_action_display_meta_add_many_new('add-rec-on',
            display_types=['rec-text', 'red-led', None])
        if retval != DSL_RETURN_SUCCESS:
            break
            
        # Create an Always Trigger that will trigger on every frame when enabled.
        # We use this trigger to display meta data while the recording is in session.
        # POST_OCCURRENCE_CHECK == after all other triggers are processed first.
        retval = dsl_ode_trigger_always_new('rec-on-trigger',     
            source=DSL_ODE_ANY_SOURCE, when=DSL_ODE_POST_OCCURRENCE_CHECK)    
        if (retval != DSL_RETURN_SUCCESS):    
            return retval    

        retval = dsl_ode_trigger_action_add('rec-on-trigger', action='add-rec-on')
        if retval != DSL_RETURN_SUCCESS:
            break

        # Disable the trigger, to be re-enabled in the recording_event listener callback
        retval = dsl_ode_trigger_enabled_set('rec-on-trigger', enabled=False)    
        if (retval != DSL_RETURN_SUCCESS):    
            return retval

            
        # ````````````````````````````````````````````````````````````````````````````
        # New ODE Handler for our Trigger
        retval = dsl_pph_ode_new('ode-handler')
        if retval != DSL_RETURN_SUCCESS:
            break
        retval = dsl_pph_ode_trigger_add('ode-handler', 'rec-on-trigger')
        if retval != DSL_RETURN_SUCCESS:
            break
    
        ##############################################################################
        #
        # Create the remaining Pipeline components
        
#        retval = dsl_source_file_new('file-source', uri_h265, True)
#        if retval != DSL_RETURN_SUCCESS:
#            break
        
        # New RTSP Source
        retval = dsl_source_rtsp_new('rtsp-source',     
            uri = hikvision_rtsp_uri,     
            protocol = DSL_RTP_ALL,     
            skip_frames = 0,     
            drop_frame_interval = 0,     
            latency=100,
            timeout=2)    
        if (retval != DSL_RETURN_SUCCESS):    
            return retval    

        # New Primary GIE using the filespecs above with interval = 1
        retval = dsl_infer_gie_primary_new('primary-gie', 
            primary_infer_config_file, primary_model_engine_file, 1)
        if retval != DSL_RETURN_SUCCESS:
            break

        # New IOU Tracker, setting operational width and hieght
        retval = dsl_tracker_new('iou-tracker', iou_tracker_config_file, 480, 272)
        if retval != DSL_RETURN_SUCCESS:
            break

        # New OSD with text, clock and bbox display all enabled. 
        retval = dsl_osd_new('on-screen-display', 
            text_enabled=True, clock_enabled=True, bbox_enabled=True, mask_enabled=False)
        if retval != DSL_RETURN_SUCCESS:
            break

        # add our ODE Pad Probe Handle to the Sink Pad of the Tiler
        retval = dsl_osd_pph_add('on-screen-display', 'ode-handler', DSL_PAD_SINK)
        if retval != DSL_RETURN_SUCCESS:
            break
 
        # New Window Sink, 0 x/y offsets and same dimensions as Tiled Display
        retval = dsl_sink_window_new('window-sink', 0, 0, WINDOW_WIDTH, WINDOW_HEIGHT)
        if retval != DSL_RETURN_SUCCESS:
            break

        # Add all the components to our pipeline - except for our second source and overlay sink 
        retval = dsl_pipeline_new_component_add_many('pipeline', 
            ['rtsp-source', 'primary-gie', 'iou-tracker',
            'on-screen-display', 'record-sink', 'window-sink', None])
#            ['rtsp-source', 'primary-gie', 'iou-tracker', 
#            'on-screen-display', 'record-sink', 'window-sink', None])
        if retval != DSL_RETURN_SUCCESS:
            break
            
        # Add the XWindow event handler functions defined above
        retval = dsl_pipeline_xwindow_key_event_handler_add("pipeline", xwindow_key_event_handler, None)
        if retval != DSL_RETURN_SUCCESS:
            break
        retval = dsl_pipeline_xwindow_delete_event_handler_add("pipeline", xwindow_delete_event_handler, None)
        if retval != DSL_RETURN_SUCCESS:
            break

        ## Add the listener callback functions defined above
        retval = dsl_pipeline_state_change_listener_add('pipeline', state_change_listener, None)
        if retval != DSL_RETURN_SUCCESS:
            break
        retval = dsl_pipeline_eos_listener_add('pipeline', eos_event_listener, None)
        if retval != DSL_RETURN_SUCCESS:
            break

        # Play the pipeline
        retval = dsl_pipeline_play('pipeline')
        if retval != DSL_RETURN_SUCCESS:
            break

        dsl_main_loop_run()
        retval = DSL_RETURN_SUCCESS
        break

    # Print out the final result
    print(dsl_return_value_to_string(retval))

    # Cleanup all DSL/GST resources
    dsl_delete_all()
    
if __name__ == '__main__':
    sys.exit(main(sys.argv))
    