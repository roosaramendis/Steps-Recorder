bl_info = {
    "name": "Steps Recorder",
    "blender": (4, 0, 0),
    "category": "3D View",
    "author": "Roosara Mendis",
    "version": (1, 0, 0),
    "location": "View3D > Sidebar",
    "description": "Capture steps of your Workflow with time interval to create timelapse video",
    "warning": "",
    "doc_url": "",
    "tracker_url": "",
    "support": "COMMUNITY",
}

import bpy
import os



filepath = bpy.path.abspath(__file__)
directory = os.path.dirname(filepath)
def register():
    from .operators import (
        TimelapsePanel,
        StartTimelapseOperator,
        StopTimelapseOperator,
        ExportAsVideoOperator,
        ManageTimelapseOperator,
        StepRecoderPreferences
        
    )
    
    # Register properties
    bpy.types.Scene.timelapse_isolate_blender = bpy.props.BoolProperty(
        name="Isolate Blender Window",
        description="Isolate the Blender window for the Recording(you can use this to record only the blender window and not the whole screen)",
        default=False
    )
    
    bpy.types.Scene.timelapse_image_format = bpy.props.EnumProperty(
        name="Image Format",
        items=[
            ('PNG', "PNG", "Save screenshots as .png"),
            ('JPEG', "JPEG", "Save screenshots as .jpg"),
        ],
        default='PNG',
        description="Choose the image format for screenshots. PNG is lossless and more file size per image, JPEG is for less file size but bit lossy with compression(depends on quality setting)"
    )

    bpy.types.Scene.timelapse_jpeg_quality = bpy.props.IntProperty(
        name="JPEG Quality",
        default=90,
        min=0,
        max=100
    )
    bpy.types.Scene.timelapse_folder = bpy.props.StringProperty(
        name="Base Timelapse Folder",
        subtype='DIR_PATH',
        default="//Steps Recorder/timelapse/"
        #default=os.path.join(directory, "timelapse")
    )
    
    bpy.types.Scene.timelapse_screenshot_folder = bpy.props.StringProperty(
        name="Screenshots Folder",
        subtype='DIR_PATH'
    )

    bpy.types.Scene.timelapse_video_folder = bpy.props.StringProperty(
        name="Videos Folder",
        subtype='DIR_PATH'
    )

    bpy.types.Scene.timelapse_interval = bpy.props.FloatProperty(
        name="Interval",
        default=1.0,
        min=0.2,
        description="Interval between screenshots in seconds. less means lengthy and smoother video more means short and fast n blocky video"
        
    )
    
    # Register classes
    bpy.utils.register_class(TimelapsePanel)
    bpy.utils.register_class(StartTimelapseOperator)
    bpy.utils.register_class(StopTimelapseOperator)
    bpy.utils.register_class(ExportAsVideoOperator)
    bpy.utils.register_class(ManageTimelapseOperator)
    bpy.utils.register_class(StepRecoderPreferences)

def unregister():
    from .operators import (
        TimelapsePanel,
        StartTimelapseOperator,
        StopTimelapseOperator,
        ExportAsVideoOperator,
        ManageTimelapseOperator,
        StepRecoderPreferences
    )
    
    # Unregister classes
    bpy.utils.unregister_class(TimelapsePanel)
    bpy.utils.unregister_class(StartTimelapseOperator)
    bpy.utils.unregister_class(StopTimelapseOperator)
    bpy.utils.unregister_class(ExportAsVideoOperator)
    bpy.utils.unregister_class(ManageTimelapseOperator)
    bpy.utils.unregister_class(StepRecoderPreferences)
    
    # Delete properties
    del bpy.types.Scene.timelapse_image_format
    del bpy.types.Scene.timelapse_jpeg_quality
    del bpy.types.Scene.timelapse_folder
    del bpy.types.Scene.timelapse_screenshot_folder
    del bpy.types.Scene.timelapse_video_folder
    del bpy.types.Scene.timelapse_interval
    del bpy.types.Scene.timelapse_isolate_blender

