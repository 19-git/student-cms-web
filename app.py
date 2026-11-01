"""
Flask Web 版学生管理系统：路由 + 页面逻辑。
界面层只负责"接网址、收表单、调核心模块、返回页面"，业务逻辑全在 student_store 里。
"""

import os
from io import BytesIO
from flask import Flask, request, session, redirect, url_for, render_template, flash, send_file
from openpyxl import Workbook, load_workbook
from werkzeug.security import generate_password_hash, check_password_hash
from student_store import StudentStore

#创建 Flask 应用
app = Flask(__name__)
#session 加密密钥：登录状态靠它（部署时改成自己的随机串）
app.secret_key = 'student-cms-web-secret'

#全局核心业务对象（load/save/增删改查/校验/去重/日志/分页都在里面）
store = StudentStore()

#管理员密码：优先读环境变量 ADMIN_PASSWORD（部署时在 Render 后台设置，代码不用改）
#默认密码 123456；ADMIN_PASSWORD_HASH 存的是密码的"哈希"，代码里看不到明文
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', '123456')
ADMIN_PASSWORD_HASH = generate_password_hash(ADMIN_PASSWORD)


#每次请求前自动执行：从文件加载最新数据 + 同步登录角色
#（这样任何时刻数据都是最新的，部署多个进程时也不会互相覆盖）
@app.before_request
def prepare():
    store.load_student()
    store.role = session.get('role')


# ============ 首页 / 登录 / 退出 ============

#首页：没登录去登录页，已登录进学生列表
@app.route('/')
def index():
    if not session.get('role'):
        return redirect(url_for('login'))
    return redirect(url_for('student_list'))


#登录页：GET 显示表单，POST 处理提交
@app.route('/login', methods=['GET', 'POST'])
#访问首页：没登录 → 跳登录页；登录了 → 跳学生列表。
def login():
    if request.method == 'POST':
        role = request.form.get('role')               # 表单里选的角色：'1'管理员 / '2'普通老师
        password = request.form.get('password', '')   # 密码（普通老师可留空）
        if role == '1':
            if check_password_hash(ADMIN_PASSWORD_HASH, password):   # 比的是哈希，不是明文
                session['role'] = 'admin'             # 记住登录状态
                store.role = 'admin'
                store.write_log("登录 | 管理员 | 成功")
                flash("管理员登录成功~")
                return redirect(url_for('student_list'))
            store.write_log("登录 | 管理员 | 密码错误")
            flash("密码错误，请重新输入！")
        elif role == '2':
            session['role'] = 'teacher'
            store.role = 'teacher'
            store.write_log("登录 | 普通老师 | 成功")
            flash("普通老师登录成功~")
            return redirect(url_for('student_list'))
        else:
            flash("请选择登录角色！")
    return render_template('login.html')


#退出登录：清掉 session 里的登录状态
@app.route('/logout')
def logout():
    session.clear()
    store.role = None
    flash("已退出登录~")
    return redirect(url_for('login'))


# ============ 学生列表（分页） ============

@app.route('/list')
def student_list():
    #从网址 ?page=2 里取页码，默认第 1 页
    page = request.args.get('page', 1, type=int)
    #调核心模块分页：拿到 本页学生 / 总数 / 总页数 / 当前页码
    students, total, pages, page = store.get_page(page)
    return render_template('list.html', students=students, total=total,
                           pages=pages, page=page)


# ============ 添加（仅管理员） ============

@app.route('/add', methods=['GET', 'POST'])
def add_student():
    #权限拦截：普通老师不能改数据（和原版同一句提示）
    if store.role != 'admin':
        flash("权限不足：普通老师只能查看，不能修改数据！")
        return redirect(url_for('student_list'))
    if request.method == 'POST':
        #从表单一次性取 5 个字段（对应原版 5 次 input）
        name = request.form.get('name', '')
        gender = request.form.get('gender', '')
        age = request.form.get('age', '')
        phone = request.form.get('phone', '')
        desc = request.form.get('desc', '')
        #交给核心模块校验+添加，返回 (成功?, 提示)
        ok, msg = store.add_student(name, gender, age, phone, desc)
        flash(msg)
        if ok:
            return redirect(url_for('student_list'))
        #失败：带着已填的值回到添加页（不用重填）
        return render_template('add.html', name=name, gender=gender,
                               age=age, phone=phone, desc=desc)
    return render_template('add.html')


