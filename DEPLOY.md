# 公司内网部署说明

以下示例以 Linux 服务器部署到 `/opt/ewll-bug` 为例。

## 1. 拉取代码

```bash
cd /opt
git clone https://github.com/ewll-b/ewll-bug.git
cd ewll-bug
```

## 2. 安装依赖

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## 3. 配置运行环境

```bash
cp .env.example .env
```

编辑 `.env`，至少修改：

```bash
SECRET_KEY=替换成一串足够长的随机字符
DATABASE=/opt/ewll-bug/data/bug_platform.db
UPLOAD_FOLDER=/opt/ewll-bug/uploads
```

## 4. 启动服务

```bash
set -a
. ./.env
set +a
.venv/bin/gunicorn -w 2 -b 0.0.0.0:5050 wsgi:app
```

公司同一内网访问：

```text
http://服务器内网IP:5050
```

## 5. systemd 后台运行

创建 `/etc/systemd/system/ewll-bug.service`：

```ini
[Unit]
Description=EWLL Bug Platform
After=network.target

[Service]
WorkingDirectory=/opt/ewll-bug
EnvironmentFile=/opt/ewll-bug/.env
ExecStart=/opt/ewll-bug/.venv/bin/gunicorn -w 2 -b 0.0.0.0:5050 wsgi:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

启动：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ewll-bug
sudo systemctl status ewll-bug
```

## 6. 必须备份的数据

定期备份：

```text
data/bug_platform.db
uploads/
```

不要把 `.env`、数据库、上传附件提交到 GitHub。
