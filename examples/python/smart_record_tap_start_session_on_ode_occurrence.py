################################################################################    
# The MIT License    
#    
# Copyright (c) 2023, Prominence AI, Inc.
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
# This example demonstrates the use of a Smart-Record Tap and how to start
# a recording session on the "occurrence" of an Object Detection Event (ODE).
# An ODE Occurrence Trigger, with a limit of 1 event, is used to trigger
# on the first detection of a Person object. The Trigger uses an ODE "Start 
# Recording Session Action" setup with the following parameters:
#   start-time: the seconds before the current time (i.e.the amount of 
#               cache/history to include.
#   duration:   the seconds after the current time (i.e. the amount of 
#               time to record after session start is called).
# Therefore, a total of start-time + duration seconds of data will be recorded.
#
# Record Tap components tap into RTSP Source components pre-decoder to enable
# smart-recording of the incomming (original) H.264 or H.265 stream. 
#
# Additional ODE Actions are added to the Trigger to 1) print the ODE 
# data (source-id, batch-id, object-id, frame-number, object-dimensions, etc.)
# to the console and 2) to capture the object (bounding-box) to a JPEG file.
# 
# A basic inference Pipeline is used with PGIE, Tracker, Tiler, OSD, and Window Sink.
#
# DSL Display Types are used to overlay text ("REC") with a red circle to
# indicate when a recording session is in progress. An ODE "Always-Trigger" and an 
# ODE "Add Display Meta Action" are used to add the text's and circle's metadata
# to each frame while the Trigger is enabled. The record_event_listener callback,
# called on both DSL_RECORDING_EVENT_START and DSL_RECORDING_EVENT_END, enables
# and disables the "Always Trigger" according to the event received. 
#
# IMPORTANT: the record_event_listener is used to reset the one-shot Occurrence-
# Trigger when called with DSL_RECORDING_EVENT_END. This allows a new recording
# session to be started on the next occurrence of a Person. 
#
# IMPORTANT: this demonstrates a multi-source Pipeline, each with their own
# Smart-Recort Tap.

#!/usr/bin/env python    

import sys    
import time    
from dsl import *    

# RTSP Source URI's  
src_url_1 = 'rtsp://192.168.100.13:8554/mystream'    
src_url_2 = 'rtsp://192.168.100.13:8554/mystream'    
src_url_3 = 'rtsp://192.168.100.13:8554/mystream'    
src_url_4 = 'rtsp://192.168.100.13:8554/mystream'    

# Filespecs (Jetson and dGPU) for the Primary GIE
primary_infer_config_file = \
    '/opt/nvidia/deepstream/deepstream/samples/configs/deepstream-app/config_infer_primary.txt'
primary_model_engine_file = \
    '/opt/nvidia/deepstream/deepstream/samples/models/Primary_Detector/resnet10.caffemodel_b8_gpu0_int8.engine'

# Filespec for the IOU Tracker config file
iou_tracker_config_file = \
    '/opt/nvidia/deepstream/deepstream/samples/configs/deepstream-app/config_tracker_IOU.yml'

TILER_WIDTH = DSL_1K_HD_WIDTH    
TILER_HEIGHT = DSL_1K_HD_HEIGHT    
WINDOW_WIDTH = DSL_1K_HD_WIDTH    
WINDOW_HEIGHT = DSL_1K_HD_HEIGHT    

PGIE_CLASS_ID_VEHICLE = 0    
PGIE_CLASS_ID_BICYCLE = 1    
PGIE_CLASS_ID_PERSON = 2    
PGIE_CLASS_ID_ROADSIGN = 3    

