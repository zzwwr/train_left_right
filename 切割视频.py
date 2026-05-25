import cv2
import os

video_path = "./train.mp4"
save_folder = "./video_frames"
step = 3  # 每隔5帧保存1帧

if not os.path.exists(save_folder):
    os.makedirs(save_folder)

cap = cv2.VideoCapture(video_path)
frame_count = 1
save_count = 1

while True:
    ret, frame = cap.read()
    if not ret:
        break

    if frame_count % step == 0:
        save_path = os.path.join(save_folder, f"{save_count}.jpg")
        cv2.imwrite(save_path, frame)
        print(f"保存：{save_count}.jpg")
        save_count += 1

    frame_count += 1

cap.release()
print(f"✅ 完成！保存 {save_count-1} 帧")