# 学生管理系统（Web 版）

基于 Flask 的学生信息管理系统。由控制台版改造而来：**业务逻辑全部复用**（校验 / 去重 / 分页 / 日志 / 权限 / JSON 存储），只把 `input()/print()` 换成了"表单 + 网页"。

## 功能

| 功能 | 说明 |
|---|---|
| 登录 + 角色权限 | 管理员可增删改查；普通老师只能查看 |
| 学生列表分页 | 10 条/页，上一页/页码/下一页 |
| 添加 / 修改 / 删除 | 网页表单，删除有确认框、用 POST 防误删 |
| 操作日志 | 记录"时间 \| 操作 \| 角色 \| 详情"，追加写入 operation.log |
| Excel 导入导出 | openpyxl，批量导入复用校验/去重规则 |
| 密码安全 | 哈希存储（werkzeug），登录页不泄露密码 |

## 技术栈

- Python 3 + Flask 3.1
- 数据存储：JSON 文件（`stu_data.txt`）
- Excel：openpyxl

## 项目结构

```
app.py              Flask 路由 + 页面逻辑（界面层）
student_store.py    核心业务模块（存取/增删改查/校验/去重/分页/日志/批量导入）
student.py          Student 数据模型
templates/          HTML 页面（Jinja2）：base / login / list / add / edit
requirements.txt    依赖清单
```

## 本地运行

```bash
pip install -r requirements.txt
python app.py
```

浏览器打开 http://127.0.0.1:5000

> ⚠️ **本地默认管理员密码：123456（仅限本地学习用）。**
> 部署上线前，务必在部署平台设置环境变量 `ADMIN_PASSWORD` 换成你自己的强密码；代码里只有密码的哈希，不存明文。

## 部署（PythonAnywhere）

线上地址：https://yzygit.pythonanywhere.com

1. 注册 PythonAnywhere（免费版即可）
2. 上传代码到 `/home/yzygit/student-cms-web/`
3. 创建 Web App（Manual configuration，Python 3.10）
4. 创建虚拟环境并安装依赖：

   ```bash
   mkvirtualenv --python=python3.10 myenv
   pip install flask openpyxl
   ```

5. 编辑 WSGI 配置文件（`/var/www/yzygit_pythonanywhere_com_wsgi.py`）：

   ```python
   import os, sys
   project_home = u'/home/yzygit/student-cms-web'
   if project_home not in sys.path:
       sys.path.insert(0, project_home)
   os.environ['ADMIN_PASSWORD'] = '你的线上密码'  # 不设置则默认 123456
   from app import app as application
   ```

6. 回到 Web 页面点 **Reload**，访问 https://yzygit.pythonanywhere.com

---

> 说明：本项目在开发过程中使用了 AI 辅助工具进行代码编写、讲解与调试；核心业务逻辑与功能设计由本人确认。