##     
# Function to be called on XWindow KeyRelease event    
##     
def xwindow_key_event_handler(key_string, client_data):    
    print('key released = ', key_string)    
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
# Function to create all Display Types used in this example    
##     
def create_display_types():    

    # ````````````````````````````````````````````````````````````````````````````````````````````````````````    
    # Create new RGBA color types    
    retval = dsl_display_type_rgba_color_custom_new('full-red', 
        red=1.0, blue=0.0, green=0.0, alpha=1.0)    
    if retval != DSL_RETURN_SUCCESS:    
        return retval    
    retval = dsl_display_type_rgba_color_custom_new('full-white', 
        red=1.0, blue=1.0, green=1.0, alpha=1.0)    
    if retval != DSL_RETURN_SUCCESS:    
        return retval    
    retval = dsl_display_type_rgba_color_custom_new('opaque-black', 
        red=0.0, blue=0.0, green=0.0, alpha=0.8)    
    if retval != DSL_RETURN_SUCCESS:    
        return retval    
    retval = dsl_display_type_rgba_font_new('impact-20-white', 
        font='impact', size=20, color='full-white')    
    if retval != DSL_RETURN_SUCCESS:    
        return retval    

    # Create a new Text type object that will be used to show the 
    # recording in progress    
    retval = dsl_display_type_rgba_text_new('rec-text', 'REC    ', 
        x_offset=10, y_offset=30, font='impact-20-white', 
        has_bg_color=True, bg_color='opaque-black')    
    if retval != DSL_RETURN_SUCCESS:    
        return retval    
    # A new RGBA Circle to be used to simulate a red LED light for 
    # the recording in progress.    
    return dsl_display_type_rgba_circle_new('red-led', 
        x_center=94, y_center=52, radius=8,     
        color='full-red', has_bg_color=True, bg_color='full-red')    

##     
# Objects of this class will be used as "client_data" for all callback
# notifications. defines a class of all component names associated with 
# a single RTSP Source. The names are derived from the unique Source name    
##    
class ComponentNames:    
    def __init__(self, source):    
        self.source = source    
        self.instance_trigger = source + '-instance-trigger'
        self.always_trigger = source + '-always-trigger'
        self.record_tap = source + '-record-tap'    
        self.start_record = source + '-start-record'
        self.display_meta = source + '-display-meta'
        
