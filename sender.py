# import requests
# import time
# import logging
# import yaml
#
# # ===================== 读取配置 =====================
# def load_config(config_path="config.yaml"):
#     with open(config_path, "r", encoding="utf-8") as f:
#         return yaml.safe_load(f)
#
# config = load_config()
#
# # ===================== 日志 =====================
# def setup_sender_logger():
#     logger = logging.getLogger("car_sender")
#     logger.setLevel(logging.INFO)
#     if logger.handlers:
#         return logger
#
#     formatter = logging.Formatter("%(asctime)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
#
#     ch = logging.StreamHandler()
#     ch.setFormatter(formatter)
#
#     from logging.handlers import TimedRotatingFileHandler
#     import os
#     LOG_DIR = "./logs"
#     os.makedirs(LOG_DIR, exist_ok=True)
#     fh = TimedRotatingFileHandler(
#         os.path.join(LOG_DIR, "sender.log"),
#         when="midnight",
#         interval=1,
#         backupCount=7,
#         encoding="utf-8"
#     )
#     fh.setFormatter(formatter)
#
#     logger.addHandler(ch)
#     logger.addHandler(fh)
#     return logger
#
# logger = setup_sender_logger()
#
# # ===================== 接口地址 =====================
# UPDATE_STATUS_URL = config["api"]["update_status_url"]
# Update_End_Status = config["api"]["UpdateEndStatus"]
#
# # ===================== 发送车辆状态 =====================
# def send_vehicle_status(status, direction):
#     status_desc = ""
#     for key, val in config["status_mapping"].items():
#         if val["code"] == status:
#             status_desc = val["desc"]
#             break
#
#     direction_desc = ""
#     for key, val in config["direction_mapping"].items():
#         if val["code"] == direction:
#             direction_desc = val["desc"]
#             break
#
#     try:
#         params = {"status": status, "direction": direction}
#         response = requests.get(UPDATE_STATUS_URL, params=params, timeout=2)
#
#         if response.status_code == 200:
#             logger.info(f"✅ 发送成功 | 状态：{status_desc} | 方向：{direction_desc}")
#         else:
#             logger.info(f"❌ 发送失败{response.status_code} | 状态：{status_desc} | 方向：{direction_desc}")
#
#     except Exception as e:
#         logger.info(f"❌ 发送异常 | 状态：{status_desc} | 方向：{direction_desc} | 异常：{str(e)}")
#
# # ===================== 【修复】发送来车/过车结束 =====================
# def send_update_order(status):
#     status = "无车" if status == 1 else "来车启动"
#     try:
#         response = requests.get(Update_End_Status, timeout=1)
#         if response.status_code == 200:
#             logger.info("✅ UpdateOrder 调用成功")
#         else:
#             logger.info("❌ UpdateOrder 调用失败")
#     except:
#         logger.info("❌ UpdateOrder 调用异常")
#
# # if __name__ == '__main__':
# #     send_vehicle_status(0,1)
# #     send_update_order(1)   # 来车
#     # send_update_order(0)     # 过车结束


import requests
import time
import logging
import yaml


# ===================== 读取配置 =====================
def load_config(config_path="config.yaml"):
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


config = load_config()


# ===================== 日志 =====================
def setup_sender_logger():
    logger = logging.getLogger("car_sender")
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger

    formatter = logging.Formatter("%(asctime)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    ch = logging.StreamHandler()
    ch.setFormatter(formatter)

    from logging.handlers import TimedRotatingFileHandler
    import os
    LOG_DIR = "./logs"
    os.makedirs(LOG_DIR, exist_ok=True)
    fh = TimedRotatingFileHandler(
        os.path.join(LOG_DIR, "sender.log"),
        when="midnight",
        interval=1,
        backupCount=7,
        encoding="utf-8"
    )
    fh.setFormatter(formatter)

    logger.addHandler(ch)
    logger.addHandler(fh)
    return logger


logger = setup_sender_logger()

# ===================== 接口地址 =====================
UPDATE_STATUS_URL = config["api"]["update_status_url"]
Update_End_Status = config["api"]["UpdateEndStatus"]
UPDATE_ORDER_URL = config["api"]["UpdateOrder"]  # 新增：车辆计数接口地址


# ===================== 发送车辆状态（原有功能） =====================
def send_vehicle_status(status, direction):
    """
    发送车辆行驶/停车状态及方向信息
    :param status: 状态编码（0=已停车，1=行驶中）
    :param direction: 方向编码（0=正向，1=反向）
    """
    status_desc = ""
    for key, val in config["status_mapping"].items():
        if val["code"] == status:
            status_desc = val["desc"]
            break

    direction_desc = ""
    for key, val in config["direction_mapping"].items():
        if val["code"] == direction:
            direction_desc = val["desc"]
            break

    try:
        params = {"status": status, "direction": direction}
        response = requests.get(UPDATE_STATUS_URL, params=params, timeout=2)

        if response.status_code == 200:
            logger.info(f"✅ 发送成功 | 状态：{status_desc} | 方向：{direction_desc}")
        else:
            logger.info(f"❌ 发送失败{response.status_code} | 状态：{status_desc} | 方向：{direction_desc}")

    except Exception as e:
        logger.info(f"❌ 发送异常 | 状态：{status_desc} | 方向：{direction_desc} | 异常：{str(e)}")


# ===================== 发送来车/过车结束信号（原有功能） =====================
def send_update_order(status):
    """
    发送来车启动/过车结束信号（原有逻辑修复后）
    :param status: 1=来车启动，0=过车结束
    """
    status_desc = "来车启动" if status == 1 else "过车结束"
    try:
        response = requests.get(Update_End_Status, timeout=1)
        if response.status_code == 200:
            logger.info(f"✅ UpdateOrder调用成功 | 状态：{status_desc}")
        else:
            logger.info(f"❌ UpdateOrder调用失败 | 状态码：{response.status_code} | 状态：{status_desc}")
    except Exception as e:
        logger.info(f"❌ UpdateOrder调用异常 | 状态：{status_desc} | 异常：{str(e)}")


# ===================== 新增：发送车辆计数信息 =====================
def send_car_count(car_count):
    """
    发送车辆经过计数区域的累计数量
    :param car_count: 累计车辆数（正向+1，反向-1）
    """
    try:
        # 构造请求参数：传递累计车辆数
        params = {"car_count": car_count}
        response = requests.get(UPDATE_ORDER_URL, params=params, timeout=2)

        if response.status_code == 200:
            logger.info(f"✅ 车辆计数发送成功 | 累计数量：{car_count} 辆")
        else:
            logger.error(f"❌ 车辆计数发送失败 | 状态码：{response.status_code} | 累计数量：{car_count} 辆")
    except Exception as e:
        logger.error(f"❌ 车辆计数发送异常 | 累计数量：{car_count} 辆 | 异常信息：{str(e)}")


# 测试代码（可选）
if __name__ == '__main__':
    # send_vehicle_status(0,1)  # 测试状态发送
    # send_update_order(1)      # 测试来车信号
    # send_update_order(0)      # 测试过车结束信号
    # send_car_count(5)         # 测试计数发送
    send_car_count(5)