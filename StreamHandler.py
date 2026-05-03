from metavision_sdk_core import PeriodicFrameGenerationAlgorithm, ColorPalette
from metavision_sdk_stream import Camera, CameraStreamSlicer, SliceCondition, RAWEvt2EventFileWriter
import threading
import os

class StreamHandler:
    def __init__(self, source_path=None, fps=60, color_palette=ColorPalette.Gray, on_frame_cb=None, on_thrad_stop_cb=None):
        self.fps = fps
        self.color_palette = color_palette
        self.on_frame_cb = on_frame_cb # Callback für das U
        self.on_thread_stop_cb = on_thrad_stop_cb
        self.is_running = True
        self.is_recording = False
        
        # Kamera oder Datei laden
        try:
            if source_path is None:
                self.camera = Camera.from_first_available()
                # self.camera = Camera.from_file("./80_balls.raw")
            else:
                self.camera = Camera.from_file(source_path)
        except Exception as e:
            raise Exception(f"Fehler beim Initialisieren: {e}")

        self.width = self.camera.width()
        self.height = self.camera.height()

        # Slicer & Generator
        # Slicer auf die exakte Frame-Dauer in Mikrosekunden einstellen
        self.slicer = CameraStreamSlicer(self.camera.move(), SliceCondition.make_n_us((int)(10000000/self.fps)))
        self.frame_gen = PeriodicFrameGenerationAlgorithm(
            sensor_width=self.width, sensor_height=self.height, 
            fps=self.fps, palette=self.color_palette
        )
        
        # Falls die Bilder direkt verarbeitet werden sollen:
        if self.on_frame_cb:
            self.frame_gen.set_output_callback(self.on_frame_cb)

        # Thread starten
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()

    def _worker(self):
        try:
            for slice in self.slicer:
                if not self.is_running:
                    break
                events = slice.events
                self.frame_gen.process_events(events)
                
                # HIER werden die Daten physisch geschrieben
                if self.is_recording and self.writer is not None:
                    try:
                        self.writer.add_cd_events(events)
                    except Exception as e:
                        print(f"Fehler beim Schreiben: {e}")
        except Exception as e:
            print(f"StreamHandler Error: {e}")
        print(f"[Camera stopped running]")
        if(self.on_thread_stop_cb):
            self.on_thread_stop_cb()

    def set_on_frame_cb(self, on_frame_cb):
        self.on_frame_cb = on_frame_cb
        self.frame_gen.set_output_callback(on_frame_cb)

    def stop(self):
        self.is_running = False
        if self.thread.is_alive():
            self.thread.join(timeout=1.0)

    def set_palette(self, palette):
        self.color_palette = palette
        self.frame_gen.set_color_palette(palette)

    def start_recording(self, save_path, base_name):
        """Startet oder stoppt die RAW-Aufnahme."""
        counter = 0
        file_path = os.path.join(save_path, f"{base_name}_{counter}.raw")
        while os.path.exists(file_path):
            counter += 1
            file_path = os.path.join(save_path, f"{base_name}_{counter}.raw")

        self.writer = RAWEvt2EventFileWriter(self.width, self.height, file_path)
        self.writer.open(path=file_path)
        self.is_recording = True

        print(f"Aufnahme gestartet: {file_path}")   

    def stop_recording(self):
        self.is_recording = False
        self.writer.close()
        self.writer = None

        print("Aufnahme gestoppt.")
