import bpy
import os
import time
import threading
from bpy.app.timers import register
import queue
import subprocess
import ctypes
import re


# Initializing Values
is_running = False
screenshot_interval = 1.0
last_depsgraph_ss_time = 0
depsgraph_handler_registered = False
file_index = 0
extension = 'png'
onlyCaptureBlender = 0



def numeric_sort_key(filename):
    # Extract the first number from the filename for sorting
    match = re.search(r'\d+', filename)
    return int(match.group()) if match else float('inf')


def get_blender_window_title():
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    hwnd = user32.GetForegroundWindow()

    length = user32.GetWindowTextLengthW(hwnd)
    buff = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buff, length + 1)

    title = buff.value
    return title
"""
def start_external_app():
    try:
        
        app_path = bpy.path.abspath("F:/github/SS_ServerApp/x64/Debug/SS_ServerApp.exe")
        subprocess.Popen([app_path])
        print(f"[INFO] Started external screenshot app: {app_path}")
    except Exception as e:
        print(f"[ERROR] Failed to start external screenshot app: {e}")

def send_screenshot_command(filepath, image_format, qlty_str, onlyCaptureBlenderwindow=0, blenderWindowTitle="Blender"):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(("127.0.0.1", 5001))
            message = f"SS|{filepath}|{image_format}|{qlty_str}|{onlyCaptureBlenderwindow}|{blenderWindowTitle}"
            s.sendall(message.encode())
            print(f"[INFO] Sent screenshot command: {message}")
    except Exception as e:
        print(f"[ERROR] Could not send command to screenshot app: {e}")
"""

screenshot_process = None

def start_external_app():
    global screenshot_process
    CREATE_NEW_CONSOLE = 0x00000010
    filepath = bpy.path.abspath(__file__)
    directory = os.path.dirname(filepath)
    app_path = os.path.join(directory, "extras","SS_ServerApp.exe")
    
    screenshot_process = subprocess.Popen(
        [app_path],
        stdin=subprocess.PIPE,
        
        creationflags=CREATE_NEW_CONSOLE,
        text=True
    )
    print("[INFO] Screenshot app launched and ready.")
    

def send_screenshot_command(filepath, image_format, qlty_str, onlyCaptureBlenderwindow=0, blenderWindowTitle="Blender"):
    global screenshot_process
    print("[INFO] send_screenshot_command called")
    if screenshot_process and screenshot_process.stdin and screenshot_process.poll() is None:
        print("[INFO] send_screenshot_command IF called")
        cmd = f"SS|{filepath}|{image_format}|{qlty_str}|{onlyCaptureBlenderwindow}|{blenderWindowTitle}\n"
        try:
            screenshot_process.stdin.write(cmd + '\n')
            screenshot_process.stdin.flush()
        except Exception as e:
            print(f"[ERROR] Failed to send command to screenshot process: {e}")
        print(f"[INFO] Sent command: {cmd.strip()}")
        
    else:
        print("[ERROR] Screenshot process not running.")
        
def kill_external_app():
    try:
        filepath = bpy.path.abspath(__file__)
        directory = os.path.dirname(filepath)
        app_path = os.path.join(directory, "extras","SS_ServerApp.exe")
        subprocess.call(["taskkill", "/F", "/IM", os.path.basename(app_path)])
        print(f"[INFO] Killed external screenshot app: {app_path}")
    except Exception as e:
        print(f"[ERROR] Failed to kill external screenshot app: {e}")        
        
# Thread-safe queue to manage file save paths
screenshot_queue = queue.Queue()

def delayed_screenshot(filepath):
    def screenshot_callback():
        take_screenshot(filepath)
        return None  
    bpy.app.timers.register(screenshot_callback, first_interval=0.03)

def take_screenshot_onEvents(scene, depsgraph):
    global last_depsgraph_ss_time, is_running

    if not is_running:
        return

    now = time.time()
    if now - last_depsgraph_ss_time >= screenshot_interval:
        last_depsgraph_ss_time = now
        print("[INFO] Queueing screenshot from depsgraph callback")

        # Queue the screenshot in a separate thread
        threading.Thread(target=queue_screenshot).start()

