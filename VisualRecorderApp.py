import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import numpy as np
import threading
import os
import queue
import time
from StreamHandler import StreamHandler
from metavision_sdk_core import ColorPalette


class VisualRecorderApp:

    def __init__(self, root):
        self.root = root
        root.title("Metavision Kamera & Recorder")
        # Ziel-Anzeige-FPS, passend zur Standard-Generierungs-FPS des StreamHandlers (standardmäßig 60)
        self.frame_rate = 30 

        self.init_menu_bar()

        self.init_main_frame()

        self.live_stream_handler = None
        self.file_stream_handler = None

        self.init_online_view()
        self.canvas_image_id = None
        

    def init_menu_bar(self):
        # Haupt-Menüleiste erstellen
        menubar = tk.Menu(root)

        # Untermenü für "Datei" erstellen
        # tearoff=0 verhindert, dass man das Menü "abreißen" kann (sieht moderner aus)
        file_menu = tk.Menu(menubar, tearoff=0)
        # Befehle zum Menü hinzufügen
        file_menu.add_command(label="Kamera", command=lambda: self.init_online_view())
        file_menu.add_command(label="Öffnen", command=lambda: self.init_offline_view())
        file_menu.add_separator() # Eine Trennlinie einfügen
        file_menu.add_command(label="Beenden", command=self.root.destroy)
        # Das "Datei"-Menü zur Haupt-Menüleiste hinzufügen
        menubar.add_cascade(label="Datei", menu=file_menu)  

        # Untermenü für "Ansicht" erstellen
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="Light", command=lambda: self.update_color_palette(ColorPalette.Light))
        view_menu.add_command(label="Dark", command=lambda: self.update_color_palette(ColorPalette.Dark))
        view_menu.add_command(label="CoolWarm", command=lambda: self.update_color_palette(ColorPalette.CoolWarm))
        view_menu.add_command(label="Gray", command=lambda: self.update_color_palette(ColorPalette.Gray))
        menubar.add_cascade(label="Ansicht", menu=view_menu)
        self.color_palette = ColorPalette.Gray

        # Untermenü für "Hilfe" erstellen
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Info", command=lambda: messagebox.showinfo("Info", "Dies ist eine Tkinter-App"))
        menubar.add_cascade(label="Hilfe", menu=help_menu)

        # Die Menüleiste dem Fenster zuweisen
        root.config(menu=menubar)

    def init_main_frame(self):
        # Hier den Frame erstellen, der den gesamten Inhalt hält
        self.main_frame = tk.Frame(root, width=400, height=300)
        self.main_frame.pack(fill="both", expand=True)
        self.root.bind("<space>", lambda event: self.toggle_recording() if self.is_live else None)
        
        # Ein kleinerer Puffer (z.B. 1 Sekunde) verringert die Verzögerung und den Speicherverbrauch.
        self.frame_queue = queue.Queue(maxsize=2) 
        self.file_counter = 1
        self.is_recording = False
        self.is_live = False
        self.save_path = "."
        
        self.all_slicers = []
        self.all_frame_generators = []
        self.current_slicer = None
        self.current_frame_generator = None
        self.canvas_image_id = None

        # CANVAS THREAD STARTEN
        self.canvas_thread = threading.Thread(target=self._poll_frame_queue, daemon=True)
        # self.canvas_thread.start()
        self.time = time.time()
        self._poll_frame_queue()

    def clear_view(self):
        with self.frame_queue.mutex:
            self.frame_queue.queue.clear()
        self.canvas_image_id = None

        for widget in self.main_frame.winfo_children():
            widget.destroy()

    def init_live_camera(self):
        if self.live_stream_handler is not None:
            return

        try:
            self.live_stream_handler = StreamHandler(fps=self.frame_rate, color_palette=self.color_palette)
        except Exception as e:
            self.live_stream_handler = None
            print(e)

        if self.live_stream_handler is None:
            self.root.after(5000, self.init_live_camera)

    def init_online_view(self):
        self.init_live_camera()

        if self.live_stream_handler is None:
            return
    
        if self.file_stream_handler is not None:
            self.file_stream_handler.set_on_frame_cb(None)
            self.file_stream_handler.active = False
            self.file_stream_handler.stop()
            self.file_stream_handler = None

        if self.live_stream_handler is not None:
            self.live_stream_handler.active = True

        self.clear_view()

        self.live_stream_handler.set_on_frame_cb(self.update_canvas)

        # Frame
        self.is_live = True
        
        # Label zur Anzeige des Pfads (optional)
        self.lbl_path = tk.Label(self.main_frame, text=f"Speichern in: {os.path.abspath(self.save_path)}", fg="gray")
        self.lbl_path.pack(side=tk.TOP)

        # UI Setup
        # if self.current_slicer is not None:
        #     width, height = self.current_slicer.camera.width(), self.current_slicer.camera.height()
        # else:
        #     width, height = 400, 400
        self.canvas = tk.Canvas(self.main_frame, width=self.live_stream_handler.width, height=self.live_stream_handler.height, bg="black")
        self.canvas.pack()
        
        # UI: Frame für die Buttons (nebeneinander)
        self.button_frame = tk.Frame(self.main_frame)
        self.button_frame.pack(pady=10)

        # Record Button
        self.btn_record = tk.Button(self.button_frame, text="Aufnahme Starten", command=self.toggle_recording, bg="green", fg="white")
        self.btn_record.pack(pady=10)

        # Ordner-Button
        self.btn_dir = tk.Button(self.button_frame, text="Ordner wählen", command=self.select_directory)
        self.btn_dir.pack(side=tk.LEFT, padx=5)

        # 1. Label und Eingabefeld für den Dateinamen
        tk.Label(self.button_frame, text="Dateinamen-Basis:").pack(pady=(10, 0))
        self.entry_filename = tk.Entry(self.button_frame)
        self.entry_filename.insert(0, "aufnahme")  # Standardwert
        self.entry_filename.pack(pady=5)

    def init_offline_view(self):
        selected_file = self.select_file()
        if not selected_file: # Falls der User nicht abgebrochen hat
            print(f"Keine Datei ausgewählt")
            return
        else:
            if self.file_stream_handler is not None:
                self.file_stream_handler.set_on_frame_cb(None)
                self.file_stream_handler.active = False

            self.file_stream_handler = StreamHandler(source_path=selected_file, fps=self.frame_rate, color_palette=self.color_palette)

        if self.file_stream_handler is None:
            return
        
        if self.live_stream_handler is not None:
            self.live_stream_handler.set_on_frame_cb(None)
            self.live_stream_handler.active = False
            if self.live_stream_handler.is_recording:
                self.live_stream_handler.stop_recording()
            self.live_stream_handler.stop()
            self.live_stream_handler = None
        
        self.clear_view()

        self.file_stream_handler.set_on_frame_cb(self.update_canvas)


        # Frame Generator (wandelt Events in Bilder um)
        self.is_live = False

        # Label zur Anzeige des Pfads (optional)
        self.lbl_path = tk.Label(self.main_frame, text=f"Spielt ab: {os.path.abspath(selected_file)}", fg="gray")
        self.lbl_path.pack()

        # UI Setup
        # if self.current_slicer is not None:
        #     width, height = self.current_slicer.camera.width(), self.current_slicer.camera.height()
        # else:
        #     width, height = 400, 400
        self.canvas = tk.Canvas(self.main_frame, width=self.file_stream_handler.width, height=self.file_stream_handler.height, bg="black")
        self.canvas.pack()

    def on_slicer_done(self):
        self.active = False
        print("Wiedergabe beendet!")
        # Hier kannst du deine GUI-Elemente zurücksetzen
        self.init_online_view()
    
    def update_color_palette(self, color_palette):
        self.color_palette = color_palette
        if self.live_stream_handler:
            self.live_stream_handler.set_palette(color_palette)
        if self.file_stream_handler:
            self.file_stream_handler.set_palette(color_palette)

    def update_canvas(self, ts, frame):
        try:
            # Konvertierung zum PIL Image im Hintergrund-Thread erledigen
            img = Image.fromarray(frame.copy())
            # .put() blockiert den StreamHandler-Thread, wenn die Queue voll ist.
            # Dadurch wird die Einlesegeschwindigkeit der Datei an die Anzeige-Rate gekoppelt.
            self.frame_queue.put(img)
        except queue.Full:
            pass

    def _poll_frame_queue(self):
        """Läuft im Main-Thread via root.after – zieht Frames aus der Queue."""
        try:
            # print(f"Items in Queue: {self.frame_queue.qsize()}")
            img = self.frame_queue.get_nowait()
            # PhotoImage muss im Main-Thread bleiben
            self.photo = ImageTk.PhotoImage(image=img)
            
            # Performance-Boost: Falls das Bild-Objekt existiert, nur Inhalt tauschen
            if self.canvas_image_id is None:
                self.canvas_image_id = self.canvas.create_image(0, 0, image=self.photo, anchor=tk.NW)
            else:
                self.canvas.itemconfig(self.canvas_image_id, image=self.photo)
        except queue.Empty:
            # print("Queue ist leer")
            pass
        
        self.root.after((int)(1000/10/self.frame_rate), self._poll_frame_queue)

    def select_directory(self):
        """Öffnet einen Dialog zur Ordnerwahl."""
        selected_dir = filedialog.askdirectory(initialdir=self.save_path, title="Speicherort wählen")
        if selected_dir: # Falls der User nicht abgebrochen hat
            self.save_path = selected_dir
            self.lbl_path.config(text=f"Speichern in: {selected_dir}")
            print(f"Neuer Speicherort: {selected_dir}")
    
        
    def select_file(self):
        return filedialog.askopenfilename(title="Datei öffnen", initialdir="./", filetypes=[("Event Files", "*.raw *.hdf5 *.dat")])

    
    def toggle_recording(self):
        """Startet oder stoppt die RAW-Aufnahme."""
        # Holen der Basis vom Eingabefeld
        if not self.live_stream_handler.is_recording:
            base_name = self.entry_filename.get()
            if not base_name: 
                base_name = "recording" # Fallback, falls Feld leer
            self.live_stream_handler.start_recording(self.save_path, base_name)
            self.btn_record.config(text="Aufnahme Stoppen", bg="red")
        else:
            self.live_stream_handler.stop_recording()
            self.btn_record.config(text="Aufnahme Starten", bg="green")
            

    
    def on_closing(self):
        """Stoppt die Hardware-Ressourcen sauber."""
        if self.live_stream_handler:
            self.live_stream_handler.stop()
        if self.file_stream_handler:
            self.file_stream_handler.stop()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = VisualRecorderApp(root)
    # Protokoll hinzufügen, damit on_closing aufgerufen wird, wenn das 'X' geklickt wird
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()