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
cd frontend
npm ci
VITE_BASE_PATH=/for-test/ npm run build
cd ..
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
START_SCHEDULER=1
```

## 4. 启动服务

```bash
set -a
. ./.env
set +a
.venv/bin/gunicorn -w 1 -b 0.0.0.0:5050 wsgi:app
```

> 测试报告机器人使用应用内定时线程触发。建议使用 1 个 gunicorn worker；如果服务器暂时仍是旧的 2 worker 配置，代码会通过数据库日期锁避免同一份日报重复发送。

后端只需监听本机端口，前端静态资源由 Nginx 提供：

```text
http://服务器内网IP
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
ExecStart=/opt/ewll-bug/.venv/bin/gunicorn -w 1 -b 0.0.0.0:5050 wsgi:app
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

## 6. Nginx 前后端分流

以下配置让 Vue 路由回退到 `index.html`，并把 API、附件、静态资源及报告导出交给 Flask：

```nginx
server {
    listen 80;
    server_name _;

    root /opt/ewll-bug/frontend/dist;
    index index.html;

    location /api/ {
        proxy_pass http://127.0.0.1:5050;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location ~ ^/(attachments|static)/ {
        proxy_pass http://127.0.0.1:5050;
        proxy_set_header Host $host;
    }

    location = /reports/testing/export {
        proxy_pass http://127.0.0.1:5050;
        proxy_set_header Host $host;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

更新配置后先执行 `sudo nginx -t`，确认通过再 reload。

## 7. test 发布目录注意事项

test 机器如果使用 `/home/echooo/fed/ewll-bug-test/current` 作为当前发布目录，数据库和上传附件必须放在 `current` 外的 `shared` 目录，避免发布切换后读到新的空数据库或新的上传目录。可参考 `deploy/ewll-bug-test.env.example`：

```bash
DATABASE=/home/echooo/fed/ewll-bug-test/shared/data/bug_platform.db
UPLOAD_FOLDER=/home/echooo/fed/ewll-bug-test/shared/uploads
```

test 的 systemd 服务建议只使用 1 个 gunicorn worker：

```ini
ExecStart=/home/echooo/fed/ewll-bug-test/current/.venv/bin/gunicorn -w 1 -b 127.0.0.1:5051 wsgi:app
```

test 的 Nginx 必须把 `/for-test/assets/` 和 SPA 路由指向当前 release 的 `frontend/dist`，并仅把以下路径代理给 Gunicorn：

```text
/for-test/api/
/for-test/attachments/
/for-test/static/
/for-test/reports/testing/export
```

发布前检查 `frontend/dist/index.html` 中的资源地址以 `/for-test/assets/` 开头；否则页面会在子路径下加载失败。

如果历史数据已经落在 `current/data/bug_platform.db`，先停服务，再把数据库迁移到固定目录，最后重启服务：

```bash
sudo systemctl stop ewll-bug-test
mkdir -p /home/echooo/fed/ewll-bug-test/shared/data /home/echooo/fed/ewll-bug-test/shared/uploads
cp /home/echooo/fed/ewll-bug-test/current/data/bug_platform.db /home/echooo/fed/ewll-bug-test/shared/data/bug_platform.db
sudo systemctl daemon-reload
sudo systemctl restart ewll-bug-test
```

## 8. 必须备份的数据

定期备份：

```text
data/bug_platform.db
uploads/
```

不要把 `.env`、数据库、上传附件提交到 GitHub。