def queue_screenshot():
    global file_index, extension
    scene = bpy.context.scene
    screenshot_folder = bpy.path.abspath(scene.timelapse_screenshot_folder)

    try:
        os.makedirs(screenshot_folder, exist_ok=True)
    except PermissionError:
        print("[ERROR] Cannot create screenshot folder.")
        return

    format = scene.timelapse_image_format
    extension = 'jpg' if format == 'JPEG' else 'png'
    file_index += 1
    filepath = os.path.join(screenshot_folder, f"{file_index}.{extension}")

    # Enqueue path and register screenshot in timer (main thread)
    screenshot_queue.put(filepath)
    delayed_screenshot(filepath)

# Screenshot function
def take_screenshot(filepath):
    global is_running, onlyCaptureBlender
    if not is_running:
        return

    scene = bpy.context.scene
    format = scene.timelapse_image_format
    original_format = scene.render.image_settings.file_format
    original_quality = scene.render.image_settings.quality
 
    scene.render.image_settings.file_format = format
    if format == 'JPEG':
        scene.render.image_settings.quality = int(scene.timelapse_jpeg_quality)
        qlty_str = str(scene.timelapse_jpeg_quality)
        print(f"[INFO] JPEG quality set to: {qlty_str}")
    else:
        qlty_str = "100"    
    isIsolateBlender = scene.timelapse_isolate_blender    
    print(f"[INFO] Taking screenshot: {filepath}")
    print(f"[INFO] Isolate Blender Window: {isIsolateBlender}")
    
    onlyCaptureBlender = 1 if isIsolateBlender else 0
    blenderWindowName = get_blender_window_title()
    print(f"[INFO] Blender Window Name: {blenderWindowName}")
   
    try:
        send_screenshot_command(filepath, extension, qlty_str, onlyCaptureBlender, blenderWindowName)
    except Exception as e:
        print(f"[ERROR] Failed to send screenshot command: {e}")
    # Restore render settings
    scene.render.image_settings.file_format = original_format
    scene.render.image_settings.quality = original_quality


# UI Panel
class TimelapsePanel(bpy.types.Panel):
    bl_label = "Steps Recorder"
    bl_idname = "VIEW3D_PT_timelapse"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Steps Recorder"

    def draw(self, context):
        layout = self.layout
        global is_running

       
        box = layout.box()
        box.enabled = not is_running
        box.prop(context.scene, "timelapse_folder", text="Output Folder")
        
        box1 = layout.box()
        box1.prop(context.scene, "timelapse_interval", text="Interval (s)")
        box1.prop(context.scene, "timelapse_isolate_blender", text="Isolate Blender Window")
        if hasattr(context.scene, "timelapse_image_format"):
            box1.prop(context.scene, "timelapse_image_format", text="Image Format")

            if context.scene.timelapse_image_format == 'JPEG':
                box1.prop(context.scene, "timelapse_jpeg_quality", text="JPEG Quality")

        if is_running:
            layout.operator("timelapse.stop", text="Stop Recording", icon='EVENT_MEDIASTOP')

        else:
            layout.operator("timelapse.start", text="Start Recording", icon='PLAY').tooltip = "Start recording timelapse screenshots"
        
        layout.separator(type= 'SPACE')    
        postPro=layout.column(heading="Post Processing")
        postPro.enabled = not is_running
        
        postPro.operator("timelapse.manage_video", text="Manage Timelapse Video", icon='SEQUENCE').tooltip = "Manage the timelapse video. this will open a new workspace with the video editing template and load the screenshots as an image sequence."
        postPro.operator("timelapse.export_video", text="Export to Video", icon='FILE_MOVIE').tooltip = "Export the screenshots to a video file. this will create a new folder in the base folder and save the video in MP$ there."
        
        layout.separator(type='LINE')
        layout.label(text="Status:", icon='INFO')
        if is_running:
            layout.label(text="Recording Active", icon='RECORD_ON')
        else:
            layout.label(text="Not Recording", icon='RECORD_OFF')

