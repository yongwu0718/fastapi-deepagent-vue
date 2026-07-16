import easyocr

# 1. 创建一个Reader对象，指定要识别的语言
# 'ch_sim' 是简体中文，'en' 是英文
reader = easyocr.Reader(['ch_sim', 'en']) [reference:8][reference:9]

# 2. 读取并识别图片
result = reader.readtext('你的图片路径.jpg') [reference:10]

# 3. 打印识别结果
for detection in result:
    # detection包含： (边界框坐标, 识别出的文字, 置信度) [reference:11]
    print(f"文本: {detection[1]}, 置信度: {detection[2]:.2f}")