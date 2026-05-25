import cv2
import time
import threading

class RTSPCapture:
    def __init__(self, source, reconnect_interval=2):
        self.source = source
        self.reconnect_interval = reconnect_interval
        self.cap = None
        self.frame = None
        self.running = True
        self.lock = threading.Lock()

        self.fps = 30
        self.is_local_video = False

        thread = threading.Thread(target=self._update_frame, daemon=True)
        thread.start()

    def _update_frame(self):
        while self.running:
            try:
                if self.cap is None or not self.cap.isOpened():
                    print("[INFO] 正在打开视频源...")
                    self.cap = cv2.VideoCapture(self.source)

                    if str(self.source).startswith("rtsp://"):
                        # 这里我帮你保留了，不报错、能走TCP
                        if hasattr(cv2, 'CAP_PROP_FFMPEG_OPTIONS'):
                            self.cap.set(cv2.CAP_PROP_FFMPEG_OPTIONS, "rtsp_transport=tcp")
                        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                        self.is_local_video = False
                    else:
                        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
                        self.is_local_video = True
                        if self.fps <= 0:
                            self.fps = 30

                ret, frame = self.cap.read()
                if ret:
                    with self.lock:
                        self.frame = frame.copy()

                    # 👇 这里注释掉，就不卡了
                    # if self.is_local_video:
                    #     time.sleep(1.0 / self.fps)

                else:
                    if self.is_local_video:
                        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    else:
                        print("[WARN] 读帧失败，重连中...")
                        self._release()
                        time.sleep(self.reconnect_interval)

            except Exception as e:
                print(f"[ERROR] 读取异常: {e}")
                self._release()
                time.sleep(self.reconnect_interval)

    def _release(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        with self.lock:
            self.frame = None

    def read(self):
        with self.lock:
            return self.frame.copy() if self.frame is not None else None

    def release(self):
        self.running = False
        self._release()