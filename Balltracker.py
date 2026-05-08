from ultralytics import YOLO
import cv2
import pandas as pd
import torch


class BallTracker:

    def __init__(self,model_path):
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.model = YOLO(model_path)
        self.model.to(self.device)

    def interpolate_ball_positions(self, ball_positions):
        ball_positions = [x.get(1,[]) for x in ball_positions]
        # convert the list into pandas dataframe
        df_ball_positions = pd.DataFrame(ball_positions,columns=['x1','y1','x2','y2'])

        # interpolate the missing values
        df_ball_positions = df_ball_positions.interpolate()
        df_ball_positions = df_ball_positions.bfill()

        ball_positions = [{1:x} for x in df_ball_positions.to_numpy().tolist()]

        return ball_positions

    def detect_frames(self, frames):
        ball_detections = []

        for frame in frames:
            player_dict = self.detect_frame(frame)
            ball_detections.append(player_dict)
        
        return ball_detections

    def detect_frame(self,frame):
        # YOLO erwartet 3 Kanäle (BGR). Event-Kamera-Frames in Gray haben nur 1 Kanal.
        if len(frame.shape) == 2:
            img_for_prediction = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        else:
            img_for_prediction = frame

        # Optimierungen: 
        # - imgsz=320 (kleiner ist schneller, reicht für Bälle oft aus)
        # - half=True (FP16 Inferenz, fast doppelt so schnell auf GPUs)
        results = self.model.predict(
            img_for_prediction, 
            classes=[32], conf=0.15, verbose=False, 
            imgsz=320, half=(self.device == 'cuda')
        )[0]

        ball_dict = {}
        for box in results.boxes:
            # Die Klassen-ID des Objekts abrufen
            class_id = int(box.cls[0])
            # Prüfen, ob der Name der Klasse "sports ball" ist
            if self.model.names[class_id] == 'sports ball':
                result = box.xyxy.tolist()[0]
                ball_dict[1] = result
                break # Wir nehmen nur den ersten (besten) Ball für die Interpolation
        
        return ball_dict

    def draw_bboxes(self,video_frames, player_detections):
        output_video_frames = []
        for frame, ball_dict in zip(video_frames, player_detections):
            # Draw Bounding Boxes
            frame = self.draw_bbox(frame, ball_dict)
            output_video_frames.append(frame)
        
        return output_video_frames
    
    def draw_bbox(self,frame, ball_dict):
        # Sicherstellen, dass das Frame BGR ist, damit farbige Boxen gezeichnet werden können
        if len(frame.shape) == 2:
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)

        # Draw Bounding Boxes
        for track_id, bbox in ball_dict.items():
            x1, y1, x2, y2 = bbox
            cv2.putText(frame, f"Ball ID: {track_id}",(int(bbox[0]),int(bbox[1] -10 )),cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)
            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 255), 2)
        
        return frame