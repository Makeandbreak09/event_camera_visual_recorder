import tkinter as tk
from tkinter import messagebox
import threading
import time
from metavision_hal import DeviceDiscovery

class RecorderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Metavision Recorder")
        self.root.geometry("300x200")

        self.device = None
        self.is_recording = False
        self.recording_thread = None

        # UI Elemente
        self.label = tk.Label(root, text="Metavision SDK Aufnahme", font=("Arial", 12))
        self.label.pack(pady=20)

        self.btn_toggle = tk.Button(
            root, 
            text="Aufnahme Starten", 
            command=self.toggle_recording,
            bg="green", 
            fg="white",
            font=("Arial", 10, "bold"),
            width=20,
            height=2
        )
        self.btn_toggle.pack(pady=10)

        self.status_label = tk.Label(root, text="Status: Bereit", fg="blue")
        self.status_label.pack(pady=5)

        # Kamera beim Start initialisieren
        self.init_camera()

    def init_camera(self):
        try:
            self.device = DeviceDiscovery.open("")
            if not self.device:
                raise Exception("Keine Kamera gefunden.")
            print("Kamera verbunden.")
        except Exception as e:
            messagebox.showerror("Fehler", f"Kamera-Initialisierung fehlgeschlagen: {e}")
            self.root.destroy()

    def toggle_recording(self):
        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_recording()

    def start_recording(self):
        self.is_recording = True
        self.btn_toggle.config(text="Aufnahme Stoppen", bg="red")
        self.status_label.config(text="Status: Nimmt auf...", fg="red")
        
        # Generiere Dateiname mit Zeitstempel
        filename = f"recording_{int(time.time())}.raw"
        
        # Aufnahme in separatem Thread starten, um GUI nicht einzufrieren
        i_events_stream = self.device.get_i_events_stream()
        i_events_stream.log_raw_data(filename)
        print(f"Aufnahme gestartet: {filename}")

    def stop_recording(self):
        self.is_recording = False
        i_events_stream = self.device.get_i_events_stream()
        i_events_stream.stop_log_raw_data()
        
        self.btn_toggle.config(text="Aufnahme Starten", bg="green")
        self.status_label.config(text="Status: Gespeichert", fg="blue")
        print("Aufnahme gestoppt.")

    def on_closing(self):
        if self.is_recording:
            self.stop_recording()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = RecorderApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()