from pathlib import Path
from hashlib import sha256

import pandas as pd

from Core.models import Student


def excel_to_students(file: Path) -> list[Student]:
    """
    从Excel表格读取数据并转换为list[Student]

    参数：
        file(Path): Excel表格文件路径

    返回：
        list[Student]: 转换完毕的学生对象列表
    """
    # 读取Excel文件
    df = pd.read_excel(file)

    # 列名映射（如果Excel列名与类字段名不同）
    column_mapping = {
        '学号': 'uid',
        '姓名': 'nickname',
        '密码': 'password'
    }
    df = df.rename(columns=column_mapping)

    # 将DataFrame转换为Student对象列表
    students = []
    for _, row in df.iterrows():
        try:
            student = Student(
                uid=int(row['uid']),
                nickname=str(row['nickname']),
                password=sha256(str(row['password']).strip().encode("utf-8")).hexdigest()
            )
            students.append(student)
        except Exception as e:
            print(f"Error creating student from row {_}: {e}")

    return students