##
# Client listner function callad at the start and end of a recording session
##
def OnRecordingEvent(session_info_ptr, client_data):

    if client_data == None:
        return None

    # cast the C void* client_data back to a py_object pointer and deref
    components = cast(client_data, POINTER(py_object)).contents.value

    session_info = session_info_ptr.contents

    print('session_id: ', session_info.session_id)
    
    # If we're starting a new recording for this source
    if session_info.recording_event == DSL_RECORDING_EVENT_START:
        print('event:      ', 'DSL_RECORDING_EVENT_START')

        # enable the always trigger showing the metadata for "recording in session" 
        retval = dsl_ode_trigger_enabled_set(components.always_trigger, enabled=True)
        if (retval != DSL_RETURN_SUCCESS):
            print('Enable always trigger failed with error: ', 
                dsl_return_value_to_string(retval))

        # in this example we will call on the Tiler to show the source 
        #that started recording.    
        retval = dsl_tiler_source_show_set('tiler', source=components.source, 
            timeout=0, has_precedence=True)    
        if (retval != DSL_RETURN_SUCCESS):
            print('Tiler show single source failed with error: ', 
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
        retval = dsl_ode_trigger_enabled_set(components.always_trigger, enabled=False)
        if (retval != DSL_RETURN_SUCCESS):
            print('Disable always trigger failed with error:', 
                dsl_return_value_to_string(retval))

        # if we're showing the source that started this recording
        # we can set the tiler back to showing all tiles, otherwise
        # another source has started recording and taken precendence
        retval, current_source, timeout  = dsl_tiler_source_show_get('tiler')
        if retval == DSL_RETURN_SUCCESS and current_source == components.source:
            dsl_tiler_source_show_all('tiler')

        # re-enable the one-shot trigger for the next "New Instance" of a person
        retval = dsl_ode_trigger_reset(components.instance_trigger)    
        if (retval != DSL_RETURN_SUCCESS):
            print('Failed to reset instance trigger with error:', 
                dsl_return_value_to_string(retval))

    return None
    
##    
# Function to create all "1-per-source" components, and add them to the Pipeline    
# pipeline - unique name of the Pipeline to add the Source components to    
# source - unique name for the RTSP Source to create    
# uri - unique uri for the new RTSP Source    
# ode_handler - Object Detection Event (ODE) handler - to add the new Triggers 
#               and Actions to
#
##    
def CreatePerSourceComponents(pipeline, source, rtsp_uri, ode_handler):    

    # New Component names based on unique source name    
    components = ComponentNames(source)    

    # For each camera, create a new RTSP Source for the specific RTSP URI    
    retval = dsl_source_rtsp_new(source,     
        uri = rtsp_uri,     
        protocol = DSL_RTP_ALL,     
        skip_frames = 0,     
        drop_frame_interval = 0,     
        latency = 2000, # jitter-buffer size based on latency of 2 sec. 
        timeout = 2)    
    if (retval != DSL_RETURN_SUCCESS):    
        return retval    

    # New record tap created with our common OnRecordingEvent callback function defined above    
    retval = dsl_tap_record_new(components.record_tap,     
        outdir = './',     
        container = DSL_CONTAINER_MP4,     
        client_listener = OnRecordingEvent)    
    if (retval != DSL_RETURN_SUCCESS):    
        return retval    

    # Add the new Tap to the Source directly    
    retval = dsl_source_rtsp_tap_add(source, tap=components.record_tap)    
    if (retval != DSL_RETURN_SUCCESS):    
        return retval    

    # Next, create the Person Instance Trigger. We will reset the trigger 
    # on DSL_RECORDING_EVENT_END. See the OnRecordingEvent() client callback 
    # function above
    retval = dsl_ode_trigger_instance_new(components.instance_trigger,     
        source=source, class_id=PGIE_CLASS_ID_PERSON, limit=1)    
    if (retval != DSL_RETURN_SUCCESS):    
        return retval    

    # Create a new Action to start the record session for this Source, 
    # with the component names as client data    
    retval = dsl_ode_action_tap_record_start_new(components.start_record,     
        record_tap=components.record_tap, start=5, duration=10, client_data=components)    
    if (retval != DSL_RETURN_SUCCESS):    
        return retval    

    # Add the Actions to the trigger for this source.     
    retval = dsl_ode_trigger_action_add_many(components.instance_trigger,     
        actions=[components.start_record, None])    
    if (retval != DSL_RETURN_SUCCESS):    
        return retval    

    # Add the new Source with its Record-Tap to the Pipeline    
    retval = dsl_pipeline_component_add(pipeline, source)    
    if (retval != DSL_RETURN_SUCCESS):    
        return retval    

    # Create an action to add the metadata for the "recording in session" indicator
    retval = dsl_ode_action_display_meta_add_many_new(components.display_meta,
        display_types= ['rec-text', 'red-led', None])
    if (retval != DSL_RETURN_SUCCESS):    
        return retval    
    
    # Create an Always Trigger that will trigger on every frame when enabled.
    # We use this trigger to display meta data while the recording is in session.
    # POST_OCCURRENCE_CHECK == after all other triggers are processed first.
    retval = dsl_ode_trigger_always_new(components.always_trigger,     
        source=source, when=DSL_ODE_POST_OCCURRENCE_CHECK)    
    if (retval != DSL_RETURN_SUCCESS):    
        return retval    

    # Disable the trigger, to be re-enabled in the recording_event listener callback
    retval = dsl_ode_trigger_enabled_set(components.always_trigger, enabled=False)    
    if (retval != DSL_RETURN_SUCCESS):    
        return retval
    
    # Add the display meta action 
    retval = dsl_ode_trigger_action_add(components.always_trigger, 
        action=components.display_meta)

    # Add the Instance and Always Triggers to the ODE Pad Probe Handler    
    return dsl_pph_ode_trigger_add_many(ode_handler, 
        triggers=[components.instance_trigger, components.always_trigger, None])    


def main(args):    

    # Since we're not using args, we can Let DSL initialize GST on first call    
    while True:    

        retval = create_display_types()        
        if retval != DSL_RETURN_SUCCESS:    
            break    

        # Create a new Action to display the "recording in-progress" text    
        retval = dsl_ode_action_display_meta_add_new('rec-text-overlay', 'rec-text')    
        if retval != DSL_RETURN_SUCCESS:    
            break    
        # Create a new Action to display the "recording in-progress" LED    
        retval = dsl_ode_action_display_meta_add_new('red-led-overlay', 'red-led')    
        if retval != DSL_RETURN_SUCCESS:    
            break    

        ## New Primary GIE using the filespecs above with interval = 4
        retval = dsl_infer_gie_primary_new('primary-gie', 
            primary_infer_config_file, primary_model_engine_file, 4)
        if retval != DSL_RETURN_SUCCESS:
            break

        # New IOU Tracker, setting operational width and hieght
        retval = dsl_tracker_new('iou-tracker', iou_tracker_config_file, 480, 272)
        if retval != DSL_RETURN_SUCCESS:
            break

        # New Tiler, setting width and height, use default cols/rows set by 
        # the number of sources
        retval = dsl_tiler_new('tiler', TILER_WIDTH, TILER_HEIGHT)
        if retval != DSL_RETURN_SUCCESS:
            break

        # Object Detection Event (ODE) Pad Probe Handler (PPH) to manage our ODE 
        # Triggers with their ODE Actions    
        retval = dsl_pph_ode_new('ode-handler')    
        if (retval != DSL_RETURN_SUCCESS):    
            break    

        # New OSD with text, clock and bbox display all enabled. 
        retval = dsl_osd_new('on-screen-display', 
            text_enabled=True, clock_enabled=True, 
            bbox_enabled=True, mask_enabled=False)
        if retval != DSL_RETURN_SUCCESS:
            break

         # Add our ODE Pad Probe Handler to the Sink pad of the OSD
        retval = dsl_osd_pph_add('on-screen-display', 
            handler='ode-handler', pad=DSL_PAD_SINK)
        if retval != DSL_RETURN_SUCCESS:
            break

        # New Window Sink, 0 x/y offsets and dimensions.
        retval = dsl_sink_window_egl_new('egl-sink', 0, 0, WINDOW_WIDTH, WINDOW_HEIGHT)
        if retval != DSL_RETURN_SUCCESS:
            break

        # Live Source so best to set the Window-Sink's sync enabled setting to false.
        retval = dsl_sink_sync_enabled_set('egl-sink', False)
        if retval != DSL_RETURN_SUCCESS:
            break

        # Add the XWindow event handler functions defined above to the Window Sink
        retval = dsl_sink_window_key_event_handler_add('egl-sink', 
            xwindow_key_event_handler, None)
        if retval != DSL_RETURN_SUCCESS:
            break
        retval = dsl_sink_window_delete_event_handler_add('egl-sink', 
            xwindow_delete_event_handler, None)
        if retval != DSL_RETURN_SUCCESS:
            break

        # Add all the components to our pipeline    
        retval = dsl_pipeline_new_component_add_many('pipeline',     
            ['primary-gie', 'iou-tracker', 'tiler',
            'on-screen-display', 'egl-sink', None])    
        if retval != DSL_RETURN_SUCCESS:    
            break    

        # For each of our four sources, call the funtion to create the 
        # source-specific components.    
        retval = CreatePerSourceComponents('pipeline', 
            'src-1', src_url_1, 'ode-handler')    
        if (retval != DSL_RETURN_SUCCESS):    
            break    
#        retval = CreatePerSourceComponents('pipeline', 
#            'src-2', src_url_2, 'ode-handler')    
        if (retval != DSL_RETURN_SUCCESS):    
            break    
#        retval = CreatePerSourceComponents('pipeline', 
#            'src-3', src_url_3, 'ode-handler')    
        if (retval != DSL_RETURN_SUCCESS):    
            break    
#        retval = CreatePerSourceComponents('pipeline', 
#            'src-4', src_url_4, 'ode-handler')    
        if (retval != DSL_RETURN_SUCCESS):    
            break    

        # Syncronize all live input sources (buffers) at the Streammux
        retval = dsl_pipeline_streammux_sync_inputs_enabled_set('pipeline', True)
        if retval != DSL_RETURN_SUCCESS:    
            break    
        
        ## Add the listener callback functions defined above    
        retval = dsl_pipeline_state_change_listener_add('pipeline', 
            state_change_listener, None)    
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
