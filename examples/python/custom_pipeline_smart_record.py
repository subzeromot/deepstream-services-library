#!/usr/bin/env python

import sys
import time
import pyds

from dsl import *

PGIE_CLASS_ID_PERSON = 2

uri_rtsp = "rtsp://192.168.1.140:8554/mystream" #"/opt/nvidia/deepstream/deepstream/samples/streams/sample_1080p_h265.mp4"

# Filespecs for the Primary GIE
primary_infer_config_file = \
    '/opt/nvidia/deepstream/deepstream/samples/configs/deepstream-app/config_infer_primary.txt'
primary_model_engine_file = \
    '/opt/nvidia/deepstream/deepstream/samples/models/Primary_Detector/resnet10.caffemodel_b8_gpu0_int8.engine'

# Filespec for the IOU Tracker config file
iou_tracker_config_file = \
    '/opt/nvidia/deepstream/deepstream/samples/configs/deepstream-app/config_tracker_IOU.yml'

class ComponentNames:	
    def __init__(self, source):	
        self.source = source	
        self.record_tap = source + '-record-tap'
        self.always_trigger = source + '-always-trigger'	
        self.ode_handler = source + '-ode-handler'

## 
# Callback function to handle recording session start and stop events
## 
def record_complete_listener(session_info_ptr, client_data):
    print(' ***  Recording Event  *** ')
    
    session_info = session_info_ptr.contents

    print('session_id: ', session_info.session_id)
    
    # If we're starting a new recording for this source
    if session_info.recording_event == DSL_RECORDING_EVENT_START:
        print('event:      ', 'DSL_RECORDING_EVENT_START')

    # Else, the recording session has ended for this source
    else:
        print('event:      ', 'DSL_RECORDING_EVENT_END')
        print('filename:   ', session_info.filename)
        print('dirpath:    ', session_info.dirpath)
        print('duration:   ', session_info.duration)
        print('container:  ', session_info.container_type)
        print('width:      ', session_info.width)
        print('height:     ', session_info.height)

        sesion_name = session_info.filename.split('_')[0]
        retval, is_on = dsl_tap_record_is_on_get(sesion_name)
        if is_on:
            print('Stoping record.')
            dsl_tap_record_session_stop(sesion_name, True)

##
# Function to create all "1-per-source" components, and add them to the Pipeline
# pipeline - unique name of the Pipeline to add the Source components to
# source - unique name for the RTSP Source to create
# uri - unique uri for the new RTSP Source
# ode_handler - Object Detection Event (ODE) handler to add the new Trigger and Actions to
##
def CreatePerSourceComponents(pipeline, source, rtsp_uri, ode_handler):
   
    global duration

    print(source)
    
    # New Component names based on unique source name
    components = ComponentNames(source)
    
    # For each camera, create a new RTSP Source for the specific RTSP URI
    retval = dsl_source_rtsp_new(source, 
        uri = rtsp_uri, 
        protocol = DSL_RTP_ALL, 
        drop_frame_interval = 0, 
        skip_frames=0,
        timeout=2,          # new-buffer timeout of 2 seconds    
        latency=1000        # jitter-buffer size based on latency of 1 second
        )
    if (retval != DSL_RETURN_SUCCESS):
        return retval

    # New record tap created with our common RecordComplete callback function defined above
    retval = dsl_tap_record_new(components.record_tap, 
        outdir = './', 
        container = DSL_CONTAINER_MP4, 
        client_listener = record_complete_listener)
    if (retval != DSL_RETURN_SUCCESS):
        return retval

    # Add the new Tap to the Source directly
    retval = dsl_source_rtsp_tap_add(source, tap=components.record_tap)
    if (retval != DSL_RETURN_SUCCESS):
        return retval

    # Add the new Source with its Record-Tap to the Pipeline	
    retval = dsl_pipeline_component_add(pipeline, source)	
    if (retval != DSL_RETURN_SUCCESS):	
        return retval	
    
    return retval
    

# Function to be called on End-of-Stream (EOS) event
def eos_event_listener(client_data):
    print('Pipeline EOS event')
    dsl_pipeline_stop('pipeline')
    dsl_main_loop_quit()

def create_display_sink(is_display: False)->bool:
    if is_display:
        # New window Sink, 0 x/y offsets and same dimensions as Tiled Display
        retval = dsl_sink_window_egl_new('final-sink', 0, 0, 1280, 720)
        if retval != DSL_RETURN_SUCCESS:
            return False
    else:
        retval = dsl_sink_fake_new('final-sink')
        if retval != DSL_RETURN_SUCCESS:
            return False
    
    return True

