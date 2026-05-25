from ultralytics import YOLO
import cv2
import torch
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import logging
from logging.handlers import TimedRotatingFileHandler
import time
import os
import yaml

from get_video import RTSPCapture
from sender import send_vehicle_status, send_update_order, send_car_count  # 新增导入send_car_count

# ==================== 读取配置文件 ====================
def load_config(config_path="config.yaml"):
    """读取yaml配置文件"""
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

config = load_config()

# ==================== 日志模块初始化 ====================
LOG_DIR = "./logs"
os.makedirs(LOG_DIR, exist_ok=True)

def setup_logger(name, log_file, level=logging.INFO):
    """初始化日志器：控制台+按天轮转文件日志"""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if logger.handlers:  # 避免重复添加处理器
        return logger

    formatter = logging.Formatter("%(asctime)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    # 控制台处理器
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    # 文件处理器（按天轮转，保留10天）
    file_handler = TimedRotatingFileHandler(log_file, when="midnight", interval=1, backupCount=10, encoding="utf-8")
    file_handler.setFormatter(formatter)

    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)
    return logger

logger = setup_logger("car_direction", os.path.join(LOG_DIR, "direction.log"))

# ==================== 模型初始化 ====================
# 自动降级设备：优先GPU，无则CPU
device = config["device"] if torch.cuda.is_available() else "cpu"
MODEL_PATH = config["model_path"]

def init_model():
    """初始化YOLOv8检测模型"""
    model = YOLO(MODEL_PATH, task="detect")
    logger.info("✅ 模型初始化完成")
    return model

model = init_model()

# ==================== 全局状态变量 ====================
prev_position = {}          # 车辆上一帧位置 {id: (cx, cy)}
stop_counter = {}           # 停车计数 {id: count}
last_direction = {}         # 上一帧方向 {id: "left"/"right"}
direction_counter = {}      # 方向稳定计数 {id: count}
stable_direction = {}       # 稳定方向 {id: "left"/"right"}
locked_direction = {}       # 停车锁定方向 {id: "left"/"right"}
last_send_status = {}       # 最后发送的状态 {id: (status_code, dir_code)}

start_after_stop_counter = {}  # 停车后启动计数 {id: count}
IGNORE_START_FRAMES = config["thresholds"]["ignore_start_frames"]  # 启动忽略帧
restart_direction_counter = {} # 重启方向计数 {id: count}
RESTART_DIR_FRAMES = config["thresholds"]["restart_dir_frames"]    # 重启方向稳定帧

no_car_counter = 0          # 无车计数
NO_CAR_FRAMES = config["thresholds"]["no_car_frames"]  # 无车清空阈值
no_car_flag = False         # 无车标记

has_sent_car_coming = False # 已发送来车信号标记
has_sent_car_end = False    # 已发送过车结束信号标记

no_car_frame_count = 0      # 无车帧计数（用于过车结束等待）
WAIT_AFTER_CAR_END = config["thresholds"]["car_end_wait_seconds"]  # 过车结束等待秒数

# 核心阈值配置
STOP_THRESH = config["thresholds"]["stop_thresh"]    # 停车位移阈值
STOP_FRAMES = config["thresholds"]["stop_frames"]    # 停车稳定帧
DIR_FRAMES = config["thresholds"]["dir_frames"]      # 方向稳定帧

COUNT_AREA = tuple(config["count_area"])  # 计数区域 (x1, y1, x2, y2)
car_count = 0                             # 累计车辆数（正向+1，反向-1）
counted_ids = set()                       # 已计数的车辆ID集合
last_sent_car_count = -1                  # 新增：最后一次发送的计数（避免重复发送）

# ==================== 加载中文字体（修复中文不显示） ====================
try:
    font = ImageFont.truetype("simhei.ttf", 20)  # 优先加载黑体
except:
    try:
        font = ImageFont.truetype("msyh.ttc", 20) # 备用加载微软雅黑
    except:
        font = ImageFont.load_default()           # 最终默认字体

# ==================== 工具函数 ====================
def cv2_put_text(img, text, pos, color=(0, 255, 0)):
    """
    OpenCV中文绘制函数：解决cv2.putText中文乱码问题
    :param img: 输入图像
    :param text: 要绘制的文字
    :param pos: 绘制位置 (x, y)
    :param color: 文字颜色 (R, G, B)
    :return: 绘制后的图像
    """
    img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img_pil)
    draw.text(pos, text, font=font, fill=color)
    return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

def is_in_area(cx, cy, area):
    """
    判断坐标是否在指定区域内
    :param cx: 中心点x坐标
    :param cy: 中心点y坐标
    :param area: 区域 (x1, y1, x2, y2)
    :return: True/False
    """
    x1, y1, x2, y2 = area
    return x1 < cx < x2 and y1 < cy < y2

