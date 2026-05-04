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
        self.is_recording = False
        self.active = True
        
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
        self.slicer = CameraStreamSlicer(self.camera.move(), SliceCondition.make_n_us((int)(1000000/10/self.fps)))
        self.frame_gen = PeriodicFrameGenerationAlgorithm(
            sensor_width=self.width, sensor_height=self.height, 
            fps=self.fps, palette=self.color_palette
        )
        
        # Internen Wrapper-Callback registrieren
        self.frame_gen.set_output_callback(self._internal_on_frame_cb)

        self.start_thread()

    def start_thread(self):
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()


    def _worker(self):
        self.active = True
        try:
            for slice in self.slicer:
                # print(f"Camera: {self.slicer.camera()}, Slice.Timestamp: {slice.t}, Slice.Event_NR: {slice.n_events}")

                # Falls die Kamera nicht aktiv ist, überspringen wir die teure Verarbeitung
                if not self.active:
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

        # Falls noch eine Aufnahme läuft, diese sauber beenden
        if self.is_recording:
            self.stop_recording()
        self.active = False

        if(self.on_thread_stop_cb):
            self.on_thread_stop_cb()

    def _internal_on_frame_cb(self, ts, frame):
        """Sicherer Wrapper, der prüft, ob ein Callback existiert."""
        if self.on_frame_cb is not None:
            self.on_frame_cb(ts, frame)

    def set_on_frame_cb(self, on_frame_cb):
        self.on_frame_cb = on_frame_cb

    def stop(self):
        # Falls noch eine Aufnahme läuft, diese sauber beenden
        if self.is_recording:
            self.stop_recording()

        self.active = False
            
        if self.thread.is_alive():
            self.thread.join(timeout=1.0)
        self.slicer = None # Gibt die Kamera-Ressource/Datei frei

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
