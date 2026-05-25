from ultralytics import YOLO
import torch

if __name__ == "__main__":    # 加载模型
    model_yaml = r"E:\yoloV8MAIN\ultralytics-main\ultralytics\cfg\models\v8\yolov8.yaml"
    data_yaml = r"E:\yoloV8MAIN\ultralytics-main\ultralytics\cfg\datasets\train.yaml"
    pre_model = r"E:\yoloV8MAIN\ultralytics-main\MuBiaoGenZong\yolov8s.pt" #E:\yoloV8MAIN\ultralytics-main\yolov8s.pt

    # build from YAML and transfer weights
    model = YOLO(model_yaml, task='detect').load(pre_model)
    if torch.cuda.is_available():
        device = torch.device('cuda')
        model.to(device)
    # 训练模型
    results = model.train(data=data_yaml, epochs=100, imgsz=460, batch=16, workers=1)