class StartTimelapseOperator(bpy.types.Operator):
    bl_idname = "timelapse.start"
    bl_label = "Start Timelapse"
    
    tooltip: bpy.props.StringProperty()
    @classmethod
    def description(cls, context, operator):
        return operator.tooltip
    
    def execute(self, context):
        global is_running, screenshot_interval, depsgraph_handler_registered, file_index, extension

        if not is_running:
            base_folder = bpy.path.abspath(context.scene.timelapse_folder)
            screenshot_folder = os.path.join(base_folder, "screenshots")
            context.scene.timelapse_screenshot_folder = screenshot_folder

            try:
                os.makedirs(screenshot_folder, exist_ok=True)
                existing_files = [f for f in os.listdir(screenshot_folder)]
                existing_indices = [int(os.path.splitext(f)[0]) for f in existing_files if f.split(".")[0].isdigit()]
                if existing_indices:
                    file_index = max(existing_indices)
            except PermissionError:
                self.report({"ERROR"}, "Cannot create screenshot folder.")
                return {'CANCELLED'}
            start_external_app()
            is_running = True
            screenshot_interval = context.scene.timelapse_interval

            if not depsgraph_handler_registered:
                bpy.app.handlers.depsgraph_update_post.append(take_screenshot_onEvents)
                depsgraph_handler_registered = True

            self.report({"INFO"}, "Timelapse recording started.")
        else:
            self.report({"WARNING"}, "Timelapse already running.")

        return {'FINISHED'}

class StopTimelapseOperator(bpy.types.Operator):
    bl_idname = "timelapse.stop"
    bl_label = "Stop Timelapse"

    def execute(self, context):
        global is_running
        kill_external_app()
        is_running = False
        self.report({"INFO"}, "Timelapse stopped.")
        return {'FINISHED'}

class ExportAsVideoOperator(bpy.types.Operator):
    bl_idname = "timelapse.export_video"
    bl_label = "export ss to mp4 Video"

    tooltip: bpy.props.StringProperty()
    @classmethod
    def description(cls, context, operator):
        return operator.tooltip
    
    def execute(self, context):
        base_folder = bpy.path.abspath(context.scene.timelapse_folder)
        screenshot_folder = os.path.join(base_folder, "screenshots")
        video_folder = os.path.join(base_folder, "videos")
        context.scene.timelapse_video_folder = video_folder

        try:
            os.makedirs(video_folder, exist_ok=True)
        except PermissionError:
            self.report({"ERROR"}, "Cannot create video folder.")
            return {'CANCELLED'}

        video_file = os.path.join(video_folder, "timelapse.mp4")

        try:
            exportAsVideo(screenshot_folder, video_file)
            self.report({"INFO"}, f"Video created: {video_file}")
        except Exception as e:
            self.report({"ERROR"}, str(e))
            return {'CANCELLED'}

        return {'FINISHED'}

def exportAsVideo(tl_output_folder, video_file):
    images = sorted([f for f in os.listdir(tl_output_folder) if f.endswith(('.png', '.jpg'))])
    if not images:
        raise ValueError("No screenshots found!")

    temp_scene = bpy.data.scenes.new("TempTimelapseScene")
    first_image_path = os.path.join(tl_output_folder, images[0])
    first_image = bpy.data.images.load(first_image_path)

    width, height = first_image.size
    if width % 2: width += 1
    if height % 2: height += 1
    bpy.data.images.remove(first_image)

    temp_scene.render.resolution_x = width
    temp_scene.render.resolution_y = height
    temp_scene.render.image_settings.file_format = 'FFMPEG'
    temp_scene.render.ffmpeg.format = 'MPEG4'
    temp_scene.render.ffmpeg.codec = 'H264'
    temp_scene.render.filepath = bpy.path.abspath(video_file)

    seq_editor = temp_scene.sequence_editor_create()
    strip = seq_editor.sequences.new_image(
        name="Timelapse",
        filepath=os.path.join(tl_output_folder, images[0]),
        channel=1,
        frame_start=1
    )

    for img in images[1:]:
        strip.elements.append(img)

    temp_scene.frame_start = 1
    temp_scene.frame_end = len(images)

    bpy.ops.render.render(animation=True, scene=temp_scene.name)
    bpy.data.scenes.remove(temp_scene)

def ShowMessageBox(message = "", title = "Message Box", icon = 'INFO'):

    def draw(self, context):
        self.layout.label(text=message)

    bpy.context.window_manager.popup_menu(draw, title = title, icon = icon)

