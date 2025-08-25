"""
AI Hand Tracking System
Real-time hand gesture recognition using MediaPipe and OpenCV
Author: Albert Baiden-Amissah
"""

import cv2
import mediapipe as mp
import numpy as np
import time
import math
import base64
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import socketserver

class HandTracker:
    def __init__(self, mode=False, max_hands=2, detection_confidence=0.5, track_confidence=0.5):
        self.mode = mode
        self.max_hands = max_hands
        self.detection_confidence = detection_confidence
        self.track_confidence = track_confidence

        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=self.mode,
            max_num_hands=self.max_hands,
            min_detection_confidence=self.detection_confidence,
            min_tracking_confidence=self.track_confidence
        )
        self.mp_draw = mp.solutions.drawing_utils

    def find_hands(self, img, draw=True):
        """Detect hands in the image"""
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.results = self.hands.process(img_rgb)

        if self.results.multi_hand_landmarks:
            for hand_landmarks in self.results.multi_hand_landmarks:
                if draw:
                    self.mp_draw.draw_landmarks(
                        img, hand_landmarks, self.mp_hands.HAND_CONNECTIONS
                    )
        return img

    def find_position(self, img, hand_number=0, draw=True):
        """Get landmark positions for a specific hand"""
        lm_list = []
        if self.results.multi_hand_landmarks:
            if hand_number < len(self.results.multi_hand_landmarks):
                hand = self.results.multi_hand_landmarks[hand_number]
                
                for id, lm in enumerate(hand.landmark):
                    h, w, c = img.shape
                    cx, cy = int(lm.x * w), int(lm.y * h)
                    lm_list.append([id, cx, cy])
                    
                    if draw and id in [4, 8, 12, 16, 20]:  # Fingertips
                        cv2.circle(img, (cx, cy), 10, (255, 0, 255), cv2.FILLED)
        
        return lm_list

    def fingers_up(self, lm_list):
        """Detect which fingers are up"""
        if len(lm_list) == 0:
            return []
            
        fingers = []
        tip_ids = [4, 8, 12, 16, 20]
        
        # Thumb
        if lm_list[tip_ids[0]][1] > lm_list[tip_ids[0] - 1][1]:
            fingers.append(1)
        else:
            fingers.append(0)
            
        # Other fingers
        for id in range(1, 5):
            if lm_list[tip_ids[id]][2] < lm_list[tip_ids[id] - 2][2]:
                fingers.append(1)
            else:
                fingers.append(0)
                
        return fingers

    def get_distance(self, p1, p2, img, draw=True):
        """Calculate distance between two landmarks"""
        x1, y1 = p1[1], p1[2]
        x2, y2 = p2[1], p2[2]
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        
        if draw:
            cv2.line(img, (x1, y1), (x2, y2), (255, 0, 255), 3)
            cv2.circle(img, (x1, y1), 15, (255, 0, 255), cv2.FILLED)
            cv2.circle(img, (x2, y2), 15, (255, 0, 255), cv2.FILLED)
            cv2.circle(img, (cx, cy), 15, (0, 0, 255), cv2.FILLED)
            
        length = math.hypot(x2 - x1, y2 - y1)
        return length, img, [x1, y1, x2, y2, cx, cy]

def main():
    """Main function to run hand tracking demo"""
    # Initialize camera
    cap = cv2.VideoCapture(0)
    
    # Check if camera opened successfully
    if not cap.isOpened():
        print("Error: Could not open camera")
        return
    
    cap.set(3, 1280)  # Width
    cap.set(4, 720)   # Height
    
    # Initialize hand tracker
    detector = HandTracker()
    
    # Variables for FPS calculation
    prev_time = 0
    
    print("Hand Tracking System Started!")
    print("Camera window should appear shortly...")
    print("Press 'q' to quit")
    print("Gestures detected:")
    print("- Open hand: All fingers up")
    print("- Fist: No fingers up")
    print("- Peace: Index and middle finger up")
    print("- Thumbs up: Only thumb up")
    
    # Create named window and set properties
    cv2.namedWindow("AI Hand Tracking - Albert Baiden-Amissah", cv2.WINDOW_AUTOSIZE)
    
    while True:
        success, img = cap.read()
        if not success:
            break
            
        # Flip image horizontally for mirror effect
        img = cv2.flip(img, 1)
        
        # Find hands
        img = detector.find_hands(img)
        lm_list = detector.find_position(img, draw=False)
        
        if len(lm_list) != 0:
            # Get finger status
            fingers = detector.fingers_up(lm_list)
            total_fingers = fingers.count(1)
            
            # Gesture recognition
            gesture = "Unknown"
            if total_fingers == 0:
                gesture = "Fist"
            elif total_fingers == 5:
                gesture = "Open Hand"
            elif total_fingers == 1 and fingers[0] == 1:
                gesture = "Thumbs Up"
            elif total_fingers == 2 and fingers[1] == 1 and fingers[2] == 1:
                gesture = "Peace Sign"
            elif total_fingers == 3 and fingers[1] == 1 and fingers[2] == 1 and fingers[3] == 1:
                gesture = "Three Fingers"
            elif total_fingers == 1 and fingers[1] == 1:
                gesture = "Pointing"
            
            # Display gesture info
            cv2.putText(img, f'Gesture: {gesture}', (50, 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(img, f'Fingers: {total_fingers}', (50, 100), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            # Distance measurement between thumb and index finger
            if len(lm_list) >= 9:
                length, img, line_info = detector.get_distance(lm_list[4], lm_list[8], img)
                cv2.putText(img, f'Distance: {int(length)}px', (50, 150), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        # Calculate and display FPS
        current_time = time.time()
        fps = 1 / (current_time - prev_time)
        prev_time = current_time
        cv2.putText(img, f'FPS: {int(fps)}', (50, 200), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
        
        # Display landmarks count
        cv2.putText(img, f'Landmarks: {len(lm_list)}', (50, 250), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
        
        # Show the image
        cv2.imshow("AI Hand Tracking - Albert Baiden-Amissah", img)
        
        # Move window to front (Windows specific)
        cv2.setWindowProperty("AI Hand Tracking - Albert Baiden-Amissah", cv2.WND_PROP_TOPMOST, 1)
        cv2.setWindowProperty("AI Hand Tracking - Albert Baiden-Amissah", cv2.WND_PROP_TOPMOST, 0)
        
        # Break loop on 'q' key press
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    # Clean up
    cap.release()
    cv2.destroyAllWindows()
    print("Hand tracking system stopped.")

if __name__ == "__main__":
    # Check if required libraries are installed
    try:
        import cv2
        import mediapipe as mp
        print("All required libraries found!")
        main()
    except ImportError as e:
        print(f"Missing required library: {e}")
        print("Please install with: pip install opencv-python mediapipe numpy")
