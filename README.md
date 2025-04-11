<p align="center">
  <a href="https://github.com/yincangshiwei/MTR_ImageTagManager/releases">Download</a>
</p>

- - -
## 项目介绍

> 模型训练：图片标签管理工具。

> 该工具主要用于处理图像训练集的标签

## 功能介绍

> 支持宫格图和列表视图切换

> 支持历史打开记录（默认只保留5个）

> 支持批量处理：添加、替换和删除

> 支持翻译配置：目前只增加百度翻译

> 支持宫格配置：配置宫格显示数量

> 支持配置存储：百度翻译和宫格数量会保存到config.ini配置文件里 

> 支持翻译功能：完整编辑和标签管理都支持翻译操作，包括翻译窗口里面也支持修改和翻译。


## 使用说明

> 运行文件：使用msi安装，执行目录里面的MTR_ImageTagManager.exe

### 百度API获取

1. 访问翻译开放平台：https://fanyi-api.baidu.com/
2. 注册登录后查看开发者信息
   ![image](https://github.com/user-attachments/assets/04825193-9f1f-4e5d-bdca-f7677bd96105)
   ![image](https://github.com/user-attachments/assets/8fc24d7c-c8b1-43df-b468-71ded3074b86)
 

## 相关技术

> Python版本：3.10.16(大于3.8都可)

> GUI UI使用：tkinter

> 打包程序使用：cx_freeze

### 目录结构

```
MTR_ImageTagManager/
├── main.py
├── setup.py
├── requirements.txt
├── README.md
├── config.ini
```

```

架构介绍：

- `main.py`: 主程序文件。
- `setup.py`: 用于打包应用程序的脚本。
- `requirements.txt`: 列出了所有依赖项。
- `README.md`: 项目的说明文档（中文）。
- `config.ini`: 配置文件。
```

## 安装说明

### 1. 拉取项目
```sh
git clone https://github.com/yincangshiwei/MTR_ImageTagManager.git
```

### 2. 进入项目目录
```sh
cd MTR_ImageTagManager
```

### 3. 安装相关依赖
```sh
pip install -r requirements.txt
```

### 4. 运行文件
```sh
python -u main.py
```

### 5. 打包exe
```sh
python setup.py build

# 打包msi
# python setup.py bdist_msi
```