class ManageTimelapseOperator(bpy.types.Operator):
    bl_idname = "timelapse.manage_video"
    bl_label = "Manage Timelapse Video"

    tooltip: bpy.props.StringProperty()
    
    @classmethod
    def description(cls, context, operator):
        return operator.tooltip
    
    def execute(self, context):
        scene = context.scene

        # Save the current file
        bpy.ops.wm.save_mainfile()

        #check if the timplapse video edting file already is saved
        original_path = bpy.data.filepath
        base, ext = os.path.splitext(original_path)
        new_path = base + "_timelapse.blend"
        existing_files = [f for f in os.listdir(os.path.dirname(original_path))]
        print(f"[INFO] Existing files: {existing_files}")
        print(f"[INFO] New file path: {new_path}")
        if os.path.basename(new_path) in existing_files:
            print("[INFO] File all ready exist")
            ShowMessageBox("Process aborted! File all ready exist: "+ new_path, "File all ready exist", icon='ERROR')
            
            return {'CANCELLED'}
        else:   
        
            # clean all objects and data in the current scene
            bpy.ops.object.select_all(action='SELECT')
            bpy.ops.object.delete()
            
            bpy.ops.outliner.orphans_purge()
            
            # Append the "Video Editing" workspace and delete all others
            filepath = bpy.path.abspath(__file__)
            directory = os.path.dirname(filepath)
            template_path = os.path.join(directory, "video editing template","video editing template.blend")
            print(f"[INFO] Appending workspace from")
            print(f"[INFO] Appending workspace from: {template_path}")
            bpy.ops.workspace.append_activate(idname="Video Editing", filepath=template_path)
            

            # Delete all other workspaces        
            workspaces = [ws for ws in bpy.data.workspaces if ws != context.workspace and ws.name != "Video Editing"]
            
            print(f"[INFO] Deleting workspaces: {workspaces}")
            bpy.data.batch_remove(ids=workspaces)        
            bpy.data.workspaces.get("Layout").rename("Preview")
            
            for workspace in bpy.data.workspaces:
                if workspace.name == "Preview":
                    for screen in workspace.screens:
                        for area in screen.areas:
                            if area.type == 'VIEW_3D':
                                area.type = 'SEQUENCE_EDITOR'
                                for region in area.regions:
                                    if region.type == 'WINDOW':
                                        space = area.spaces.active
                                        space.view_type = 'PREVIEW'  # Shows preview of video
                                        space.display_mode = 'IMAGE'  # Ensures preview displays image (or movie)
                                print("[INFO] Replaced 3D View with Sequencer in Preview mode in Layout workspace.")
                                break
                
            # Load screenshots as image sequence
            screenshot_folder = bpy.path.abspath(scene.timelapse_screenshot_folder)
            images = sorted(
                [f for f in os.listdir(screenshot_folder) if f.endswith(('.png', '.jpg'))],
                key=numeric_sort_key
            )

            if not images:
                self.report({"ERROR"}, "No screenshots found.")
                return {'CANCELLED'}

            filepath = os.path.join(screenshot_folder, images[0])
            strip = context.scene.sequence_editor.sequences.new_image(
                name="TimelapseSeq",
                filepath=filepath,
                channel=1,
                frame_start=1
            )

            for img in images[1:]:
                strip.elements.append(img)

            context.scene.frame_start = 1
            context.scene.frame_end = len(images)

            self.report({"INFO"}, "Video Editing setup completed.")
            
            # Save As a new .blend file and open it
            
            bpy.ops.wm.save_as_mainfile(filepath=new_path, copy=True)
            self.report({"INFO"}, f"Saved as: {new_path}")

            # Open the newly saved file
            bpy.ops.wm.open_mainfile(filepath=new_path)
            
            
            return {'FINISHED'}

# Register
def register():
    
    bpy.utils.register_class(TimelapsePanel)
    bpy.utils.register_class(StartTimelapseOperator)
    bpy.utils.register_class(StopTimelapseOperator)
    bpy.utils.register_class(ExportAsVideoOperator)
    bpy.types.Scene.timelapse_screenshot_folder = bpy.props.StringProperty()
    bpy.types.Scene.timelapse_video_folder = bpy.props.StringProperty()
    
    

def unregister():
    bpy.utils.unregister_class(TimelapsePanel)
    bpy.utils.unregister_class(StartTimelapseOperator)
    bpy.utils.unregister_class(StopTimelapseOperator)
    bpy.utils.unregister_class(ExportAsVideoOperator)
    del bpy.types.Scene.timelapse_folder
    del bpy.types.Scene.timelapse_screenshot_folder
    del bpy.types.Scene.timelapse_video_folder
    del bpy.types.Scene.timelapse_interval
    del bpy.types.Scene.timelapse_image_format
    del bpy.types.Scene.timelapse_jpeg_quality

if __name__ == "__main__":
    register()