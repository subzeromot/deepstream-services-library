FROM nvcr.io/nvidia/deepstream:6.2-devel
ENV NVIDIA_DRIVER_CAPABILITIES $NVIDIA_DRIVER_CAPABILITIES,video
ENV LOGLEVEL="INFO"
ENV GST_DEBUG=2
ENV GST_DEBUG_FILE=/app/GST_DEBUG.log

RUN apt update -y && apt-get -y install \
    libgstrtspserver-1.0-dev \
    gstreamer1.0-rtsp \
    libapr1 \
    libapr1-dev \
    libaprutil1 \
    libaprutil1-dev \
    libgeos-dev \
    libcurl4-openssl-dev

RUN apt-get -y install \
    libavformat-dev \
    libswscale-dev  

# RUN apt -y install libapr*
RUN python3 -m pip install --upgrade pip
RUN pip3 install pyds_ext opencv_python apsw
RUN apt install libopencv-dev

# RUN apt install -y  python3-gi python3-dev python3-gst-1.0 python-gi-dev git python-dev \
#     python3 python3-pip python3.8-dev cmake g++ build-essential libglib2.0-dev \
#     libglib2.0-dev-bin libgstreamer1.0-dev libtool m4 autoconf automake libgirepository1.0-dev libcairo2-dev -y

# # RTSP
# RUN apt-get install -y libgstrtspserver-1.0-0 gstreamer1.0-rtsp libgirepository1.0-dev gobject-introspection gir1.2-gst-rtsp-server-1.0

# RUN apt-get install -y gstreamer1.0-libav \
#     && apt-get install --reinstall -y gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly libavresample-dev \
#     libavresample4 libavutil-dev libavutil56 libavcodec-dev libavcodec58 libavformat-dev libavformat58 libavfilter7 libde265-dev \
#     libde265-0 libx265-179 libx264-155 libvpx6 libmpeg2encpp-2.1-0 libmpeg2-4 libmpg123-0 -y

# docker run --gpus all -it --rm --net=host --privileged -v /tmp/.X11-unix:/tmp/.X11-unix -v $(pwd):/workspace -e DISPLAY=$DISPLAY -w /workspace deepstream_dsl:latest