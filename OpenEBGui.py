import customtkinter as ctk
from tkinter import filedialog
import subprocess
import threading
import datetime

class OpenEBGui(ctk.CTk):
    def __init__(self):
        super().__init__()

    # Fenster-Einstellungen
        self.title("OpenEB Control Center")
        self.geometry("800x600")
        ctk.set_appearance_mode("dark")

        # Layout-Raster
        self.grid_columnconfigure(0, weight=1)
        
        # Titel
        self.label = ctk.CTkLabel(self, text="OpenEB Player & Recorder", font=("Arial", 20, "bold"))
        # self.grid(row=0, column=0, padx=20, pady=20)

        # --- SEKTION 1: LIVE KAMERA ---
        self.live_btn = ctk.CTkButton(self, text="Live Kamera starten", fg_color="green", hover_color="darkgreen", command=self.start_live)
        self.live_btn.grid(row=1, column=0, padx=20, pady=20)

        # --- SEKTION 2: LIVE KAMERA ---
        self.live_btn = ctk.CTkButton(self, text="Datei aufnehmen", fg_color="red", hover_color="darkred", command=self.start_recording)
        self.live_btn.grid(row=2, column=0, padx=20, pady=20)

        # --- SEKTION 3: DATEI ABSPIELEN ---
        self.play_btn = ctk.CTkButton(self, text="Datei auswählen & abspielen", command=self.play_file)
        self.play_btn.grid(row=3, column=0, padx=20, pady=20)

        # --- SEKTION 4: STATUS / LOG ---
        self.status_log = ctk.CTkTextbox(self, height=100)
        self.status_log.grid(row=4, column=0, padx=20, pady=20, sticky="nsew")
        self.status_log.insert("0.0", "Bereit...\n")

    def log(self, text):
        self.status_log.insert("end", f"> {text}\n")
        self.status_log.see("end")

    def run_command(self, cmd):
        # Startet den Prozess in einem eigenen Thread, damit die GUI nicht einfriert
        def thread_run():
            try:
                self.log(f"Starte: {' '.join(cmd)}")
                # Hier musst du ggf. den Pfad zu deinen OpenEB-Tools anpassen
                subprocess.run(cmd, check=True)
            except Exception as e:
                self.log(f"Fehler: {e}")

        threading.Thread(target=thread_run, daemon=True).start()

    def start_live(self):
        # Beispielbefehl für Live-View (metavision_viewer ist ein Standard-Tool von OpenEB)
        self.run_command(["metavision_viewer"])

    def start_recording(self):
        file_path = filedialog.asksaveasfilename(initialfile=datetime.datetime.now().strftime("%Y-%m-%d %H%M%S"), filetypes=[("Event File", ".raw")])
        if not file_path.endswith(('.raw')):
            file_path += '.raw'
        print(file_path)
        if file_path:
            # Spielt die gewählte Datei ab
            self.run_command(["metavision_viewer", "-o", file_path])


    def play_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Event Files", "*.raw *.dat *.hdf5")])
        if file_path:
            # Spielt die gewählte Datei ab
            self.run_command(["metavision_viewer", "-i", file_path])

if __name__ == "__main__":
    app = OpenEBGui()
    app.mainloop()

    