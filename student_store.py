"""
核心业务模块：学生数据的存取、增删改查、校验、去重、日志。
从控制台版 studentcms.py 抽出（去掉 input()/print()），供 Web 版 app.py 调用。
"""

import os                    # 判断文件是否存在/大小（load 时用
import json                  # JSON 读写 stu_data.txt
import datetime              # 日志时间戳
from student import Student  # 学生数据模型 导入

#代码文件所在目录的绝对路径（本地和线上服务器通用）
#保证数据文件、日志始终生成在项目目录里，不会因为运行目录不同而找不到
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, 'stu_data.txt')
LOG_FILE = os.path.join(BASE_DIR, 'operation.log')


class StudentStore:
    #角色显示名映射：日志里显示"管理员/普通老师"，与控制台版格式保持一致
    #Web 版要把 `'admin'` 翻译成 "管理员" 显示。
    ROLE_NAMES = {'admin': '管理员', 'teacher': '普通老师'}

    def __init__(self):
        self.stu_list = []   # 学生对象列表：[Student(), Student(), ...]
        self.role = None     # 当前登录角色：'admin' 管理员 / 'teacher' 普通老师

    # ============ 数据存取 ============

    #从 stu_data.txt 读取学生数据（文件存在且非空时才读）
    def load_student(self):
        if os.path.exists(DATA_FILE) and os.path.getsize(DATA_FILE) > 0:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                stu_list = json.loads(f.read())
            #把 [字典, 字典, ...] 转成 [Student对象, Student对象, ...]
            self.stu_list = [Student(**d) for d in stu_list]

    #把学生列表写成 JSON 存回 stu_data.txt（Web 版：每次增删改后立即保存）
    def save_student(self):
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            f.write(json.dumps([s.__dict__ for s in self.stu_list],
                               ensure_ascii=False, indent=4))

    # ============ 操作日志 ============

    #追加一行到 operation.log（时间 | 操作 | 谁 | 详情）
    def write_log(self, content):
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"{now} | {content}\n")

    #把角色代码转成中文显示名（admin→管理员，teacher→普通老师）
    def role_name(self):
        return self.ROLE_NAMES.get(self.role, self.role)

    # ============ 校验规则（与控制台版一致）============

    #校验函数统一返回 (是否通过, 错误提示)
    #网页不能重输，所以改成返回 (对错, 提示语) 让网页直接显示错误原因。
    @staticmethod
    def check_name(name):
        return name.strip() != "", "姓名不能为空！"

    @staticmethod
    def check_gender(gender):
        return gender in ["男", "女"], "性别只能输入男或女！"

    @staticmethod
    def check_age(age):
        return age.isdigit() and 1 <= int(age) <= 150, "年龄必须是 1~150 的数字！"

    @staticmethod
    def check_phone(phone):
        return phone.isdigit() and len(phone) == 11, "电话必须是 11 位数字！"

    # ============ 去重 ============

    #判断是否存在同名（和控制台版"遍历拦截"同一逻辑）
    def is_duplicate(self, name):
        return any(stu.name == name for stu in self.stu_list) # any = 只要有任何一个满足就 True

    # ============ 增删改查 ============

    #添加学生：入参是网页表单传来的值；返回 (成功?, 提示信息)
    def add_student(self, name, gender, age, phone, desc):
        name = name.strip()
        #1.去重拦截（先于其他校验，和原版一致）
        if self.is_duplicate(name):
            return False, f"学生{name}已存在，不能重复添加！"
        #2.逐项校验
        ok, msg = self.check_gender(gender)
        if not ok:
            return False, msg
        ok, msg = self.check_age(age)
        if not ok:
            return False, msg
        ok, msg = self.check_phone(phone)
        if not ok:
            return False, msg
        #3.封装成学生对象并加入列表
        stu = Student(name, gender, int(age), phone, desc.strip())
        self.stu_list.append(stu)
        #4.记日志 + 立即保存
        self.write_log(f"添加学生 | {self.role_name()} | 添加姓名：{name}")
        self.save_student()
        return True, f"已添加{name}学生信息~"

    #删除学生：按姓名查找并移除；返回 (成功?, 提示信息)
    #原来 "删完还继续问"，现在**删一次返回一次**（网页点一次按钮就完事），找不到就返回错误提示。
    def delete_student(self, name):
        for stu in self.stu_list:
            if stu.name == name:
                self.stu_list.remove(stu)
                self.write_log(f"删除学生 | {self.role_name()} | 删除姓名：{name}")
                self.save_student()
                return True, f"已删除{name}学生信息~"
        return False, f"未找到学生{name}！"

    #修改学生：按姓名定位后整体更新；返回 (成功?, 提示信息)
    #原来修改是 "输入姓名→再一项项重输"，网页版是 "表单里改完一起提交"。
    def update_student(self, name, gender, age, phone, desc):
        for stu in self.stu_list:
            if stu.name == name:
                stu.gender = gender
                stu.age = int(age)
                stu.phone = phone
                stu.desc = desc.strip()
                self.write_log(f"修改学生 | {self.role_name()} | 修改姓名：{name}")
                self.save_student()
                return True, f"已修改{name}学生信息~"
        return False, f"未找到学生{name}！"

    #按姓名找单个学生，找不到返回 None
    def find_student(self, name):
        for stu in self.stu_list:
            if stu.name == name:
                return stu
        return None

    #批量导入学生（Excel 导入）：rows 是解析好的每行数据 [姓名,性别,年龄,电话,描述]
    #逐行复用"手动添加"的校验+去重规则；返回 (成功条数, 被跳过的说明列表)
    def import_students(self, rows):
        ok_count = 0
        skip_list = []
        for row in rows:
            #一行可能不足 5 列（Excel 末尾常有空格子），统一补成 5 个
            cells = [str(c).strip() if c is not None else '' for c in row]
            while len(cells) < 5:
                cells.append('')
            name, gender, age, phone, desc = cells[0], cells[1], cells[2], cells[3], cells[4]
            #整行全空则跳过（Excel 常见的空行）
            if not any(cells):
                continue
            #和手动添加走同一套规则：先去重，再逐项校验
            if self.is_duplicate(name):
                skip_list.append(f"{name}：已存在，跳过")
                continue
            ok, msg = self.check_gender(gender)
            if not ok:
                skip_list.append(f"{name}：{msg}")
                continue
            ok, msg = self.check_age(age)
            if not ok:
                skip_list.append(f"{name}：{msg}")
                continue
            ok, msg = self.check_phone(phone)
            if not ok:
                skip_list.append(f"{name}：{msg}")
                continue
            self.stu_list.append(Student(name, gender, int(age), phone, desc))
            ok_count += 1
        #批量导入：只记一条日志、只保存一次（不会像手动添加那样每条都写）
        self.write_log(f"导入学生 | {self.role_name()} | 成功导入{ok_count}条，跳过{len(skip_list)}条")
        self.save_student()
        return ok_count, skip_list

    # ============ 分页（复用控制台版公式）============

    #返回 (本页学生列表, 总条数, 总页数, 当前页码)
    def get_page(self, page, page_size=10):
        total = len(self.stu_list)
        #总页数：向上取整（有零头多算一页）
        pages = (total + page_size - 1) // page_size
        if pages == 0:
            pages = 1
        #页码越界时拉回合法范围
        if page < 1:
            page = 1
        if page > pages:
            page = pages
        #切片取本页
        start = (page - 1) * page_size
        end = start + page_size
        return self.stu_list[start:end], total, pages, page
