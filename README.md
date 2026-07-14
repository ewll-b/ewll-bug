# alvinsclubBUG管理平台

一个面向 100 人以内团队的轻量 Bug 管理平台，使用 `Python + Flask + SQLite` 构建，强调简洁、方便、开箱可用。

## 已实现能力

- 按项目管理 Bug
- 支持 `APP / WEB / Backend / AI` 模块分类
- 账号密码登录，内置管理员端
- 支持项目下拉切换，切换后页面数据联动更新
- 生命周期支持：`打开`、`处理中`、`已解决`、`待验证`、`已驳回`、`已关闭`
- 开发点击“已解决”后自动回测试待办并变为 `待验证`
- 测试点击“驳回”后自动回到对应开发待办
- Bug 编号按 `0001` 递增展示
- Bug 列表支持按创建人、当前处理人、状态、创建时间筛选
- 支持关联需求和测试用例
- 新增用例库，支持 Excel 上传并同步执行状态统计
- 新增需求页面
- 新增测试报告图表页，可导出图表报告
- 新增 Admin 管理端，可创建项目和账号角色
- 支持按项目配置飞书 / Lark 群机器人，新建 Bug 后自动推送到默认项目群或模块专属群
- 内置示例项目、成员和 Bug 数据

## 本地运行

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python app.py
```

本机打开浏览器访问 [http://127.0.0.1:5050](http://127.0.0.1:5050)

同一局域网内的其他人可以访问 `http://你的电脑IP:5050`，例如 `http://192.168.0.161:5050`。

首次进入会先到登录页，输入账号密码后进入平台。

示例账号：

- 管理员：`admin / admin123`
- 测试：`lit / 123456`
- 开发：`zhouyue / 123456`

## 目录结构

```text
app.py
templates/
static/
data/
uploads/
tests/
```

## 部署到公司内网

正式部署建议使用 `gunicorn` 运行：

```bash
cp .env.example .env
set -a
. ./.env
set +a
.venv/bin/gunicorn -w 2 -b 0.0.0.0:5050 wsgi:app
```

更完整的服务器部署、systemd 后台运行和备份说明见 [DEPLOY.md](DEPLOY.md)。

## 数据安全

以下本地文件不会提交到 GitHub：

- `.env`
- `data/*.db`
- `data.db`
- `uploads/`
- `.venv/`
- `__pycache__/`

正式使用时必须定期备份：

- `data/bug_platform.db`
- `uploads/`

## 适合的后续增强

- 增加评论 @ 人、更多群通知模板
- 增加 Excel / PDF 报告导出
- 接入真实组织架构与单点登录
