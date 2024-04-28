#!/usr/bin/env python

import sys
import time
import pyds

from dsl import *

uri_rtsp = "rtsp://192.168.1.140:8554/mystream" #"/opt/nvidia/deepstream/deepstream/samples/streams/sample_1080p_h265.mp4"

# Filespecs for the Primary GIE
primary_infer_config_file = \
    '/opt/nvidia/deepstream/deepstream/samples/configs/deepstream-app/config_infer_primary.txt'
primary_model_engine_file = \
    '/opt/nvidia/deepstream/deepstream/samples/models/Primary_Detector/resnet10.caffemodel_b8_gpu0_int8.engine'

# Filespec for the IOU Tracker config file
iou_tracker_config_file = \
    '/opt/nvidia/deepstream/deepstream/samples/configs/deepstream-app/config_tracker_IOU.yml'

# Function to be called on End-of-Stream (EOS) event
def eos_event_listener(client_data):
    print('Pipeline EOS event')
    dsl_pipeline_stop('pipeline')
    dsl_main_loop_quit()

def create_rtsp_source(src_name: str, uri_rtsp: str):
    retval = dsl_source_rtsp_new(src_name,     
            uri = uri_rtsp,     
            protocol = DSL_RTP_ALL,     
            skip_frames = 0,     
            drop_frame_interval = 0,     
            latency=1000,
            timeout=2)   
    return retval

def create_display_sink(is_display: False)->bool:
    if is_display:
        # New window Sink, 0 x/y offsets and same dimensions as Tiled Display
        retval = dsl_sink_window_egl_new('egl-sink', 0, 0, 1280, 720)
        if retval != DSL_RETURN_SUCCESS:
            return False
    else:
        retval = dsl_sink_fake_new('egl-sink')
        if retval != DSL_RETURN_SUCCESS:
            return False
    
    return True


def custom_pad_probe_handler(buffer, user_data):
    frame_number=0
    num_rects=0

    # Retrieve batch metadata from the gst_buffer
    batch_meta = pyds.gst_buffer_get_nvds_batch_meta(buffer)
    l_frame = batch_meta.frame_meta_list
    while l_frame is not None:
        try:
            frame_meta = pyds.glist_get_nvds_frame_meta(l_frame.data)
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

        print(f"Frame Number={frame_number} Number of Objects={obj_counters}")
        
        try:
            l_frame=l_frame.next
        except StopIteration:
            break
    return DSL_PAD_PROBE_OK

def main(args):

    # Since we're not using args, we can Let DSL initialize GST on first call
    while True:

        # New URI File Source
        retval = create_rtsp_source('rtsp-source-1', uri_rtsp)   
        if retval != DSL_RETURN_SUCCESS:
            break
        retval = create_rtsp_source('rtsp-source-2', uri_rtsp)  
        if retval != DSL_RETURN_SUCCESS:
            break
        retval = create_rtsp_source('rtsp-source-3', uri_rtsp)  
        if retval != DSL_RETURN_SUCCESS:
            break
        retval = create_rtsp_source('rtsp-source-4', uri_rtsp)  

        # New Primary GIE using the filespecs above, with interval and Id
        retval = dsl_infer_gie_primary_new('primary-gie', 
            primary_infer_config_file, primary_model_engine_file, 1)
        if retval != DSL_RETURN_SUCCESS:
            break

        # New IOU Tracker, setting operational width and hieght
        retval = dsl_tracker_new('iou-tracker', iou_tracker_config_file, 480, 272)
        if retval != DSL_RETURN_SUCCESS:
            break

        # New Tiler, setting width and height, use default cols/rows set by source count
        retval = dsl_tiler_new('tiler', 1280, 720)
        if retval != DSL_RETURN_SUCCESS:
            break

        # New OSD with text, clock and bbox display all enabled. 
        retval = dsl_osd_new('on-screen-display', 
            text_enabled=True, clock_enabled=True, bbox_enabled=True, mask_enabled=False)
        if retval != DSL_RETURN_SUCCESS:
            break
        
        create_display_sink(is_display=False)
        
        retval = dsl_pph_custom_new('custom-pph', 
            client_handler=custom_pad_probe_handler, client_data=None)
        if retval != DSL_RETURN_SUCCESS:
            break
        
        # Add the custom PPH to the Sink pad (input) of the Tiler
        retval = dsl_tiler_pph_add('tiler', 
            handler='custom-pph', pad=DSL_PAD_SINK)
        if retval != DSL_RETURN_SUCCESS:
            break

        # Add all the components to our pipeline
        retval = dsl_pipeline_new_component_add_many('pipeline', 
            ['rtsp-source-1','rtsp-source-2','rtsp-source-3','rtsp-source-4',
            'primary-gie', 'iou-tracker', 'tiler', 'on-screen-display', 'egl-sink', None])
        if retval != DSL_RETURN_SUCCESS:
            break

        # New Pipeline to use with the above components
        retval = dsl_pipeline_eos_listener_add('pipeline', eos_event_listener, None)
        if retval != DSL_RETURN_SUCCESS:
            break


        # Play the pipeline
        retval = dsl_pipeline_play('pipeline')
        if retval != DSL_RETURN_SUCCESS:
            break

        # Once playing, we can dump the pipeline graph to dot file, which can be converted to an image file for viewing/debugging
        dsl_pipeline_dump_to_dot('pipeline', 'state-playing')

        dsl_main_loop_run()
        break

    # Print out the final result
    print(dsl_return_value_to_string(retval))

    dsl_pipeline_delete_all()
    dsl_component_delete_all()

if __name__ == '__main__':
    sys.exit(main(sys.argv))