# ============ 修改（仅管理员） ============

@app.route('/edit/<name>', methods=['GET', 'POST'])
def edit_student(name):
    if store.role != 'admin':
        flash("权限不足：普通老师只能查看，不能修改数据！")
        return redirect(url_for('student_list'))
    #按姓名找学生，找不到就回列表
    stu = store.find_student(name)
    if stu is None:
        flash(f"未找到学生{name}！")
        return redirect(url_for('student_list'))
    if request.method == 'POST':
        gender = request.form.get('gender', '')
        age = request.form.get('age', '')
        phone = request.form.get('phone', '')
        desc = request.form.get('desc', '')
        ok, msg = store.update_student(name, gender, age, phone, desc)
        flash(msg)
        return redirect(url_for('student_list'))
    #GET：把学生旧值传给模板，表单预填
    return render_template('edit.html', stu=stu)


# ============ 删除（仅管理员） ============

#用 POST 而不是 GET：删除是有风险的操作，POST 避免"点个链接就删了"
@app.route('/delete/<name>', methods=['POST'])
def delete_student(name):
    if store.role != 'admin':
        flash("权限不足：普通老师只能查看，不能修改数据！")
        return redirect(url_for('student_list'))
    ok, msg = store.delete_student(name)
    flash(msg)
    return redirect(url_for('student_list'))


# ============ Excel 导出（管理员和老师都可以） ============

@app.route('/export')
def export_excel():
    if not store.role:
        flash("请先登录！")
        return redirect(url_for('login'))
    #在内存里生成 Excel（不落盘），直接作为附件下载
    wb = Workbook()
    ws = wb.active
    ws.title = "学生信息"
    ws.append(['姓名', '性别', '年龄', '电话', '描述'])   # 第一行表头（与控制台版一致）
    for stu in store.stu_list:
        ws.append([stu.name, stu.gender, stu.age, stu.phone, stu.desc])
    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)
    return send_file(bio, as_attachment=True, download_name='学生信息.xlsx',
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


# ============ Excel 导入（仅管理员） ============

@app.route('/import', methods=['POST'])
def import_excel():
    if store.role != 'admin':
        flash("权限不足：普通老师只能查看，不能修改数据！")
        return redirect(url_for('student_list'))
    file = request.files.get('file')                 # 取上传的文件
    if file is None or file.filename == '':
        flash("请先选择要导入的 Excel 文件！")
        return redirect(url_for('student_list'))
    if not file.filename.lower().endswith('.xlsx'):
        flash("只支持 .xlsx 格式的文件！")
        return redirect(url_for('student_list'))
    try:
        wb = load_workbook(file)                     # openpyxl 读 Excel
    except Exception as e:
        flash(f"Excel 文件解析失败：{e}")
        return redirect(url_for('student_list'))
    ws = wb.active
    rows = []
    #跳过第一行表头，从第二行开始取数据
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row is None:
            continue
        rows.append(list(row))
    #交给核心模块批量导入（校验/去重/日志/保存都在里面）
    ok_count, skip_list = store.import_students(rows)
    msg = f"导入完成：成功 {ok_count} 条，跳过 {len(skip_list)} 条"
    if skip_list:
        msg += "；跳过原因：" + "；".join(skip_list[:5]) + ("……" if len(skip_list) > 5 else "")
    flash(msg)
    return redirect(url_for('student_list'))


# ============ 启动 ============

if __name__ == '__main__':
    #PORT 环境变量由部署平台（Render）提供；本地运行默认 5000
    port = int(os.environ.get('PORT', 5000))
    #debug=True：本地改代码自动重启、报错页面更详细；上线部署时改成 False
    app.run(host='0.0.0.0', port=port, debug=True)