# ==================== 主程序 ====================
if __name__ == "__main__":
    SOURCE = config["source"]
    logger.info("🚀 程序启动")
    cap = RTSPCapture(SOURCE)  # 初始化视频流读取器

    while True:
        frame = cap.read()
        if frame is None:  # 帧读取失败，短暂等待后重试
            time.sleep(0.05)
            continue

        try:
            # YOLOv8跟踪推理
            results = model.track(
                source=frame,
                persist=True,        # 持久化跟踪器
                tracker="bytetrack.yaml",  # ByteTrack跟踪器配置
                device=device,       # 推理设备
                conf=config["conf"], # 置信度阈值
                iou=config["iou"],   # IOU阈值
                imgsz=config["imgsz"],# 推理图像尺寸
                half = True,
                stream = True  # 启用异步流，减少等待时间
            )

            # 绘制计数区域
            x1_area, y1_area, x2_area, y2_area = COUNT_AREA
            cv2.rectangle(frame, (x1_area, y1_area), (x2_area, y2_area), (255, 255, 0), 2)
            frame = cv2_put_text(frame, "计数区域", (x1_area, y1_area - 25), (255, 255, 0))

            has_car = False  # 本帧是否检测到车辆标记

            # 检测到有车辆跟踪结果
            if results[0].boxes.id is not None:
                has_car = True
                no_car_counter = 0      # 重置无车计数
                no_car_flag = False     # 重置无车标记
                no_car_frame_count = 0  # 重置无车帧计数

                # 首次检测到车辆，发送来车信号
                if not has_sent_car_coming:
                    send_update_order(1)
                    logger.info("📦 检测到车辆，发送来车信号")
                    has_sent_car_coming = True
                    has_sent_car_end = False

                # 提取车辆ID和检测框
                ids = results[0].boxes.id.cpu().numpy().astype(int)
                boxes = results[0].boxes.xyxy.cpu().numpy().astype(int)

                # 遍历每辆检测到的车辆
                for id, box in zip(ids, boxes):
                    x1, y1, x2, y2 = box
                    cx = (x1 + x2) // 2  # 计算中心点x
                    cy = (y1 + y2) // 2  # 计算中心点y

                    # 初始化车辆状态（首次出现）
                    if id not in stop_counter:
                        stop_counter[id] = 0
                        last_direction[id] = ""
                        direction_counter[id] = 0
                        stable_direction[id] = ""
                        locked_direction[id] = ""
                        start_after_stop_counter[id] = 0
                        restart_direction_counter[id] = 0

                    dx, dy = 0, 0
                    current_direction = ""
                    is_stopped = False

                    # 计算位移和方向（基于上一帧位置）
                    if id in prev_position:
                        prev_cx, prev_cy = prev_position[id]
                        dx = cx - prev_cx  # x方向位移
                        dy = cy - prev_cy  # y方向位移

                        # 过滤微小位移（防抖）
                        if abs(dx) < 3:
                            dx = 0

                        # 判断是否停车：位移小于停车阈值
                        is_stopped = abs(dx) < STOP_THRESH and abs(dy) < STOP_THRESH

                        # 判断行驶方向（仅x方向有效）
                        if abs(dx) >= 2:
                            current_direction = "right" if dx > 0 else "left"

                    # 方向稳定性判断（非停车状态）
                    if current_direction and not is_stopped:
                        if current_direction == last_direction[id]:
                            direction_counter[id] += 1  # 同一方向计数+1
                        else:
                            direction_counter[id] = 1   # 方向变化，重置计数
                            last_direction[id] = current_direction

                        # 达到方向稳定帧，更新稳定方向
                        if direction_counter[id] >= DIR_FRAMES:
                            stable_direction[id] = current_direction
                            locked_direction[id] = current_direction

                    # 停车计数更新
                    if is_stopped:
                        stop_counter[id] += 1
                    else:
                        stop_counter[id] = 0

                    # 最终停车判定：连续N帧静止
                    finally_stopped = stop_counter[id] >= STOP_FRAMES

                    # ==================== 停车重启方向逻辑修复 ====================
                    if finally_stopped:
                        # 停车状态：重置启动相关计数
                        start_after_stop_counter[id] = 0
                        restart_direction_counter[id] = 0
                    else:
                        if stop_counter[id] == 0:
                            # 非停车且刚启动：计数+1
                            start_after_stop_counter[id] += 1
                            if start_after_stop_counter[id] == 1:
                                # 首次启动：清空历史方向状态
                                locked_direction[id] = ""
                                stable_direction[id] = ""
                                last_direction[id] = ""
                                direction_counter[id] = 0

                    # 停车状态下，稳定方向沿用锁定方向
                    if finally_stopped:
                        stable_direction[id] = locked_direction.get(id, "")

                    # 更新车辆上一帧位置
                    prev_position[id] = (cx, cy)

                    # ==================== 车辆计数逻辑 ====================
                    # 车辆在计数区域内 + 稳定方向已确定 + 未计数过
                    if is_in_area(cx, cy, COUNT_AREA):
                        if id not in counted_ids and stable_direction[id] != "":
                            # 正向（right）+1，反向（left）-1
                            if stable_direction[id] == "right":
                                car_count += 1
                            elif stable_direction[id] == "left":
                                car_count -= 1
                            counted_ids.add(id)  # 标记为已计数
                            logger.info(f"📊 车辆计数更新 | ID:{id} | 方向:{stable_direction[id]} | 累计:{car_count}")

                    # ==================== 状态发送过滤 ====================
                    if stable_direction[id] == "":
                        continue  # 方向未稳定，跳过
                    if not finally_stopped and start_after_stop_counter[id] < IGNORE_START_FRAMES:
                        continue  # 启动初期，跳过
                    if not finally_stopped:
                        # 行驶中：重启方向稳定判断
                        if stable_direction[id] == last_direction[id]:
                            restart_direction_counter[id] += 1
                        else:
                            restart_direction_counter[id] = 1
                        if restart_direction_counter[id] < RESTART_DIR_FRAMES:
                            continue  # 重启方向未稳定，跳过

                    # 过车结束信号已发送，跳过状态更新
                    if has_sent_car_end:
                        continue

                    # 构造当前状态（状态码+方向码）
                    dir_code = 0 if stable_direction[id] == "right" else 1
                    status_code = 0 if finally_stopped else 1
                    current_state = (status_code, dir_code)
                    last_state = last_send_status.get(id)

                    # 状态变化时发送更新
                    if current_state != last_state:
                        last_send_status[id] = current_state
                        status_txt = "已停车" if status_code == 0 else "行驶中"
                        dir_txt = "正向" if dir_code == 0 else "反向"
                        logger.info(f"✅ 发送状态 | 车辆ID:{id} | 状态：{status_txt} | 方向：{dir_txt}")
                        send_vehicle_status(status_code, dir_code)

                    # ==================== 绘制车辆信息 ====================
                    color = (0, 0, 255) if finally_stopped else (0, 255, 0)  # 停车红/行驶绿
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)       # 绘制检测框
                    cv2.circle(frame, (cx, cy), 5, color, -1)                # 绘制中心点
                    # 绘制车辆ID和方向
                    draw_text = f"ID:{id} | {stable_direction[id] if stable_direction[id] else '未知'}"
                    frame = cv2_put_text(frame, draw_text, (x1, y1 - 10), color)

            # ==================== 无车逻辑处理 ====================
            if not has_car:
                no_car_frame_count += 1
                no_car_counter += 1

                # 达到过车结束等待时间
                if no_car_frame_count >= WAIT_AFTER_CAR_END:
                    frame = cv2_put_text(frame, "过车结束", (30, 30), (255, 255, 0))
                    # 发送过车结束信号
                    if has_sent_car_coming and not has_sent_car_end:
                        send_update_order(0)
                        logger.info("✅ 过车结束，发送离开信号")
                        has_sent_car_end = True
                else:
                    frame = cv2_put_text(frame, "车辆离开中...", (30, 30), (255, 255, 0))

            # 长时间无车：清空所有状态（释放资源）
            if no_car_counter >= NO_CAR_FRAMES and not no_car_flag:
                logger.info("🧹 长时间无车，清空所有状态")
                prev_position.clear()
                stop_counter.clear()
                last_direction.clear()
                direction_counter.clear()
                stable_direction.clear()
                locked_direction.clear()
                last_send_status.clear()
                start_after_stop_counter.clear()
                restart_direction_counter.clear()
                counted_ids.clear()
                car_count = 0                 # 重置计数
                last_sent_car_count = -1      # 重置最后发送计数
                no_car_flag = True
                has_sent_car_coming = False
                has_sent_car_end = False

            # ==================== 新增：发送车辆计数（避免重复发送） ====================
            if car_count != last_sent_car_count:
                send_car_count(car_count)
                last_sent_car_count = car_count  # 更新最后发送计数

            # 绘制累计车辆数
            frame = cv2_put_text(frame, f"已通过：{car_count} 辆", (30, 60), (255, 255, 255))
            # 显示画面
            cv2.imshow("车辆检测与计数", frame)

            # 按q退出程序
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        except Exception as e:
            logger.error(f"❌ 程序异常：{str(e)}", exc_info=True)  # 打印异常堆栈  
            time.sleep(0.1)

    # 释放资源
    cap.release()
    cv2.destroyAllWindows()
    logger.info("🛑 程序正常退出")