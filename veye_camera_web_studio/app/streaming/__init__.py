"""VEYE live-streaming subsystem.

Layered, pluggable design (see project plan):

    Stage 0  Configurator  -> per platform x series pre-capture camera setup
                              (media-ctl / v4l2-ctl / config script + I2C writes)
    Stage 1  Provider      -> platform-specific GStreamer capture + encode stage
    Stage 2  Transport     -> protocol-specific output + delivery to the browser
    Stage 3  StreamService -> orchestrates configure -> gst-launch subprocess lifecycle
"""