def custom_pad_probe_handler(buffer, user_data):
    # Retrieve batch metadata from the gst_buffer
    batch_meta = pyds.gst_buffer_get_nvds_batch_meta(buffer)
    l_frame = batch_meta.frame_meta_list
    while l_frame is not None:
        try:
            frame_meta = pyds.glist_get_nvds_frame_meta(l_frame.data)
            src_index = frame_meta.pad_index
        except StopIteration:
            break

        frame_number=frame_meta.frame_num
        num_rects = frame_meta.num_obj_meta
        l_obj=frame_meta.obj_meta_list
        obj_counters = 0
        while l_obj is not None:
            try:
                # Casting l_obj.data to pyds.NvDsObjectMeta
                obj_meta=pyds.glist_get_nvds_object_meta(l_obj.data)
                obj_counters +=1
            except StopIteration:
                break
            try: 
                l_obj=l_obj.next
            except StopIteration:
                break

            # print(obj_meta.class_id)
        # print(f"Frame Number={frame_number} Number of Objects={obj_counters}")

        if frame_number == 200:
            retval, is_on = dsl_tap_record_is_on_get(f'src-{src_index}-record-tap')
            if is_on:
                print('Recording in progress, stoping first.')
                dsl_tap_record_session_stop(f'src-{src_index}-record-tap', True)
            else:
                print('Start record')
                retval = dsl_tap_record_session_start(
                    f'src-{src_index}-record-tap', 1, 10, None)
                if (retval != DSL_RETURN_SUCCESS):
                    print('record failed')
                    break

        # if frame_number == 400:
        #     retval, is_on = dsl_tap_record_is_on_get(f'src-{src_index}-record-tap')
        #     if is_on:
        #         print('Recording in progress, stoping first.')
        #         dsl_tap_record_session_stop(f'src-{src_index}-record-tap', True)
        
        try:
            l_frame=l_frame.next
        except StopIteration:
            break
    return DSL_PAD_PROBE_OK

def main(args):
    while True:
        # New Primary GIE using the filespecs above, with interval and Id
        retval = dsl_infer_gie_primary_new('pgie', 
            primary_infer_config_file, primary_model_engine_file, 1)
        if retval != DSL_RETURN_SUCCESS:
            break
        
        # New IOU Tracker, setting operational width and hieght
        retval = dsl_tracker_new('tracker', iou_tracker_config_file, 480, 272)
        if retval != DSL_RETURN_SUCCESS:
            break
        # retval = dsl_tracker_ktl_new('tracker', max_width=480, max_height=270)
        # if (retval != DSL_RETURN_SUCCESS):
        #     break

        retval = dsl_tiler_new('tiler', width=1280, height=720)
        if (retval != DSL_RETURN_SUCCESS):
            break

        retval = dsl_osd_new('osd', text_enabled=True, clock_enabled=True,
            bbox_enabled=True, mask_enabled=False)
        if (retval != DSL_RETURN_SUCCESS):
            break
        
        create_display_sink(is_display=False)

        # Create a Pipeline and add the new components.
        retval = dsl_pipeline_new_component_add_many('pipeline', 
            components=['pgie', 'tracker', 'tiler', 'osd', 'final-sink', None]) 
        if (retval != DSL_RETURN_SUCCESS):
            break
    
        # Object Detection Event (ODE) Pad Probe Handler (PPH) to manage our ODE Triggers with their ODE Actions
        retval = dsl_pph_ode_new('ode-handler')
        if (retval != DSL_RETURN_SUCCESS):
            break
    
        # Add the ODE Handler to the Sink (input) pad of the Tiler - before the batched frames are combined/tiled
        retval = dsl_tiler_pph_add('tiler', 'ode-handler', DSL_PAD_SINK)
        if (retval != DSL_RETURN_SUCCESS):
            break


        retval = dsl_pph_custom_new('custom-pph', 
            client_handler=custom_pad_probe_handler, client_data=None)
        if retval != DSL_RETURN_SUCCESS:
            break
        
        # Add the custom PPH to the Sink pad (input) of the Tiler
        retval = dsl_tiler_pph_add('tiler', 
            handler='custom-pph', pad=DSL_PAD_SINK)
        if retval != DSL_RETURN_SUCCESS:
            break

        # For each of our four sources, call the function to create the source-specific components.
        retval = CreatePerSourceComponents('pipeline', 'src-0', uri_rtsp, 'ode-handler')
        if (retval != DSL_RETURN_SUCCESS):
            break
        retval = CreatePerSourceComponents('pipeline', 'src-1', uri_rtsp, 'ode-handler')
        if (retval != DSL_RETURN_SUCCESS):
            break
        retval = CreatePerSourceComponents('pipeline', 'src-2', uri_rtsp, 'ode-handler')
        if (retval != DSL_RETURN_SUCCESS):
            break
        retval = CreatePerSourceComponents('pipeline', 'src-3', uri_rtsp, 'ode-handler')
        if (retval != DSL_RETURN_SUCCESS):
            break
        
        # Pipeline has been successfully created, ok to play
        retval = dsl_pipeline_play('pipeline')
        if (retval != DSL_RETURN_SUCCESS):
            break

        # join the main loop until stopped. 
        dsl_main_loop_run()
        break

    # Print out the final result
    print(dsl_return_value_to_string(retval))

    # free up all resources
    dsl_pipeline_delete_all()
    dsl_component_delete_all()

if __name__ == '__main__':
    sys.exit(main(sys.argv))
