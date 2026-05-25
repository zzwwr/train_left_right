import os
import random
import shutil
def checkFile(path): #获取label的全部绝对路径存入列表
    listSaveLabel = []
    for i in os.listdir(path):
        listSaveLabel.append(path+"\\"+i)
    return listSaveLabel

def splitList(lst,ratio): #将列表按比例切分出来数据
    split_idx1 = int(len(lst) * ratio[0] / sum(ratio))
    split_idx2 = split_idx1 + int(len(lst) * ratio[1] / sum(ratio))
    return lst[:split_idx1], lst[split_idx1:split_idx2], lst[split_idx2:]

def saveLabel(saveLabelPath,train,val,test): #将切分出来的数据集进行数据划分
    trainPath = saveLabelPath+"//train"
    testPath = saveLabelPath+"//test"
    valPath = saveLabelPath+"//val"

    if not os.path.exists(testPath):
        os.makedirs(testPath)
    if not os.path.exists(trainPath):
        os.makedirs(trainPath)
    if not os.path.exists(valPath):
        os.makedirs(valPath)

    for trainFile in train:
        if os.path.isfile(trainFile):
            newFilePath1 = os.path.join(trainPath, os.path.basename(trainFile))
            shutil.copy(trainFile, newFilePath1)


    for testFile in test:
        if os.path.isfile(testFile):
            newFilePath2 = os.path.join(testPath, os.path.basename(testFile))
            shutil.copy(testFile, newFilePath2)

    for valFile in val:
        if os.path.isfile(valFile):
            newFilePath3 = os.path.join(valPath, os.path.basename(valFile))
            shutil.copy(valFile, newFilePath3)

def saveImg(saveImgPath,train,val,test):  #这里需要替换图片的地址
    trainPath = saveImgPath+"//train"
    testPath = saveImgPath+"//test"
    valPath = saveImgPath+"//val"

    if not os.path.exists(testPath):
        os.makedirs(testPath)
    if not os.path.exists(trainPath):
        os.makedirs(trainPath)
    if not os.path.exists(valPath):
        os.makedirs(valPath)

    for trainFile in train:
        trainFile = trainFile.replace("label", "image")
        trainFile = trainFile.replace("txt", "jpg")
        if os.path.isfile(trainFile):
            newFilePath1 = os.path.join(trainPath, os.path.basename(trainFile))
            shutil.copy(trainFile, newFilePath1)

    for testFile in test:
        testFile = testFile.replace("label", "image")
        testFile = testFile.replace("txt", "jpg")
        if os.path.isfile(testFile):
            newFilePath2 = os.path.join(testPath, os.path.basename(testFile))
            shutil.copy(testFile, newFilePath2)

    for valFile in val:
        valFile = valFile.replace("label", "image")
        valFile = valFile.replace("txt", "jpg")
        if os.path.isfile(valFile):
            newFilePath2 = os.path.join(valPath, os.path.basename(valFile))
            shutil.copy(valFile, newFilePath2)


path = r"E:\yoloV8MAIN\ultralytics-main\MuBiaoGenZong\视频切分图像\data\label"
saveLabelFile = r"E:\yoloV8MAIN\ultralytics-main\MuBiaoGenZong\视频切分图像\labels"
saveImageFile = r"E:\yoloV8MAIN\ultralytics-main\MuBiaoGenZong\视频切分图像\images"
ratio = [8,1,1]

labelList = checkFile(path)
random.shuffle(labelList)
train, val, test = splitList(labelList,ratio)
print("正在分别存入label标签到新建文件夹中")
saveLabel(saveLabelFile,train,val,test)
print("正在分别存入image图片到新建文件夹中")
saveImg(saveImageFile,train,val,test)

