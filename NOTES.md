# Latexam开发笔记

## Maintainer 管理端

### 文件系统

- log/ 客户端日志
- papers/ 考卷信息
  - **对于每个考卷文件夹，都有如下：**
    - assets/ 考卷需要的资源文件
    - paper.lep 考卷主文件（加密）
- latexam_maintainer.py 入口文件

### 实现

**注意，教师端实际上只是服务端的控制面板，所以这些考卷实际的操作位置在服务端，教师端的只是用于预览和查档**

首先，管理端要先弹出一个窗口，教师在此处输入服务器地址端口和密码进入系统。

接着，教师可以选择创建试卷，发布试卷，批改试卷。

在创建试卷中，教师可以创建并编辑题目，每个题目（question）包含题干（title）、题目类型（type），题目类型可以是“choice”（单项选择题）或“common”（主观题），如果选择客观题，选项要包含入题干中。

这是一个完整的试卷实现：

```Python
class Paper:
    serial_number: int  # 试卷序列号
    title: str  # 试卷标题
    questions: list[Question]  # 试卷题目内容

class Question:
    title: str  # 题干，Markdown语法
    type: str  # 题目类型
```

发布试卷需要教师使用已有考卷文件夹，并且规定时间以及考试人员列表（可导入，如果费事，不另外安排数据库给考试人员列表）。

这是考试的实现和考试人员实现：

```Python
class Exam:
    paper: Paper  # 考试使用的考卷
    title: str  # 考试标题
    start_time: int  # 开始时间戳
    end_time: int  # 结束时间戳
    student_list: list[Student]  # 考试人员列表

class Student:
    number: int  # 准考证号
    name: str  # 名字
    password: str  # MD5化的密码，用于验证
```

完成后，教师便成功命令服务器准备考试系统，管理端全程无需参加“监考”。

## Server 服务端

### 文件系统

- log/ 服务器日志
- papers/ 考卷信息
  - assets/ 考卷需要的资源文件
  - paper.lep 考卷主文件（加密）
- latexam_server.py 入口文件

除了教师端实现外，server本身可能需要一个抽象的Server类来进行总运作。

通信采用HTTP封装库，减轻网络通信的难度。

基本上功能和教师端学生端对着写就行，只不过要注意的是临时存储的答题卡文件以及试卷文件是要在服务端本地加密的。

服务器在一个时候只能进行一次考试！

## Student 学生端

### 文件系统

- log/ 客户端日志
- papers/ 考卷信息
  - assets/ 考卷需要的资源文件
  - paper.lep 考卷主文件（加密）
- latexam_student.py 入口文件

学生端可以连接到服务器，并且看到服务器目前考试状况，选择加入考试。

正常答题即可，答完整套试卷后再进行提交。