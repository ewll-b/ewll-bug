from __future__ import annotations

import io
import math
import os
import re
import sqlite3
import smtplib
import ssl
import threading
import time
import uuid
import base64
import hashlib
import hmac
import json
from contextlib import closing
from datetime import datetime
from email.message import EmailMessage
from html import escape
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/mpl")
os.environ.setdefault("XDG_CACHE_HOME", "/private/tmp")

import openpyxl
from flask import Flask, Response, flash, g, jsonify, redirect, render_template, request, send_file, session, url_for
from werkzeug.utils import secure_filename


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = BASE_DIR / "data" / "bug_platform.db"
DEFAULT_UPLOAD_FOLDER = BASE_DIR / "uploads"
PAGE_SIZE = 10
BUG_PAGE_SIZE = 20
CASE_PAGE_SIZE = 12

STATUS_OPTIONS = [
    ("open", "已打开"),
    ("in_progress", "处理中"),
    ("pending_verification", "待验证"),
    ("closed", "已关闭"),
    ("duplicate", "重复"),
    ("on_hold", "搁置"),
]
STATUS_LABELS = dict(STATUS_OPTIONS)
TODO_STATUS_CODES = ("open", "in_progress", "pending_verification")
BUG_SEVERITY_OPTIONS = ["最高", "高", "中", "低", "最低", "建议"]
MAIL_NOTIFY_SEVERITY = "最高"
BUG_PLATFORM_OPTIONS = ["Android", "iOS", "双端", "H5", "后端", "AI"]
BUG_NOTIFY_RULE_OPTIONS = [
    {"key": "APP", "label": "APP（Android / iOS / 双端）"},
    {"key": "H5", "label": "H5"},
    {"key": "WEB", "label": "WEB"},
    {"key": "Backend", "label": "后端"},
    {"key": "AI", "label": "AI"},
]
BUG_PLATFORM_NOTIFY_KEY_MAP = {
    "Android": "APP",
    "iOS": "APP",
    "双端": "APP",
    "H5": "H5",
    "WEB": "WEB",
    "后端": "Backend",
    "AI": "AI",
}
BUG_ATTACHMENT_SOURCE_FIELDS = {
    "title",
    "version",
    "environment",
    "description",
    "expected_result",
    "actual_result",
    "attachments",
}
BUG_INLINE_ATTACHMENT_FIELDS = (
    "title",
    "version",
    "environment",
    "description",
    "expected_result",
    "actual_result",
)
REPORT_PLATFORM_LABELS = {
    "iOS": "IOS",
}
BUG_PRIORITY_OPTIONS = BUG_SEVERITY_OPTIONS.copy()
BUG_PRIORITY_ICON_MAP = {
    "最高": "highest",
    "高": "high",
    "中": "medium",
    "低": "low",
    "最低": "lowest",
    "建议": "suggestion",
}
BUG_SEVERITY_FALLBACK_MAP = {
    "严重": "最高",
    "一般": "中",
    "建议": "建议",
}


def bug_notify_key_for_platform(platform: object) -> str:
    platform_text = str(platform or "").strip()
    return BUG_PLATFORM_NOTIFY_KEY_MAP.get(platform_text, platform_text)


def bug_notify_label_for_key(rule_key: object) -> str:
    rule_key_text = str(rule_key or "").strip()
    for rule_option in BUG_NOTIFY_RULE_OPTIONS:
        if rule_option["key"] == rule_key_text:
            return str(rule_option["label"])
    return rule_key_text


REQUIREMENT_STATUS_OPTIONS = [
    ("pending", "待评估"),
    ("in_progress", "进行中"),
    ("completed", "已完成"),
    ("on_hold", "已搁置"),
]
REQUIREMENT_STATUS_LABELS = dict(REQUIREMENT_STATUS_OPTIONS)
MAIL_SECURITY_OPTIONS = [
    ("tls", "STARTTLS"),
    ("ssl", "SSL/TLS"),
    ("none", "无加密"),
]
DEFAULT_MAIL_SETTINGS = {
    "enabled": False,
    "host": "",
    "port": "587",
    "security": "tls",
    "username": "",
    "password": "",
    "from_email": "",
    "sender_name": "Alvin's Club Bug Management Platform",
    "send_time": "10:05",
    "last_sent_at": "",
    "last_sent_date": "",
    "last_result": "",
}
DEFAULT_GROUP_REPORT_SETTINGS = {
    "enabled": False,
    "webhook_url": "",
    "secret": "",
    "send_time": "18:00",
    "project_id": "",
    "version": "",
    "base_url": "",
    "last_sent_at": "",
    "last_sent_date": "",
    "last_result": "",
}
CASE_STATUS_OPTIONS = ["未测", "通过", "失败", "受阻", "跳过"]
CASE_STATUS_COLORS = {
    "未测": "#d9d9d9",
    "通过": "#7bc67e",
    "失败": "#ef6f6c",
    "受阻": "#f6c85f",
    "跳过": "#68b5e8",
}
CASE_STATUS_CHART_LABELS = {
    "未测": "Not Run",
    "通过": "Pass",
    "失败": "Fail",
    "受阻": "Blocked",
    "跳过": "Skip",
}
PLATFORM_RESULT_OPTIONS = ["", "pass", "failed", "block", "skip"]

SVG_CHART_WIDTH = 680
SVG_CHART_HEIGHT = 320

SAMPLE_USERS = [
    ("李婷", "测试负责人", "tester"),
    ("周越", "APP 开发", "developer"),
    ("王昊", "WEB 开发", "developer"),
    ("赵航", "后端开发", "developer"),
    ("沈意", "AI 工程师", "developer"),
    ("陈默", "产品经理", "pm"),
    ("Admin", "系统管理员", "admin"),
]

ADMIN_ROLE_CODE = "admin"
ADMIN_ROLE_LABEL = "系统管理员"

ROLE_OPTIONS = [
    ("tester_engineer", "测试工程师"),
    ("app_developer", "APP开发"),
    ("h5_developer", "H5开发"),
    ("backend_developer", "后端开发"),
    ("ai_developer", "AI开发"),
    ("product", "产品"),
    ("designer", "设计"),
]

ROLE_LABELS = dict(ROLE_OPTIONS)
ACCOUNT_TYPE_OPTIONS = [
    ("member", "普通成员"),
    ("admin", "管理员"),
]
ACCOUNT_TYPE_LABELS = dict(ACCOUNT_TYPE_OPTIONS)

SAMPLE_CREDENTIALS = {
    "lit": "123456",
    "zhouyue": "123456",
    "wanghao": "123456",
    "zhaohang": "123456",
    "shenyi": "123456",
    "chenmo": "123456",
    "admin": "admin123",
}

SAMPLE_USER_PROFILES = [
    {
        "name": name,
        "role": role,
        "role_code": role_code,
        "account_type": "admin" if role_code == ADMIN_ROLE_CODE else "member",
        "username": username,
        "password": SAMPLE_CREDENTIALS[username],
        "email": f"{username}@alvinsclub.ai",
    }
    for (name, role, role_code), username in zip(SAMPLE_USERS, SAMPLE_CREDENTIALS.keys())
]

SAMPLE_PROJECTS = [
    ("零售增长平台", "增长业务相关项目"),
    ("智能客服系统", "AI 服务与管理后台"),
    ("商家工作台", "商家端 APP / WEB / API"),
]

SAMPLE_REQUIREMENTS = [
    ("商家工作台", "REQ-001", "首页升级改版"),
    ("商家工作台", "REQ-002", "退款链路容错优化"),
    ("智能客服系统", "REQ-003", "知识库检索准确率提升"),
]

SAMPLE_CASES = [
    {
        "project_name": "商家工作台",
        "folder_name": "测试用例",
        "doc_name": "2.6.0-首页优化测试用例",
        "case_no": "2.6.0-HOME-TC-001",
        "title": "首页 banner 点击跳转",
        "priority_level": "P0",
        "module_name": "首页推荐",
        "steps": "1. 打开首页\n2. 点击 banner 卡片",
        "expected_result": "正常跳转到活动页，页面数据完整展示。",
        "execute_status": "通过",
        "source_type": "在线文档",
        "ios_result": "pass",
        "android_result": "",
        "h5_result": "",
        "remark": "",
    },
    {
        "project_name": "商家工作台",
        "folder_name": "测试用例",
        "doc_name": "2.6.0-首页优化测试用例",
        "case_no": "2.6.0-HOME-TC-002",
        "title": "首页固定坑位顺序校验",
        "priority_level": "P0",
        "module_name": "首页推荐",
        "steps": "1. 打开首页\n2. 查看固定坑位顺序",
        "expected_result": "固定坑位顺序正确且位置稳定。",
        "execute_status": "失败",
        "source_type": "在线文档",
        "ios_result": "failed",
        "android_result": "",
        "h5_result": "",
        "remark": "iOS 展示顺序错误",
    },
    {
        "project_name": "商家工作台",
        "folder_name": "测试用例",
        "doc_name": "2.6.0-首页优化测试用例",
        "case_no": "2.6.0-HOME-TC-003",
        "title": "星模横滑推荐内容过滤",
        "priority_level": "P1",
        "module_name": "首页推荐",
        "steps": "1. 使用新账号进入首页\n2. 查看横滑推荐内容",
        "expected_result": "已关注星模和品牌内容不再重复推荐。",
        "execute_status": "受阻",
        "source_type": "在线文档",
        "ios_result": "block",
        "android_result": "",
        "h5_result": "",
        "remark": "测试账号画像未准备完成",
    },
    {
        "project_name": "零售增长平台",
        "folder_name": "测试组",
        "doc_name": "2.4.0_功能测试用例",
        "case_no": "2.4.0-ORDER-TC-001",
        "title": "订单列表按时间筛选",
        "priority_level": "P1",
        "module_name": "订单列表",
        "steps": "1. 进入订单列表\n2. 选择开始和结束日期",
        "expected_result": "列表仅展示时间范围内数据。",
        "execute_status": "跳过",
        "source_type": "在线文档",
        "ios_result": "skip",
        "android_result": "",
        "h5_result": "",
        "remark": "需求排期顺延",
    },
    {
        "project_name": "智能客服系统",
        "folder_name": "共享文档",
        "doc_name": "2.5.0_OOTD_AI试穿_测试用例",
        "case_no": "2.5.0-AI-TC-001",
        "title": "知识库召回最新政策",
        "priority_level": "P0",
        "module_name": "知识库检索",
        "steps": "1. 提问配送政策\n2. 查看命中答案",
        "expected_result": "优先命中最新知识库切片内容。",
        "execute_status": "通过",
        "source_type": "在线文档",
        "ios_result": "pass",
        "android_result": "pass",
        "h5_result": "",
        "remark": "",
    },
]

SAMPLE_BUGS = [
    {
        "title": "首页帖子无法 tryon",
        "project_name": "商家工作台",
        "version": "2.6.0",
        "module": "APP",
        "platform": "双端",
        "severity": "高",
        "priority": "高",
        "status": "open",
        "creator_name": "李婷",
        "assignee_name": "周越",
        "previous_assignee_name": "周越",
        "environment": "iOS 18.1 / 测试环境",
        "description": "进入首页后点击帖子 tryon 入口，无法进入试穿流程。",
        "expected_result": "应当正常进入试穿页面。",
        "actual_result": "点击无反应。",
        "resolution_note": "",
        "requirement_code": "REQ-001",
        "case_code": "TC-001",
    },
    {
        "title": "AI 问答推荐结果与知识库不一致",
        "project_name": "智能客服系统",
        "version": "2.5.0",
        "module": "AI",
        "platform": "AI",
        "severity": "低",
        "priority": "低",
        "status": "pending_verification",
        "creator_name": "李婷",
        "assignee_name": "沈意",
        "previous_assignee_name": "沈意",
        "environment": "RAG v2 / 测试知识库",
        "description": "用户问配送时效时，答案引用了过期政策。",
        "expected_result": "优先返回最新知识库答案。",
        "actual_result": "命中了过期切片内容。",
        "resolution_note": "已更新召回规则。",
        "requirement_code": "REQ-003",
        "case_code": "TC-005",
    },
    {
        "title": "后端退款接口偶发 500",
        "project_name": "商家工作台",
        "version": "2.6.0",
        "module": "Backend",
        "platform": "后端",
        "severity": "高",
        "priority": "高",
        "status": "pending_verification",
        "creator_name": "李婷",
        "assignee_name": "李婷",
        "previous_assignee_name": "赵航",
        "environment": "压测环境",
        "description": "批量退款时偶发空指针。",
        "expected_result": "接口稳定返回结果。",
        "actual_result": "部分请求返回 500。",
        "resolution_note": "后端已修复，待验证。",
        "requirement_code": "REQ-002",
        "case_code": "TC-002",
    },
]


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-change-me-before-deploy"),
        DATABASE=os.environ.get("DATABASE", str(DEFAULT_DB_PATH)),
        UPLOAD_FOLDER=os.environ.get("UPLOAD_FOLDER", str(DEFAULT_UPLOAD_FOLDER)),
        PAGE_SIZE=PAGE_SIZE,
        BUG_PAGE_SIZE=BUG_PAGE_SIZE,
        CASE_PAGE_SIZE=CASE_PAGE_SIZE,
    )

    if test_config:
        app.config.update(test_config)

    Path(app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)

    def current_time() -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def normalize_bug_severity_value(severity: object, priority: object = "") -> str:
        severity_text = str(severity or "").strip()
        priority_text = str(priority or "").strip()
        if severity_text in BUG_SEVERITY_OPTIONS:
            return severity_text
        if priority_text in BUG_SEVERITY_OPTIONS:
            return priority_text
        if severity_text in BUG_SEVERITY_FALLBACK_MAP:
            return BUG_SEVERITY_FALLBACK_MAP[severity_text]
        if priority_text in BUG_SEVERITY_FALLBACK_MAP:
            return BUG_SEVERITY_FALLBACK_MAP[priority_text]
        return severity_text or priority_text or "高"

    def get_bug_sync_token() -> str:
        token = str(session.get("bug_sync_token", "") or "").strip()
        if not token:
            token = str(time.time_ns())
            session["bug_sync_token"] = token
        return token

    def bump_bug_sync_token() -> str:
        token = str(time.time_ns())
        session["bug_sync_token"] = token
        return token

    def format_bug_no(value: object) -> str:
        if value is None:
            return ""
        text = str(value).strip()
        if not text:
            return ""
        if text.startswith("BUG-"):
            return text
        if text.isdigit():
            return text.zfill(3)
        return text

    def get_db() -> sqlite3.Connection:
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DATABASE"])
            g.db.row_factory = sqlite3.Row
        return g.db

    def build_asset_version() -> str:
        watched_files = [BASE_DIR / "app.py"]
        watched_files.extend(path for path in (BASE_DIR / "static").rglob("*") if path.is_file())
        watched_files.extend(path for path in (BASE_DIR / "templates").rglob("*") if path.is_file())
        latest_mtime = max(int(path.stat().st_mtime) for path in watched_files)
        return str(latest_mtime)

    @app.context_processor
    def inject_asset_version() -> dict[str, str]:
        return {
            "asset_version": build_asset_version(),
            "bug_sync_token": get_bug_sync_token(),
            "role_options": ROLE_OPTIONS,
            "role_labels": ROLE_LABELS,
            "account_type_options": ACCOUNT_TYPE_OPTIONS,
            "account_type_labels": ACCOUNT_TYPE_LABELS,
        }

    @app.after_request
    def add_no_cache_headers(response: Response) -> Response:
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    def init_db() -> None:
        schema = """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            role TEXT NOT NULL,
            role_code TEXT,
            account_type TEXT NOT NULL DEFAULT 'member',
            username TEXT,
            password TEXT,
            email TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            bug_notify_enabled INTEGER NOT NULL DEFAULT 0,
            bug_notify_webhook TEXT,
            bug_notify_secret TEXT,
            bug_notify_base_url TEXT,
            bug_notify_last_sent_at TEXT,
            bug_notify_last_result TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS project_bug_notify_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            module TEXT NOT NULL,
            enabled INTEGER NOT NULL DEFAULT 0,
            webhook_url TEXT,
            secret TEXT,
            last_sent_at TEXT,
            last_result TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(project_id, module)
        );

        CREATE TABLE IF NOT EXISTS requirements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            code TEXT NOT NULL,
            title TEXT NOT NULL,
            version TEXT,
            status TEXT,
            priority TEXT,
            description TEXT,
            acceptance_criteria TEXT,
            requirement_doc_link TEXT,
            design_doc_link TEXT,
            creator_id INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS test_cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            version TEXT,
            folder_name TEXT,
            doc_name TEXT,
            case_no TEXT NOT NULL,
            title TEXT NOT NULL,
            priority_level TEXT,
            module_name TEXT,
            steps TEXT,
            expected_result TEXT,
            actual_result TEXT,
            ios_result TEXT,
            android_result TEXT,
            h5_result TEXT,
            remark TEXT,
            executor TEXT,
            environment_info TEXT,
            device_info TEXT,
            network_info TEXT,
            source_type TEXT NOT NULL,
            doc_link TEXT,
            execute_status TEXT NOT NULL,
            creator_id INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS case_document_columns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            version TEXT,
            folder_name TEXT,
            doc_name TEXT,
            column_name TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            creator_id INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS case_document_cells (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            column_id INTEGER NOT NULL,
            case_id INTEGER NOT NULL,
            cell_value TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_case_document_cells_unique
        ON case_document_cells(column_id, case_id);

        CREATE INDEX IF NOT EXISTS idx_case_document_columns_document
        ON case_document_columns(project_id, version, folder_name, doc_name, sort_order, id);

        CREATE INDEX IF NOT EXISTS idx_case_document_cells_case
        ON case_document_cells(case_id);

        CREATE TABLE IF NOT EXISTS bugs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bug_no TEXT,
            title TEXT NOT NULL,
            project_id INTEGER NOT NULL,
            version TEXT,
            module TEXT NOT NULL,
            platform TEXT,
            severity TEXT NOT NULL,
            priority TEXT NOT NULL,
            status TEXT NOT NULL,
            assignee_id INTEGER NOT NULL,
            creator_id INTEGER,
            previous_assignee_id INTEGER,
            reporter TEXT,
            requirement_id INTEGER,
            case_id INTEGER,
            environment TEXT,
            description TEXT NOT NULL,
            expected_result TEXT,
            actual_result TEXT,
            resolution_note TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS bug_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bug_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            detail TEXT NOT NULL,
            operator_name TEXT NOT NULL,
            environment_snapshot TEXT,
            status_snapshot TEXT,
            assignee_snapshot TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS bug_attachments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bug_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            stored_name TEXT NOT NULL,
            content_type TEXT,
            source_field TEXT NOT NULL DEFAULT 'attachments',
            file_path TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS bug_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bug_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            parent_id INTEGER,
            author_name TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            actor_id INTEGER,
            bug_id INTEGER,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            link_path TEXT,
            is_read INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            read_at TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_notifications_user_read
        ON notifications(user_id, is_read, created_at DESC, id DESC);

        CREATE INDEX IF NOT EXISTS idx_notifications_bug
        ON notifications(bug_id);

        CREATE TABLE IF NOT EXISTS mail_settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            enabled INTEGER NOT NULL DEFAULT 0,
            host TEXT,
            port INTEGER,
            security TEXT,
            username TEXT,
            password TEXT,
            from_email TEXT,
            sender_name TEXT,
            send_time TEXT,
            last_sent_at TEXT,
            last_sent_date TEXT,
            last_result TEXT,
            report_notify_enabled INTEGER NOT NULL DEFAULT 0,
            report_notify_webhook TEXT,
            report_notify_secret TEXT,
            report_notify_send_time TEXT,
            report_notify_project_id INTEGER,
            report_notify_version TEXT,
            report_notify_base_url TEXT,
            report_notify_last_sent_at TEXT,
            report_notify_last_sent_date TEXT,
            report_notify_last_result TEXT
        );
        """

        with closing(sqlite3.connect(app.config["DATABASE"])) as db:
            db.executescript(schema)
            db.commit()

    def column_names(table_name: str) -> set[str]:
        rows = get_db().execute(f"PRAGMA table_info({table_name})").fetchall()
        return {row["name"] for row in rows}

    def run_migrations() -> None:
        db = get_db()
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS case_document_columns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                version TEXT,
                folder_name TEXT,
                doc_name TEXT,
                column_name TEXT NOT NULL,
                sort_order INTEGER NOT NULL DEFAULT 0,
                creator_id INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS case_document_cells (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                column_id INTEGER NOT NULL,
                case_id INTEGER NOT NULL,
                cell_value TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE UNIQUE INDEX IF NOT EXISTS idx_case_document_cells_unique
            ON case_document_cells(column_id, case_id);

            CREATE INDEX IF NOT EXISTS idx_case_document_columns_document
            ON case_document_columns(project_id, version, folder_name, doc_name, sort_order, id);

            CREATE INDEX IF NOT EXISTS idx_case_document_cells_case
            ON case_document_cells(case_id);

            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                actor_id INTEGER,
                bug_id INTEGER,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                link_path TEXT,
                is_read INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                read_at TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_notifications_user_read
            ON notifications(user_id, is_read, created_at DESC, id DESC);

            CREATE INDEX IF NOT EXISTS idx_notifications_bug
            ON notifications(bug_id);

            CREATE TABLE IF NOT EXISTS project_bug_notify_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                module TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 0,
                webhook_url TEXT,
                secret TEXT,
                last_sent_at TEXT,
                last_result TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(project_id, module)
            );

            CREATE INDEX IF NOT EXISTS idx_project_bug_notify_rules_project
            ON project_bug_notify_rules(project_id);
            """
        )
        for table, column_sqls in {
            "projects": [
                ("bug_notify_enabled", "ALTER TABLE projects ADD COLUMN bug_notify_enabled INTEGER NOT NULL DEFAULT 0"),
                ("bug_notify_webhook", "ALTER TABLE projects ADD COLUMN bug_notify_webhook TEXT"),
                ("bug_notify_secret", "ALTER TABLE projects ADD COLUMN bug_notify_secret TEXT"),
                ("bug_notify_base_url", "ALTER TABLE projects ADD COLUMN bug_notify_base_url TEXT"),
                ("bug_notify_last_sent_at", "ALTER TABLE projects ADD COLUMN bug_notify_last_sent_at TEXT"),
                ("bug_notify_last_result", "ALTER TABLE projects ADD COLUMN bug_notify_last_result TEXT"),
            ],
            "users": [
                ("role_code", "ALTER TABLE users ADD COLUMN role_code TEXT"),
                ("account_type", "ALTER TABLE users ADD COLUMN account_type TEXT NOT NULL DEFAULT 'member'"),
                ("username", "ALTER TABLE users ADD COLUMN username TEXT"),
                ("password", "ALTER TABLE users ADD COLUMN password TEXT"),
                ("email", "ALTER TABLE users ADD COLUMN email TEXT"),
            ],
            "mail_settings": [
                ("enabled", "ALTER TABLE mail_settings ADD COLUMN enabled INTEGER NOT NULL DEFAULT 0"),
                ("host", "ALTER TABLE mail_settings ADD COLUMN host TEXT"),
                ("port", "ALTER TABLE mail_settings ADD COLUMN port INTEGER"),
                ("security", "ALTER TABLE mail_settings ADD COLUMN security TEXT"),
                ("username", "ALTER TABLE mail_settings ADD COLUMN username TEXT"),
                ("password", "ALTER TABLE mail_settings ADD COLUMN password TEXT"),
                ("from_email", "ALTER TABLE mail_settings ADD COLUMN from_email TEXT"),
                ("sender_name", "ALTER TABLE mail_settings ADD COLUMN sender_name TEXT"),
                ("send_time", "ALTER TABLE mail_settings ADD COLUMN send_time TEXT"),
                ("last_sent_at", "ALTER TABLE mail_settings ADD COLUMN last_sent_at TEXT"),
                ("last_sent_date", "ALTER TABLE mail_settings ADD COLUMN last_sent_date TEXT"),
                ("last_result", "ALTER TABLE mail_settings ADD COLUMN last_result TEXT"),
                ("report_notify_enabled", "ALTER TABLE mail_settings ADD COLUMN report_notify_enabled INTEGER NOT NULL DEFAULT 0"),
                ("report_notify_webhook", "ALTER TABLE mail_settings ADD COLUMN report_notify_webhook TEXT"),
                ("report_notify_secret", "ALTER TABLE mail_settings ADD COLUMN report_notify_secret TEXT"),
                ("report_notify_send_time", "ALTER TABLE mail_settings ADD COLUMN report_notify_send_time TEXT"),
                ("report_notify_project_id", "ALTER TABLE mail_settings ADD COLUMN report_notify_project_id INTEGER"),
                ("report_notify_version", "ALTER TABLE mail_settings ADD COLUMN report_notify_version TEXT"),
                ("report_notify_base_url", "ALTER TABLE mail_settings ADD COLUMN report_notify_base_url TEXT"),
                ("report_notify_last_sent_at", "ALTER TABLE mail_settings ADD COLUMN report_notify_last_sent_at TEXT"),
                ("report_notify_last_sent_date", "ALTER TABLE mail_settings ADD COLUMN report_notify_last_sent_date TEXT"),
                ("report_notify_last_result", "ALTER TABLE mail_settings ADD COLUMN report_notify_last_result TEXT"),
            ],
            "test_cases": [
                ("version", "ALTER TABLE test_cases ADD COLUMN version TEXT"),
                ("folder_name", "ALTER TABLE test_cases ADD COLUMN folder_name TEXT"),
                ("doc_name", "ALTER TABLE test_cases ADD COLUMN doc_name TEXT"),
                ("priority_level", "ALTER TABLE test_cases ADD COLUMN priority_level TEXT"),
                ("module_name", "ALTER TABLE test_cases ADD COLUMN module_name TEXT"),
                ("steps", "ALTER TABLE test_cases ADD COLUMN steps TEXT"),
                ("expected_result", "ALTER TABLE test_cases ADD COLUMN expected_result TEXT"),
                ("actual_result", "ALTER TABLE test_cases ADD COLUMN actual_result TEXT"),
                ("ios_result", "ALTER TABLE test_cases ADD COLUMN ios_result TEXT"),
                ("android_result", "ALTER TABLE test_cases ADD COLUMN android_result TEXT"),
                ("h5_result", "ALTER TABLE test_cases ADD COLUMN h5_result TEXT"),
                ("remark", "ALTER TABLE test_cases ADD COLUMN remark TEXT"),
                ("executor", "ALTER TABLE test_cases ADD COLUMN executor TEXT"),
                ("environment_info", "ALTER TABLE test_cases ADD COLUMN environment_info TEXT"),
                ("device_info", "ALTER TABLE test_cases ADD COLUMN device_info TEXT"),
                ("network_info", "ALTER TABLE test_cases ADD COLUMN network_info TEXT"),
                ("creator_id", "ALTER TABLE test_cases ADD COLUMN creator_id INTEGER"),
            ],
            "bugs": [
                ("bug_no", "ALTER TABLE bugs ADD COLUMN bug_no TEXT"),
                ("version", "ALTER TABLE bugs ADD COLUMN version TEXT"),
                ("creator_id", "ALTER TABLE bugs ADD COLUMN creator_id INTEGER"),
                ("previous_assignee_id", "ALTER TABLE bugs ADD COLUMN previous_assignee_id INTEGER"),
                ("reporter", "ALTER TABLE bugs ADD COLUMN reporter TEXT"),
                ("requirement_id", "ALTER TABLE bugs ADD COLUMN requirement_id INTEGER"),
                ("case_id", "ALTER TABLE bugs ADD COLUMN case_id INTEGER"),
                ("platform", "ALTER TABLE bugs ADD COLUMN platform TEXT"),
            ],
            "bug_history": [
                ("environment_snapshot", "ALTER TABLE bug_history ADD COLUMN environment_snapshot TEXT"),
                ("status_snapshot", "ALTER TABLE bug_history ADD COLUMN status_snapshot TEXT"),
                ("assignee_snapshot", "ALTER TABLE bug_history ADD COLUMN assignee_snapshot TEXT"),
            ],
            "bug_comments": [
                ("parent_id", "ALTER TABLE bug_comments ADD COLUMN parent_id INTEGER"),
            ],
            "bug_attachments": [
                ("source_field", "ALTER TABLE bug_attachments ADD COLUMN source_field TEXT NOT NULL DEFAULT 'attachments'"),
            ],
            "requirements": [
                ("version", "ALTER TABLE requirements ADD COLUMN version TEXT"),
                ("status", "ALTER TABLE requirements ADD COLUMN status TEXT"),
                ("priority", "ALTER TABLE requirements ADD COLUMN priority TEXT"),
                ("description", "ALTER TABLE requirements ADD COLUMN description TEXT"),
                ("acceptance_criteria", "ALTER TABLE requirements ADD COLUMN acceptance_criteria TEXT"),
                ("requirement_doc_link", "ALTER TABLE requirements ADD COLUMN requirement_doc_link TEXT"),
                ("design_doc_link", "ALTER TABLE requirements ADD COLUMN design_doc_link TEXT"),
                ("creator_id", "ALTER TABLE requirements ADD COLUMN creator_id INTEGER"),
                ("updated_at", "ALTER TABLE requirements ADD COLUMN updated_at TEXT"),
            ],
        }.items():
            existing = column_names(table)
            for column_name, sql in column_sqls:
                if column_name not in existing:
                    db.execute(sql)
        mail_settings_count = db.execute("SELECT COUNT(*) AS count FROM mail_settings").fetchone()["count"]
        if not mail_settings_count:
            db.execute(
                """
                INSERT INTO mail_settings (
                    id, enabled, host, port, security, username, password,
                    from_email, sender_name, send_time, last_sent_at, last_sent_date, last_result,
                    report_notify_enabled, report_notify_webhook, report_notify_secret, report_notify_send_time,
                    report_notify_project_id, report_notify_version, report_notify_base_url,
                    report_notify_last_sent_at, report_notify_last_sent_date, report_notify_last_result
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    1,
                    1 if DEFAULT_MAIL_SETTINGS["enabled"] else 0,
                    DEFAULT_MAIL_SETTINGS["host"],
                    int(DEFAULT_MAIL_SETTINGS["port"]),
                    DEFAULT_MAIL_SETTINGS["security"],
                    DEFAULT_MAIL_SETTINGS["username"],
                    DEFAULT_MAIL_SETTINGS["password"],
                    DEFAULT_MAIL_SETTINGS["from_email"],
                    DEFAULT_MAIL_SETTINGS["sender_name"],
                    DEFAULT_MAIL_SETTINGS["send_time"],
                    DEFAULT_MAIL_SETTINGS["last_sent_at"],
                    DEFAULT_MAIL_SETTINGS["last_sent_date"],
                    DEFAULT_MAIL_SETTINGS["last_result"],
                    1 if DEFAULT_GROUP_REPORT_SETTINGS["enabled"] else 0,
                    DEFAULT_GROUP_REPORT_SETTINGS["webhook_url"],
                    DEFAULT_GROUP_REPORT_SETTINGS["secret"],
                    DEFAULT_GROUP_REPORT_SETTINGS["send_time"],
                    None,
                    DEFAULT_GROUP_REPORT_SETTINGS["version"],
                    DEFAULT_GROUP_REPORT_SETTINGS["base_url"],
                    DEFAULT_GROUP_REPORT_SETTINGS["last_sent_at"],
                    DEFAULT_GROUP_REPORT_SETTINGS["last_sent_date"],
                    DEFAULT_GROUP_REPORT_SETTINGS["last_result"],
                ),
            )
        if "version" in column_names("requirements"):
            db.execute(
                """
                UPDATE requirements
                SET version = CASE
                    WHEN code LIKE 'REQ-%' THEN substr(code, 5, instr(substr(code, 5), '-') - 1)
                    ELSE version
                END
                WHERE version IS NULL
                """
            )
        if "version" in column_names("test_cases"):
            db.execute(
                """
                UPDATE test_cases
                SET version = CASE
                    WHEN COALESCE(version, '') <> '' THEN version
                    WHEN instr(COALESCE(doc_name, ''), '-') > 0
                        AND substr(doc_name, 1, instr(doc_name, '-') - 1) LIKE '%.%'
                        THEN substr(doc_name, 1, instr(doc_name, '-') - 1)
                    WHEN instr(COALESCE(case_no, ''), '-') > 0
                        AND substr(case_no, 1, instr(case_no, '-') - 1) LIKE '%.%'
                        THEN substr(case_no, 1, instr(case_no, '-') - 1)
                    ELSE ''
                END
                WHERE COALESCE(version, '') = ''
                """
            )
        if "creator_id" in column_names("requirements"):
            db.execute("UPDATE requirements SET creator_id = 6 WHERE creator_id IS NULL")
        if "status" in column_names("requirements"):
            db.execute("UPDATE requirements SET status = 'pending' WHERE COALESCE(status, '') = ''")
        if "priority" in column_names("requirements"):
            db.execute("UPDATE requirements SET priority = '中' WHERE COALESCE(priority, '') = ''")
        if "description" in column_names("requirements"):
            db.execute("UPDATE requirements SET description = '' WHERE description IS NULL")
        if "acceptance_criteria" in column_names("requirements"):
            db.execute("UPDATE requirements SET acceptance_criteria = '' WHERE acceptance_criteria IS NULL")
        if "requirement_doc_link" in column_names("requirements"):
            db.execute("UPDATE requirements SET requirement_doc_link = '' WHERE requirement_doc_link IS NULL")
        if "design_doc_link" in column_names("requirements"):
            db.execute("UPDATE requirements SET design_doc_link = '' WHERE design_doc_link IS NULL")
        if "updated_at" in column_names("requirements"):
            db.execute("UPDATE requirements SET updated_at = created_at WHERE COALESCE(updated_at, '') = ''")
        if "creator_id" in column_names("test_cases"):
            db.execute("UPDATE test_cases SET creator_id = 7 WHERE creator_id IS NULL")
        if "severity" in column_names("bugs"):
            db.execute(
                """
                UPDATE bugs
                SET severity = CASE
                    WHEN COALESCE(priority, '') IN ('最高', '高', '中', '低', '最低', '建议') THEN priority
                    WHEN severity = '严重' THEN '最高'
                    WHEN severity = '一般' THEN '中'
                    WHEN severity = '建议' THEN '建议'
                    WHEN COALESCE(severity, '') = '' THEN '高'
                    ELSE severity
                END
                WHERE (
                    COALESCE(priority, '') IN ('最高', '高', '中', '低', '最低', '建议')
                    AND COALESCE(severity, '') <> COALESCE(priority, '')
                )
                OR COALESCE(severity, '') = ''
                OR severity IN ('严重', '一般')
                OR severity NOT IN ('最高', '高', '中', '低', '最低', '建议')
                """
            )
        if "status" in column_names("bugs"):
            db.execute("UPDATE bugs SET status = 'open' WHERE COALESCE(status, '') = ''")
            db.execute("UPDATE bugs SET status = 'pending_verification' WHERE status = 'resolved'")
            db.execute("UPDATE bugs SET status = 'in_progress' WHERE status = 'rejected'")
        if "priority" in column_names("bugs"):
            db.execute(
                """
                UPDATE bugs
                SET priority = COALESCE(NULLIF(severity, ''), '高')
                WHERE COALESCE(priority, '') <> COALESCE(NULLIF(severity, ''), '高')
                """
            )
        if "account_type" in column_names("users"):
            db.execute(
                """
                UPDATE users
                SET account_type = CASE
                    WHEN COALESCE(account_type, '') <> '' THEN account_type
                    WHEN COALESCE(role_code, '') = ? THEN 'admin'
                    ELSE 'member'
                END
                """,
                (ADMIN_ROLE_CODE,),
            )
        if "bug_no" in column_names("bugs"):
            bug_rows = db.execute(
                """
                SELECT id
                FROM bugs
                WHERE COALESCE(bug_no, '') = ''
                ORDER BY datetime(created_at) ASC, id ASC
                """
            ).fetchall()
            if bug_rows:
                current_max = 0
                existing_numbers = db.execute("SELECT bug_no FROM bugs WHERE COALESCE(bug_no, '') <> ''").fetchall()
                for row in existing_numbers:
                    bug_no_text = str(row["bug_no"] or "").strip()
                    if bug_no_text.isdigit():
                        current_max = max(current_max, int(bug_no_text))
                next_no = current_max + 1
                for row in bug_rows:
                    db.execute("UPDATE bugs SET bug_no = ? WHERE id = ?", (str(next_no).zfill(3), row["id"]))
                    next_no += 1
        if "platform" in column_names("bugs"):
            db.execute(
                """
                UPDATE bugs
                SET platform = CASE
                    WHEN module = 'AI' THEN 'AI'
                    WHEN module = 'Backend' THEN '后端'
                    WHEN module = 'H5' THEN 'H5'
                    WHEN module IN ('APP', 'WEB') THEN '双端'
                    ELSE COALESCE(platform, '')
                END
                WHERE COALESCE(platform, '') = ''
                """
            )
        bug_history_columns = column_names("bug_history")
        if "environment_snapshot" in bug_history_columns:
            db.execute(
                """
                UPDATE bug_history
                SET environment_snapshot = COALESCE(
                    (SELECT COALESCE(bugs.environment, '') FROM bugs WHERE bugs.id = bug_history.bug_id),
                    ''
                )
                WHERE COALESCE(environment_snapshot, '') = ''
                """
            )
        if "status_snapshot" in bug_history_columns:
            db.execute(
                """
                UPDATE bug_history
                SET status_snapshot = COALESCE(
                    (SELECT COALESCE(bugs.status, '') FROM bugs WHERE bugs.id = bug_history.bug_id),
                    ''
                )
                WHERE COALESCE(status_snapshot, '') = ''
                """
            )
            db.execute("UPDATE bug_history SET status_snapshot = 'open' WHERE action IN ('初始化', '创建缺陷')")
            db.execute("UPDATE bug_history SET status_snapshot = 'in_progress' WHERE action = '开始处理'")
            db.execute("UPDATE bug_history SET status_snapshot = 'pending_verification' WHERE action IN ('标记已解决', '提交待验证')")
            db.execute("UPDATE bug_history SET status_snapshot = 'in_progress' WHERE action IN ('驳回缺陷', '退回处理')")
            db.execute("UPDATE bug_history SET status_snapshot = 'closed' WHERE action = '关闭缺陷'")
            db.execute("UPDATE bug_history SET status_snapshot = 'pending_verification' WHERE status_snapshot = 'resolved'")
            db.execute("UPDATE bug_history SET status_snapshot = 'in_progress' WHERE status_snapshot = 'rejected'")
        if "assignee_snapshot" in bug_history_columns:
            db.execute(
                """
                UPDATE bug_history
                SET assignee_snapshot = COALESCE(
                    (
                        SELECT COALESCE(users.name, '')
                        FROM bugs
                        LEFT JOIN users ON bugs.assignee_id = users.id
                        WHERE bugs.id = bug_history.bug_id
                    ),
                    ''
                )
                WHERE COALESCE(assignee_snapshot, '') = ''
                """
            )
        db.commit()

    def fetch_project_by_name(name: str) -> sqlite3.Row | None:
        return get_db().execute("SELECT * FROM projects WHERE name = ?", (name,)).fetchone()

    def fetch_project(project_id: int) -> sqlite3.Row | None:
        return get_db().execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()

    def fetch_projects() -> list[sqlite3.Row]:
        return get_db().execute("SELECT * FROM projects ORDER BY id").fetchall()

    def fetch_project_bug_notify_rule(project_id: int, module: str) -> sqlite3.Row | None:
        return get_db().execute(
            """
            SELECT *
            FROM project_bug_notify_rules
            WHERE project_id = ? AND module = ?
            """,
            (project_id, module),
        ).fetchone()

    def fetch_project_bug_notify_rule_options(project_id: int) -> list[dict[str, object]]:
        rows = get_db().execute(
            """
            SELECT *
            FROM project_bug_notify_rules
            WHERE project_id = ?
            """,
            (project_id,),
        ).fetchall()
        by_module = {str(row["module"]): row for row in rows}
        rule_options: list[dict[str, object]] = []
        for rule_option in BUG_NOTIFY_RULE_OPTIONS:
            module = str(rule_option["key"])
            row = by_module.get(module)
            rule_options.append(
                {
                    "module": module,
                    "label": str(rule_option["label"]),
                    "enabled": bool(row["enabled"]) if row else False,
                    "webhook_url": str(row["webhook_url"] or "") if row else "",
                    "secret": str(row["secret"] or "") if row else "",
                    "last_sent_at": str(row["last_sent_at"] or "") if row else "",
                    "last_result": str(row["last_result"] or "") if row else "",
                }
            )
        return rule_options

    def fetch_users() -> list[sqlite3.Row]:
        return get_db().execute("SELECT * FROM users ORDER BY id").fetchall()

    def fetch_user(user_id: int) -> sqlite3.Row | None:
        return get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

    def fetch_mail_settings() -> dict[str, str]:
        row = get_db().execute("SELECT * FROM mail_settings WHERE id = 1").fetchone()
        if row is None:
            return DEFAULT_MAIL_SETTINGS.copy()
        settings = DEFAULT_MAIL_SETTINGS.copy()
        settings.update(
            {
                "enabled": bool(row["enabled"]),
                "host": row["host"] or "",
                "port": str(row["port"] or DEFAULT_MAIL_SETTINGS["port"]),
                "security": row["security"] or DEFAULT_MAIL_SETTINGS["security"],
                "username": row["username"] or "",
                "password": row["password"] or "",
                "from_email": row["from_email"] or "",
                "sender_name": row["sender_name"] or DEFAULT_MAIL_SETTINGS["sender_name"],
                "send_time": row["send_time"] or DEFAULT_MAIL_SETTINGS["send_time"],
                "last_sent_at": row["last_sent_at"] or "",
                "last_sent_date": row["last_sent_date"] or "",
                "last_result": row["last_result"] or "",
            }
        )
        return settings

    def fetch_group_report_settings() -> dict[str, str]:
        row = get_db().execute("SELECT * FROM mail_settings WHERE id = 1").fetchone()
        if row is None:
            return DEFAULT_GROUP_REPORT_SETTINGS.copy()
        settings = DEFAULT_GROUP_REPORT_SETTINGS.copy()
        settings.update(
            {
                "enabled": bool(row["report_notify_enabled"]),
                "webhook_url": row["report_notify_webhook"] or "",
                "secret": row["report_notify_secret"] or "",
                "send_time": row["report_notify_send_time"] or DEFAULT_GROUP_REPORT_SETTINGS["send_time"],
                "project_id": str(row["report_notify_project_id"] or ""),
                "version": row["report_notify_version"] or "",
                "base_url": row["report_notify_base_url"] or "",
                "last_sent_at": row["report_notify_last_sent_at"] or "",
                "last_sent_date": row["report_notify_last_sent_date"] or "",
                "last_result": row["report_notify_last_result"] or "",
            }
        )
        return settings

    def update_mail_settings(form) -> None:
        enabled = 1 if form.get("enabled") == "1" else 0
        host = form.get("host", "").strip()
        port_text = form.get("port", "").strip() or DEFAULT_MAIL_SETTINGS["port"]
        security = form.get("security", "").strip() or DEFAULT_MAIL_SETTINGS["security"]
        username = form.get("username", "").strip()
        password = form.get("password", "").strip()
        from_email = form.get("from_email", "").strip()
        sender_name = form.get("sender_name", "").strip() or DEFAULT_MAIL_SETTINGS["sender_name"]
        send_time = form.get("send_time", "").strip() or DEFAULT_MAIL_SETTINGS["send_time"]
        if security not in dict(MAIL_SECURITY_OPTIONS):
            raise ValueError("请选择有效的邮箱加密方式。")
        try:
            port = int(port_text)
        except ValueError as exc:
            raise ValueError("端口号格式不正确。") from exc
        if host and (not from_email or not username):
            raise ValueError("请至少填写 SMTP 主机、登录账号和发件邮箱。")
        if len(send_time) != 5 or ":" not in send_time:
            raise ValueError("发送时间格式不正确，请使用 HH:MM。")
        db = get_db()
        db.execute(
            """
            UPDATE mail_settings
            SET enabled = ?, host = ?, port = ?, security = ?, username = ?, password = ?,
                from_email = ?, sender_name = ?, send_time = ?
            WHERE id = 1
            """,
            (enabled, host, port, security, username, password, from_email, sender_name, send_time),
        )
        db.commit()

    def update_group_report_settings(form) -> None:
        enabled = 1 if form.get("enabled") == "1" else 0
        webhook_url = form.get("webhook_url", "").strip()
        secret = form.get("secret", "").strip()
        send_time = form.get("send_time", "").strip() or DEFAULT_GROUP_REPORT_SETTINGS["send_time"]
        project_id_text = form.get("project_id", "").strip()
        version = form.get("version", "").strip()
        base_url = form.get("base_url", "").strip()
        if webhook_url and not webhook_url.startswith(("https://", "http://")):
            raise ValueError("群机器人 Webhook 地址格式不正确。")
        if len(send_time) != 5 or ":" not in send_time:
            raise ValueError("发送时间格式不正确，请使用 HH:MM。")
        project_id = None
        if project_id_text:
            try:
                project_id = int(project_id_text)
            except ValueError as exc:
                raise ValueError("请选择有效项目。") from exc
            if fetch_project(project_id) is None:
                raise ValueError("所选项目不存在。")
        if enabled and not webhook_url:
            raise ValueError("开启群测试报告通知前，请先填写群机器人 Webhook。")
        db = get_db()
        db.execute(
            """
            UPDATE mail_settings
            SET report_notify_enabled = ?, report_notify_webhook = ?, report_notify_secret = ?,
                report_notify_send_time = ?, report_notify_project_id = ?, report_notify_version = ?,
                report_notify_base_url = ?
            WHERE id = 1
            """,
            (enabled, webhook_url, secret, send_time, project_id, version, base_url),
        )
        db.commit()

    def validate_project_bug_notify_settings(
        enabled: int,
        webhook_url: str,
        base_url: str = "",
        label: str = "新建 Bug 群通知",
    ) -> None:
        if webhook_url and not webhook_url.startswith(("https://", "http://")):
            raise ValueError(f"{label} Webhook 地址格式不正确。")
        if base_url and not base_url.startswith(("https://", "http://")):
            raise ValueError("平台访问地址格式不正确，请填写 http:// 或 https:// 开头的地址。")
        if enabled and not webhook_url:
            raise ValueError(f"开启{label}前，请先填写群机器人 Webhook。")

    def parse_project_bug_notify_rule_form(form) -> list[dict[str, object]]:
        rules: list[dict[str, object]] = []
        for rule_option in BUG_NOTIFY_RULE_OPTIONS:
            module = str(rule_option["key"])
            enabled = 1 if form.get(f"bug_notify_rule_enabled_{module}") == "1" else 0
            webhook_url = form.get(f"bug_notify_rule_webhook_{module}", "").strip()
            secret = form.get(f"bug_notify_rule_secret_{module}", "").strip()
            validate_project_bug_notify_settings(
                enabled=enabled,
                webhook_url=webhook_url,
                label=f"{rule_option['label']} 群通知",
            )
            rules.append(
                {
                    "module": module,
                    "enabled": enabled,
                    "webhook_url": webhook_url,
                    "secret": secret,
                }
            )
        return rules

    def save_project_bug_notify_rules(project_id: int, rules: list[dict[str, object]]) -> None:
        db = get_db()
        now_text = current_time()
        for rule in rules:
            module = str(rule["module"])
            existing = fetch_project_bug_notify_rule(project_id, module)
            if existing is None:
                db.execute(
                    """
                    INSERT INTO project_bug_notify_rules (
                        project_id, module, enabled, webhook_url, secret, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        project_id,
                        module,
                        int(rule["enabled"]),
                        str(rule["webhook_url"]),
                        str(rule["secret"]),
                        now_text,
                        now_text,
                    ),
                )
            else:
                db.execute(
                    """
                    UPDATE project_bug_notify_rules
                    SET enabled = ?, webhook_url = ?, secret = ?, updated_at = ?
                    WHERE project_id = ? AND module = ?
                    """,
                    (
                        int(rule["enabled"]),
                        str(rule["webhook_url"]),
                        str(rule["secret"]),
                        now_text,
                        project_id,
                        module,
                    ),
                )

    def resolve_user_role_from_form(form) -> tuple[str, str, str]:
        account_type = form.get("account_type", "member").strip() or "member"
        role_code = form.get("role_code", "").strip()
        if account_type == "admin" and not role_code:
            return account_type, ADMIN_ROLE_CODE, ADMIN_ROLE_LABEL
        if role_code == ADMIN_ROLE_CODE:
            return account_type, role_code, ADMIN_ROLE_LABEL
        role = ROLE_LABELS.get(role_code, "").strip()
        return account_type, role_code, role

    def update_mail_run_result(result_text: str, mark_daily_sent: bool = False) -> str:
        now_text = current_time()
        params: list[object] = [result_text]
        sql = "UPDATE mail_settings SET last_result = ?"
        if mark_daily_sent:
            sql += ", last_sent_at = ?, last_sent_date = ?"
            today_text = datetime.now().strftime("%Y-%m-%d")
            params.extend([now_text, today_text])
        sql += " WHERE id = 1"
        get_db().execute(sql, params)
        get_db().commit()
        return now_text

    def update_group_report_run_result(result_text: str, mark_daily_sent: bool = False) -> str:
        now_text = current_time()
        params: list[object] = [result_text]
        sql = "UPDATE mail_settings SET report_notify_last_result = ?"
        if mark_daily_sent:
            sql += ", report_notify_last_sent_at = ?, report_notify_last_sent_date = ?"
            today_text = datetime.now().strftime("%Y-%m-%d")
            params.extend([now_text, today_text])
        sql += " WHERE id = 1"
        get_db().execute(sql, params)
        get_db().commit()
        return now_text

    def fetch_user_todo_summary_rows(severity: str = "") -> list[sqlite3.Row]:
        db = get_db()
        join_parts = [
            "bugs.assignee_id = users.id",
            f"bugs.status IN ({','.join('?' for _ in TODO_STATUS_CODES)})",
        ]
        params: list[object] = list(TODO_STATUS_CODES)
        if severity:
            join_parts.append("COALESCE(bugs.severity, '') = ?")
            params.append(severity)
        return db.execute(
            f"""
            SELECT
                users.id,
                users.name,
                users.username,
                users.email,
                COUNT(bugs.id) AS todo_count
            FROM users
            LEFT JOIN bugs
                ON {' AND '.join(join_parts)}
            GROUP BY users.id, users.name, users.username, users.email
            ORDER BY users.id
            """,
            params,
        ).fetchall()

    def fetch_user_todo_items(user_id: int, limit: int = 5, severity: str = "") -> list[sqlite3.Row]:
        db = get_db()
        where_parts = [
            "bugs.assignee_id = ?",
            f"bugs.status IN ({','.join('?' for _ in TODO_STATUS_CODES)})",
        ]
        params: list[object] = [user_id, *TODO_STATUS_CODES]
        if severity:
            where_parts.append("COALESCE(bugs.severity, '') = ?")
            params.append(severity)
        params.append(limit)
        return db.execute(
            f"""
            SELECT
                bugs.id,
                bugs.bug_no,
                bugs.title,
                bugs.status,
                bugs.version,
                bugs.severity,
                projects.name AS project_name
            FROM bugs
            JOIN projects ON projects.id = bugs.project_id
            WHERE {' AND '.join(where_parts)}
            ORDER BY bugs.updated_at DESC, bugs.id DESC
            LIMIT ?
            """,
            params,
        ).fetchall()

    def smtp_client(mail_settings: dict[str, str]):
        host = mail_settings["host"]
        port = int(mail_settings["port"] or 0)
        security = mail_settings["security"]
        if security == "ssl":
            client = smtplib.SMTP_SSL(host, port, context=ssl.create_default_context(), timeout=30)
        else:
            client = smtplib.SMTP(host, port, timeout=30)
        client.ehlo()
        if security == "tls":
            client.starttls(context=ssl.create_default_context())
            client.ehlo()
        return client

    def build_todo_email_html(user: sqlite3.Row, todo_count: int, todo_items: list[sqlite3.Row]) -> str:
        items_html = "".join(
            f"""
            <tr>
                <td style="padding:10px 12px;border-bottom:1px solid #edf2f7;">{format_bug_no(item["bug_no"] or item["id"])}</td>
                <td style="padding:10px 12px;border-bottom:1px solid #edf2f7;">{escape(item["project_name"] or "-")}</td>
                <td style="padding:10px 12px;border-bottom:1px solid #edf2f7;">{escape(item["title"] or "-")}</td>
                <td style="padding:10px 12px;border-bottom:1px solid #edf2f7;">{escape(item["severity"] or "-")}</td>
                <td style="padding:10px 12px;border-bottom:1px solid #edf2f7;">{escape(STATUS_LABELS.get(item["status"], item["status"]))}</td>
            </tr>
            """
            for item in todo_items
        )
        if not items_html:
            items_html = """
            <tr>
                <td colspan="5" style="padding:14px 12px;color:#7b8798;text-align:center;">当前没有待办事项</td>
            </tr>
            """
        return f"""
        <div style="font-family:'PingFang SC','Microsoft YaHei',sans-serif;background:#f5f7fb;padding:28px;">
            <div style="max-width:720px;margin:0 auto;background:#ffffff;border-radius:18px;border:1px solid #e4ebf5;overflow:hidden;">
                <div style="padding:22px 24px;background:linear-gradient(135deg,#eef5ff 0%,#f9fbff 100%);border-bottom:1px solid #e4ebf5;">
                    <h2 style="margin:0;font-size:22px;color:#223349;">Alvin's Club Bug Management Platform 待办汇总</h2>
                    <p style="margin:8px 0 0;color:#617289;font-size:13px;">{escape(user['name'])}，以下是你当前的缺陷待办汇总。</p>
                </div>
                <div style="padding:22px 24px;">
                    <div style="display:inline-block;padding:10px 16px;border-radius:999px;background:#edf4ff;color:#2d6fe3;font-size:14px;font-weight:700;">
                        当前待办总数：{todo_count}
                    </div>
                    <table style="width:100%;margin-top:18px;border-collapse:collapse;font-size:13px;color:#2a3a50;">
                        <thead>
                            <tr style="background:#f8fbff;">
                                <th style="padding:10px 12px;text-align:left;border-bottom:1px solid #edf2f7;">编号</th>
                                <th style="padding:10px 12px;text-align:left;border-bottom:1px solid #edf2f7;">项目</th>
                                <th style="padding:10px 12px;text-align:left;border-bottom:1px solid #edf2f7;">标题</th>
                                <th style="padding:10px 12px;text-align:left;border-bottom:1px solid #edf2f7;">严重级别</th>
                                <th style="padding:10px 12px;text-align:left;border-bottom:1px solid #edf2f7;">状态</th>
                            </tr>
                        </thead>
                        <tbody>
                            {items_html}
                        </tbody>
                    </table>
                    <p style="margin:18px 0 0;color:#7b8798;font-size:12px;">邮件由系统在工作日 10:05 自动发送，生成时间：{current_time()}</p>
                </div>
            </div>
        </div>
        """

    def send_todo_summary_emails(
        force: bool = False,
        mark_daily_sent: bool = False,
        fail_when_empty: bool = True,
    ) -> tuple[int, int, str]:
        raise ValueError("邮件发送已取消，请使用项目新建 Bug 群通知。")
        mail_settings = fetch_mail_settings()
        if not mail_settings["enabled"] and not force:
            raise ValueError("待办邮件通知未开启。")
        required_values = [mail_settings["host"], mail_settings["port"], mail_settings["username"], mail_settings["from_email"]]
        if not all(required_values):
            raise ValueError("请先在 Admin 中完整配置 SMTP、发件邮箱和账号信息。")
        users = [row for row in fetch_user_todo_summary_rows() if (row["email"] or "").strip()]
        if not users:
            raise ValueError("当前没有可接收邮件的账号，请先为账号填写邮箱。")
        deliverable_users = [row for row in users if int(row["todo_count"] or 0) > 0]
        skipped_count = len(users) - len(deliverable_users)
        if not deliverable_users:
            result_text = "今日无待办，无需发送。"
            sent_at = update_mail_run_result(result_text, mark_daily_sent=mark_daily_sent)
            if fail_when_empty:
                raise ValueError("当前没有待办，无需发送。")
            return 0, skipped_count, sent_at

        sent_count = 0
        with smtp_client(mail_settings) as client:
            if mail_settings["username"]:
                client.login(mail_settings["username"], mail_settings["password"])
            for user in deliverable_users:
                todo_items = fetch_user_todo_items(int(user["id"]))
                todo_count = int(user["todo_count"] or 0)
                message = EmailMessage()
                message["Subject"] = f"[待办汇总] {user['name']} 当前有 {todo_count} 个待办"
                message["From"] = f"{mail_settings['sender_name']} <{mail_settings['from_email']}>"
                message["To"] = user["email"]
                plain_lines = [
                    f"{user['name']}，您好：",
                    f"当前待办总数：{todo_count}",
                    "",
                ]
                for item in todo_items:
                    plain_lines.append(
                        f"- {format_bug_no(item['bug_no'] or item['id'])} | {item['project_name']} | {item['title']} | {item['severity'] or '-'} | {STATUS_LABELS.get(item['status'], item['status'])}"
                    )
                message.set_content("\n".join(plain_lines))
                message.add_alternative(build_todo_email_html(user, todo_count, todo_items), subtype="html")
                client.send_message(message)
                sent_count += 1

        sent_at = update_mail_run_result(
            f"成功发送 {sent_count} 封，未发送 {skipped_count} 个无待办账号。",
            mark_daily_sent=mark_daily_sent,
        )
        return sent_count, skipped_count, sent_at

    def build_bug_detail_absolute_url(bug_id: int, base_url: str = "") -> str:
        base_url = (base_url.strip() or request.host_url or "").rstrip("/")
        return f"{base_url}{url_for('bug_detail', bug_id=bug_id)}" if base_url else url_for("bug_detail", bug_id=bug_id)

    def build_severe_bug_assignment_email_html(
        assignee_user: sqlite3.Row,
        bug: sqlite3.Row,
        trigger_reason: str,
        operator_name: str,
        bug_url: str,
    ) -> str:
        rows = [
            ("缺陷编号", format_bug_no(bug["bug_no"] or bug["id"])),
            ("项目", bug["project_name"] or "-"),
            ("标题", bug["title"] or "-"),
            ("当前状态", STATUS_LABELS.get(str(bug["status"] or ""), str(bug["status"] or "-"))),
            ("当前处理人", assignee_user["name"] or "-"),
            ("创建人", bug["creator_name"] or "-"),
            ("严重级别", bug["severity"] or "-"),
            ("触发动作", trigger_reason),
            ("操作人", operator_name or "-"),
        ]
        if bug["version"]:
            rows.insert(3, ("版本", bug["version"]))
        if bug["platform"]:
            rows.insert(4, ("端", bug["platform"]))
        if bug["environment"]:
            rows.append(("环境", bug["environment"]))
        rows_html = "".join(
            f"""
            <tr>
                <td style="padding:10px 12px;border-bottom:1px solid #edf2f7;width:92px;color:#66778e;">{escape(label)}</td>
                <td style="padding:10px 12px;border-bottom:1px solid #edf2f7;color:#243446;">{escape(str(value))}</td>
            </tr>
            """
            for label, value in rows
        )
        description_html = escape(str(bug["description"] or "-")).replace("\n", "<br>")
        return f"""
        <div style="font-family:'PingFang SC','Microsoft YaHei',sans-serif;background:#f5f7fb;padding:28px;">
            <div style="max-width:760px;margin:0 auto;background:#ffffff;border-radius:18px;border:1px solid #e4ebf5;overflow:hidden;">
                <div style="padding:22px 24px;background:linear-gradient(135deg,#fff4f2 0%,#fffaf8 100%);border-bottom:1px solid #f2ddd8;">
                    <h2 style="margin:0;font-size:22px;color:#223349;">Alvin's Club Bug Management Platform 严重 Bug 通知</h2>
                    <p style="margin:8px 0 0;color:#617289;font-size:13px;">{escape(assignee_user['name'])}，你有一条新的严重 Bug 待处理，请尽快关注。</p>
                </div>
                <div style="padding:22px 24px;">
                    <div style="display:inline-block;padding:10px 16px;border-radius:999px;background:#fff1ea;color:#c0563f;font-size:14px;font-weight:700;">
                        严重级别：{escape(str(bug['severity'] or '-'))}
                    </div>
                    <table style="width:100%;margin-top:18px;border-collapse:collapse;font-size:13px;">
                        <tbody>
                            {rows_html}
                        </tbody>
                    </table>
                    <div style="margin-top:18px;padding:14px 16px;border-radius:14px;background:#f8fafc;border:1px solid #e8edf5;">
                        <div style="font-size:12px;color:#6f7f92;margin-bottom:8px;">问题描述</div>
                        <div style="font-size:13px;color:#243446;line-height:1.8;">{description_html}</div>
                    </div>
                    <p style="margin:18px 0 0;font-size:13px;">
                        <a href="{escape(bug_url)}" style="color:#1f63d8;text-decoration:none;">点击查看缺陷详情</a>
                    </p>
                    <p style="margin:12px 0 0;color:#7b8798;font-size:12px;">邮件发送时间：{current_time()}</p>
                </div>
            </div>
        </div>
        """

    def send_single_severe_bug_notification(
        bug: sqlite3.Row | None,
        assignee_user_id: int | None,
        trigger_reason: str,
        operator_name: str,
    ) -> tuple[bool, str]:
        if bug is None:
            return False, "未找到对应 Bug。"
        if str(bug["severity"] or "") != MAIL_NOTIFY_SEVERITY:
            return False, "当前 Bug 非严重级别。"
        if str(bug["status"] or "") not in TODO_STATUS_CODES:
            return False, "当前状态无需发送严重 Bug 待办通知。"
        if not assignee_user_id:
            return False, "当前处理人为空，无法发送通知。"

        assignee_user = fetch_user(int(assignee_user_id))
        if assignee_user is None:
            return False, "当前处理人不存在。"
        recipient_email = str(assignee_user["email"] or "").strip()
        if not recipient_email:
            return False, f"{assignee_user['name']} 未配置邮箱。"

        mail_settings = fetch_mail_settings()
        if not mail_settings["enabled"]:
            return False, "待办邮件通知未开启。"
        required_values = [mail_settings["host"], mail_settings["port"], mail_settings["username"], mail_settings["from_email"]]
        if not all(required_values):
            return False, "SMTP、发件邮箱或邮箱账号配置不完整。"

        bug_url = build_bug_detail_absolute_url(int(bug["id"]))
        message = EmailMessage()
        message["Subject"] = f"[严重Bug通知] {format_bug_no(bug['bug_no'] or bug['id'])} 已进入你的待办"
        message["From"] = f"{mail_settings['sender_name']} <{mail_settings['from_email']}>"
        message["To"] = recipient_email
        plain_lines = [
            f"{assignee_user['name']}，您好：",
            f"你有一条严重 Bug 待办，请尽快处理。",
            f"缺陷编号：{format_bug_no(bug['bug_no'] or bug['id'])}",
            f"项目：{bug['project_name'] or '-'}",
            f"标题：{bug['title'] or '-'}",
            f"状态：{STATUS_LABELS.get(str(bug['status'] or ''), str(bug['status'] or '-'))}",
            f"触发动作：{trigger_reason}",
            f"操作人：{operator_name or '-'}",
            f"详情链接：{bug_url}",
        ]
        message.set_content("\n".join(plain_lines))
        message.add_alternative(
            build_severe_bug_assignment_email_html(
                assignee_user=assignee_user,
                bug=bug,
                trigger_reason=trigger_reason,
                operator_name=operator_name,
                bug_url=bug_url,
            ),
            subtype="html",
        )

        with smtp_client(mail_settings) as client:
            if mail_settings["username"]:
                client.login(mail_settings["username"], mail_settings["password"])
            client.send_message(message)

        update_mail_run_result(
            f"已即时通知 {assignee_user['name']}：{format_bug_no(bug['bug_no'] or bug['id'])} {trigger_reason}",
            mark_daily_sent=False,
        )
        return True, f"已通知 {assignee_user['name']}（{recipient_email}）。"

    def maybe_send_severe_bug_assignment_notification(
        bug_id: int,
        assignee_user_id: int | None,
        trigger_reason: str,
        operator_name: str,
    ) -> tuple[bool, str]:
        bug = fetch_bug(bug_id)
        return create_severe_bug_assignment_message(
            bug=bug,
            assignee_user_id=assignee_user_id,
            trigger_reason=trigger_reason,
            operator_name=operator_name,
        )

    def update_project_bug_notify_result(project_id: int, result_text: str, mark_sent: bool = False) -> str:
        now_text = current_time()
        params: list[object] = [result_text]
        sql = "UPDATE projects SET bug_notify_last_result = ?"
        if mark_sent:
            sql += ", bug_notify_last_sent_at = ?"
            params.append(now_text)
        sql += " WHERE id = ?"
        params.append(project_id)
        get_db().execute(sql, params)
        get_db().commit()
        return now_text

    def update_project_bug_notify_rule_result(
        project_id: int,
        module: str,
        result_text: str,
        mark_sent: bool = False,
    ) -> str:
        now_text = current_time()
        params: list[object] = [result_text]
        sql = "UPDATE project_bug_notify_rules SET last_result = ?"
        if mark_sent:
            sql += ", last_sent_at = ?"
            params.append(now_text)
        sql += " WHERE project_id = ? AND module = ?"
        params.extend([project_id, module])
        get_db().execute(sql, params)
        get_db().commit()
        return now_text

    def build_new_bug_group_message(bug: sqlite3.Row, operator_name: str, bug_url: str) -> str:
        lines = [
            "新建 Bug 通知",
            f"项目：{bug['project_name'] or '-'}",
            f"缺陷编号：{format_bug_no(bug['bug_no'] or bug['id'])}",
            f"标题：{bug['title'] or '-'}",
            f"严重级别：{bug['severity'] or '-'}",
            f"状态：{STATUS_LABELS.get(str(bug['status'] or ''), str(bug['status'] or '-'))}",
            f"当前处理人：{bug['assignee_name'] or '-'}",
            f"创建人：{bug['creator_name'] or operator_name or '-'}",
            f"版本：{bug['version'] or '-'}",
            f"端：{bug['platform'] or '-'}",
        ]
        if bug["environment"]:
            lines.append(f"环境：{bug['environment']}")
        lines.extend(
            [
                "",
                f"问题描述：{str(bug['description'] or '-').strip()}",
            ]
        )
        if bug_url:
            lines.extend(["", f"详情链接：{bug_url}"])
        lines.extend(["", f"发送时间：{current_time()}"])
        return "\n".join(lines)

    def maybe_send_new_bug_group_notification(
        bug_id: int,
        operator_name: str,
    ) -> tuple[bool, str]:
        bug = fetch_bug(bug_id)
        if bug is None:
            return False, "未找到对应 Bug。"
        project = fetch_project(int(bug["project_id"] or 0))
        if project is None:
            return False, "未找到对应项目。"
        bug_platform = str(bug["platform"] or "").strip()
        bug_notify_key = bug_notify_key_for_platform(bug_platform) or str(bug["module"] or "").strip()
        module_rule = fetch_project_bug_notify_rule(int(project["id"]), bug_notify_key) if bug_notify_key else None
        notify_target = "项目默认群"
        webhook_url = ""
        secret = ""
        is_module_rule = False
        if module_rule is not None and bool(module_rule["enabled"]):
            notify_target = f"{bug_notify_label_for_key(bug_notify_key)}群"
            webhook_url = str(module_rule["webhook_url"] or "").strip()
            secret = str(module_rule["secret"] or "").strip()
            is_module_rule = True
        elif bool(project["bug_notify_enabled"]):
            webhook_url = str(project["bug_notify_webhook"] or "").strip()
            secret = str(project["bug_notify_secret"] or "").strip()
        else:
            return False, "当前项目未开启新建 Bug 群通知。"
        if not webhook_url:
            result_text = f"新建 Bug 群通知未发送：{notify_target}未配置群机器人 Webhook。"
            if is_module_rule:
                update_project_bug_notify_rule_result(int(project["id"]), bug_notify_key, result_text)
            else:
                update_project_bug_notify_result(int(project["id"]), result_text)
            return False, result_text

        bug_url = build_bug_detail_absolute_url(int(bug["id"]), str(project["bug_notify_base_url"] or ""))
        message_text = build_new_bug_group_message(
            bug=bug,
            operator_name=operator_name,
            bug_url=bug_url,
        )
        try:
            send_group_report_message(
                webhook_url=webhook_url,
                message_text=message_text,
                secret=secret,
            )
        except Exception as exc:
            result_text = f"新建 Bug 群通知发送失败：{exc}"
            if is_module_rule:
                update_project_bug_notify_rule_result(int(project["id"]), bug_notify_key, result_text)
            else:
                update_project_bug_notify_result(int(project["id"]), result_text)
            return False, result_text

        result_text = f"新建 Bug 群通知已发送到{notify_target}：{format_bug_no(bug['bug_no'] or bug['id'])} {bug['title'] or ''}".strip()
        if is_module_rule:
            sent_at = update_project_bug_notify_rule_result(int(project["id"]), bug_notify_key, result_text, mark_sent=True)
        else:
            sent_at = update_project_bug_notify_result(int(project["id"]), result_text, mark_sent=True)
        return True, f"已发送到{notify_target}（{sent_at}）。"

    def build_group_report_message(
        project: sqlite3.Row,
        version: str,
        summary: dict,
        case_total: int,
        distribution: list[dict],
        risk_bugs: list[sqlite3.Row],
        generated_at: str,
        open_bug_platform_counts: list[dict[str, object]] | None = None,
        base_url: str = "",
        manual_note: str = "",
    ) -> str:
        not_run_count = next((item["count"] for item in distribution if item["status"] == "未测"), 0)
        executed_count = max(case_total - not_run_count, 0)
        progress_percent = "0%" if case_total <= 0 else f"{(executed_count / case_total) * 100:.0f}%"
        fixed_bug_count = int(summary["verification_count"]) + int(summary["closed_count"])
        reopened_or_open_count = int(summary["active_count"])
        project_label = project["name"] if not version else f"{project['name']}{version}"
        normalized_manual_note = "\n".join(
            line.strip() for line in str(manual_note or "").splitlines() if line.strip()
        )
        open_bug_platform_counts = open_bug_platform_counts or []
        lines = [
            f"测试项目：{project_label}",
            f"• 整体测试进度：{progress_percent}",
            f"• 用例执行进度：已测 {executed_count} / 总用例 {case_total}",
            "• 缺陷情况",
            f"• 发现 Bug 数：{summary['total']}",
            f"• 修复 Bug 数：{fixed_bug_count}",
            f"• 已回归验证：{summary['closed_count']}",
            f"• 还打开 Bug 数：{reopened_or_open_count}",
        ]
        for item in open_bug_platform_counts:
            lines.append(f"  {item['label']}：{item['count']}")
        lines.append("• 今日风险/备注：")
        if normalized_manual_note:
            lines.extend(normalized_manual_note.splitlines())
        return "\n".join(lines)

    def build_group_report_payload(message_text: str, secret: str = "") -> bytes:
        payload: dict[str, object] = {
            "msg_type": "text",
            "content": {
                "text": message_text,
            },
        }
        if secret:
            timestamp = str(int(time.time()))
            string_to_sign = f"{timestamp}\n{secret}"
            sign = base64.b64encode(
                hmac.new(string_to_sign.encode("utf-8"), digestmod=hashlib.sha256).digest()
            ).decode("utf-8")
            payload["timestamp"] = timestamp
            payload["sign"] = sign
        return json.dumps(payload, ensure_ascii=False).encode("utf-8")

    def send_group_report_message(
        webhook_url: str,
        message_text: str,
        secret: str = "",
    ) -> dict[str, object]:
        request_body = build_group_report_payload(message_text, secret=secret)
        http_request = urllib_request.Request(
            webhook_url,
            data=request_body,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Content-Length": str(len(request_body)),
            },
            method="POST",
        )
        try:
            with urllib_request.urlopen(http_request, timeout=20) as response:
                raw_body = response.read().decode("utf-8", errors="replace")
        except urllib_error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise ValueError(f"群机器人请求失败：HTTP {exc.code} {detail}") from exc
        except urllib_error.URLError as exc:
            raise ValueError(f"群机器人请求失败：{exc.reason}") from exc
        try:
            payload = json.loads(raw_body or "{}")
        except json.JSONDecodeError:
            return {"ok": True, "raw": raw_body}
        status_code = payload.get("code", payload.get("StatusCode"))
        status_message = payload.get("msg") or payload.get("StatusMessage") or payload
        if status_code not in (None, 0):
            raise ValueError(f"群机器人发送失败：{status_message}")
        return payload

    def send_testing_report_to_group(
        force: bool = False,
        mark_daily_sent: bool = False,
        manual_note: str = "",
    ) -> tuple[str, str, str]:
        settings = fetch_group_report_settings()
        if not settings["enabled"] and not force:
            raise ValueError("群测试报告通知未开启。")
        webhook_url = settings["webhook_url"].strip()
        if not webhook_url:
            raise ValueError("请先配置群机器人 Webhook。")
        project_id_text = settings["project_id"].strip()
        if not project_id_text:
            raise ValueError("请先选择要发送测试报告的项目。")
        try:
            project_id = int(project_id_text)
        except ValueError as exc:
            raise ValueError("群测试报告通知中的项目配置无效。") from exc
        project = fetch_project(project_id)
        if project is None:
            raise ValueError("所选项目不存在。")
        version = settings["version"].strip()
        summary = fetch_summary(version=version, project_id=project_id)
        case_total = count_test_cases(version=version, project_id=project_id)
        distribution = execution_distribution(project_id=project_id, version=version)
        risk_bugs = fetch_report_risk_bugs(project_id=project_id, version=version)
        open_bug_platform_counts = fetch_open_bug_counts_by_platform(project_id=project_id, version=version)
        message_text = build_group_report_message(
            project=project,
            version=version,
            summary=summary,
            case_total=case_total,
            distribution=distribution,
            risk_bugs=risk_bugs,
            generated_at=current_time(),
            open_bug_platform_counts=open_bug_platform_counts,
            base_url=settings["base_url"].strip(),
            manual_note=manual_note,
        )
        send_group_report_message(
            webhook_url=webhook_url,
            message_text=message_text,
            secret=settings["secret"].strip(),
        )
        note_suffix = "（含手动备注）" if str(manual_note or "").strip() else ""
        sent_at = update_group_report_run_result(
            f"测试报告已发送到群：{project['name']} / {version or '全部版本'}{note_suffix}",
            mark_daily_sent=mark_daily_sent,
        )
        return project["name"], version or "全部版本", sent_at

    def can_manage_bug(bug: sqlite3.Row | None) -> bool:
        return bug is not None and g.current_user is not None and (
            is_admin() or int(bug["creator_id"] or 0) == int(g.current_user["id"])
        )

    def can_edit_bug_platform(bug: sqlite3.Row | None) -> bool:
        return bug is not None and g.current_user is not None and (
            is_admin()
            or int(bug["creator_id"] or 0) == int(g.current_user["id"])
            or int(bug["assignee_id"] or 0) == int(g.current_user["id"])
        )

    def can_manage_bug_comment(comment: sqlite3.Row | None) -> bool:
        return comment is not None and g.current_user is not None and (
            is_admin() or int(comment["user_id"] or 0) == int(g.current_user["id"])
        )

    def can_manage_requirement(requirement: sqlite3.Row | None) -> bool:
        return requirement is not None and g.current_user is not None and (
            is_admin() or int(requirement["creator_id"] or 0) == int(g.current_user["id"])
        )

    def can_manage_case_document(document: sqlite3.Row | None) -> bool:
        return document is not None and g.current_user is not None and (
            is_admin() or int(document["creator_id"] or 0) == int(g.current_user["id"])
        )

    def can_edit_case_execution(document: sqlite3.Row | None) -> bool:
        return document is not None and g.current_user is not None

    def project_usage_count(project_id: int) -> int:
        db = get_db()
        bug_count = int(db.execute("SELECT COUNT(*) AS count FROM bugs WHERE project_id = ?", (project_id,)).fetchone()["count"])
        requirement_count = int(db.execute("SELECT COUNT(*) AS count FROM requirements WHERE project_id = ?", (project_id,)).fetchone()["count"])
        case_count = int(db.execute("SELECT COUNT(*) AS count FROM test_cases WHERE project_id = ?", (project_id,)).fetchone()["count"])
        return bug_count + requirement_count + case_count

    def user_usage_count(user_id: int) -> int:
        db = get_db()
        assignee_count = int(db.execute("SELECT COUNT(*) AS count FROM bugs WHERE assignee_id = ?", (user_id,)).fetchone()["count"])
        creator_count = int(db.execute("SELECT COUNT(*) AS count FROM bugs WHERE creator_id = ?", (user_id,)).fetchone()["count"])
        previous_count = int(db.execute("SELECT COUNT(*) AS count FROM bugs WHERE previous_assignee_id = ?", (user_id,)).fetchone()["count"])
        return assignee_count + creator_count + previous_count

    def delete_project_with_related_data(project_id: int) -> dict[str, int]:
        db = get_db()
        bug_rows = db.execute("SELECT id FROM bugs WHERE project_id = ?", (project_id,)).fetchall()
        bug_ids = [int(row["id"]) for row in bug_rows]
        case_rows = db.execute("SELECT id FROM test_cases WHERE project_id = ?", (project_id,)).fetchall()
        case_ids = [int(row["id"]) for row in case_rows]
        attachment_paths: list[str] = []
        deleted_attachments = 0
        deleted_histories = 0
        deleted_bugs = 0
        if bug_ids:
            placeholders = ",".join("?" for _ in bug_ids)
            attachment_paths = [
                row["file_path"]
                for row in db.execute(
                    f"SELECT file_path FROM bug_attachments WHERE bug_id IN ({placeholders})",
                    bug_ids,
                ).fetchall()
            ]
            deleted_attachments = int(
                db.execute(f"DELETE FROM bug_attachments WHERE bug_id IN ({placeholders})", bug_ids).rowcount or 0
            )
            deleted_histories = int(
                db.execute(f"DELETE FROM bug_history WHERE bug_id IN ({placeholders})", bug_ids).rowcount or 0
            )
            db.execute(f"DELETE FROM bug_comments WHERE bug_id IN ({placeholders})", bug_ids)
            deleted_bugs = int(db.execute("DELETE FROM bugs WHERE project_id = ?", (project_id,)).rowcount or 0)
        if case_ids:
            case_placeholders = ",".join("?" for _ in case_ids)
            db.execute(f"DELETE FROM case_document_cells WHERE case_id IN ({case_placeholders})", case_ids)
        db.execute("DELETE FROM case_document_columns WHERE project_id = ?", (project_id,))
        db.execute("DELETE FROM project_bug_notify_rules WHERE project_id = ?", (project_id,))
        deleted_requirements = int(db.execute("DELETE FROM requirements WHERE project_id = ?", (project_id,)).rowcount or 0)
        deleted_cases = int(db.execute("DELETE FROM test_cases WHERE project_id = ?", (project_id,)).rowcount or 0)
        deleted_projects = int(db.execute("DELETE FROM projects WHERE id = ?", (project_id,)).rowcount or 0)
        db.commit()
        for file_path in attachment_paths:
            try:
                attachment_file = Path(file_path)
                if attachment_file.exists():
                    attachment_file.unlink()
            except OSError:
                pass
        return {
            "projects": deleted_projects,
            "bugs": deleted_bugs,
            "requirements": deleted_requirements,
            "cases": deleted_cases,
            "attachments": deleted_attachments,
            "histories": deleted_histories,
        }

    def fetch_user_by_credentials(username: str, password: str) -> sqlite3.Row | None:
        return get_db().execute(
            "SELECT * FROM users WHERE username = ? AND password = ?",
            (username, password),
        ).fetchone()

    scheduler_started = {"value": False}

    def due_for_daily_mail(now: datetime, mail_settings: dict[str, str]) -> bool:
        if not mail_settings["enabled"]:
            return False
        send_time = mail_settings["send_time"] or DEFAULT_MAIL_SETTINGS["send_time"]
        if len(send_time) != 5 or ":" not in send_time:
            return False
        if now.weekday() >= 5:
            return False
        last_sent_date = mail_settings["last_sent_date"] or ""
        return now.strftime("%H:%M") == send_time and last_sent_date != now.strftime("%Y-%m-%d")

    def due_for_daily_group_report(now: datetime, settings: dict[str, str]) -> bool:
        if not settings["enabled"]:
            return False
        send_time = settings["send_time"] or DEFAULT_GROUP_REPORT_SETTINGS["send_time"]
        if len(send_time) != 5 or ":" not in send_time:
            return False
        last_sent_date = settings["last_sent_date"] or ""
        return now.strftime("%H:%M") == send_time and last_sent_date != now.strftime("%Y-%m-%d")

    def start_mail_scheduler() -> None:
        if scheduler_started["value"]:
            return
        scheduler_started["value"] = True

        def scheduler_loop() -> None:
            while True:
                try:
                    with app.app_context():
                        now = datetime.now()
                        mail_settings = fetch_mail_settings()
                        if due_for_daily_mail(now, mail_settings):
                            try:
                                send_todo_summary_emails(force=False, mark_daily_sent=True, fail_when_empty=False)
                            except Exception as exc:
                                get_db().execute(
                                    "UPDATE mail_settings SET last_result = ? WHERE id = 1",
                                    (f"定时发送失败：{exc}",),
                                )
                                get_db().commit()
                        group_report_settings = fetch_group_report_settings()
                        if due_for_daily_group_report(now, group_report_settings):
                            try:
                                send_testing_report_to_group(force=False, mark_daily_sent=True)
                            except Exception as exc:
                                update_group_report_run_result(f"群测试报告发送失败：{exc}", mark_daily_sent=False)
                except Exception:
                    pass
                time.sleep(30)

        thread = threading.Thread(target=scheduler_loop, name="todo-mail-scheduler", daemon=True)
        thread.start()

    def admin_redirect_target() -> str:
        next_url = request.form.get("next", "").strip()
        if next_url.startswith("/"):
            return next_url
        return url_for("admin_center")

    def local_back_url(default_url: str) -> str:
        next_url = request.values.get("next", "").strip()
        if next_url.startswith("/"):
            return next_url
        referrer = (request.referrer or "").strip()
        if not referrer:
            return default_url
        parsed = urllib_parse.urlparse(referrer)
        if parsed.netloc not in {"", request.host}:
            return default_url
        candidate = parsed.path or default_url
        if parsed.query:
            candidate = f"{candidate}?{parsed.query}"
        return candidate if candidate.startswith("/") else default_url

    def require_admin_access() -> Response | None:
        if not is_admin():
            flash("仅管理员可访问。", "error")
            return redirect(url_for("bug_list"))
        return None

    def admin_dashboard_cards() -> list[dict[str, str | int]]:
        group_report_settings = fetch_group_report_settings()
        return [
            {
                "title": "项目管理",
                "desc": "创建项目、修改项目信息，并配置新建 Bug 群通知。",
                "count_label": "项目数",
                "count": len(fetch_projects()),
                "href": url_for("admin_projects_page"),
            },
            {
                "title": "账号管理",
                "desc": "创建账号、分配角色、维护登录信息与邮箱配置。",
                "count_label": "账号数",
                "count": len(fetch_users()),
                "href": url_for("admin_users_page"),
            },
            {
                "title": "群测试报告通知",
                "desc": "配置飞书群机器人，每日自动把测试报告推送到群里。",
                "count_label": "通知状态",
                "count": "已开启" if group_report_settings["enabled"] else "未开启",
                "href": url_for("admin_report_notify_page"),
            },
        ]

    def fetch_requirement_by_code(code: str) -> sqlite3.Row | None:
        return get_db().execute("SELECT * FROM requirements WHERE code = ?", (code,)).fetchone()

    def fetch_case_by_no(case_no: str) -> sqlite3.Row | None:
        return get_db().execute("SELECT * FROM test_cases WHERE case_no = ?", (case_no,)).fetchone()

    def fetch_case(case_id: int) -> sqlite3.Row | None:
        return get_db().execute("SELECT * FROM test_cases WHERE id = ?", (case_id,)).fetchone()

    def build_bug_form_prefill_from_case(case_item: sqlite3.Row | None) -> dict:
        if case_item is None:
            return {}
        case_title = str(case_item["title"] or "").strip()
        case_no = str(case_item["case_no"] or "").strip()
        title = case_title or case_no
        if case_no and case_title:
            title = f"{case_no} {case_title}"
        return {
            "title": title,
            "version": str(case_item["version"] or "").strip(),
            "module": "APP",
            "platform": "",
            "severity": "高",
            "priority": "高",
            "assignee_id": "",
            "requirement_id": "",
            "case_id": str(case_item["id"]),
            "environment": str(case_item["environment_info"] or "").strip(),
            "description": str(case_item["steps"] or "").strip(),
            "expected_result": str(case_item["expected_result"] or "").strip(),
            "actual_result": "",
        }

    def build_bug_form_prefill_from_request(case_item: sqlite3.Row | None = None) -> dict:
        form_values = build_bug_form_prefill_from_case(case_item)
        if not form_values.get("version"):
            selected_version = request.args.get("version", "").strip()
            if selected_version:
                form_values["version"] = selected_version
        return form_values

    def find_user_id(db: sqlite3.Connection, user_name: str) -> int:
        row = db.execute("SELECT id FROM users WHERE name = ?", (user_name,)).fetchone()
        if not row:
            raise ValueError(f"用户不存在: {user_name}")
        return row["id"]

    def find_project_id(db: sqlite3.Connection, project_name: str) -> int:
        row = db.execute("SELECT id FROM projects WHERE name = ?", (project_name,)).fetchone()
        if not row:
            raise ValueError(f"项目不存在: {project_name}")
        return row["id"]

    def insert_bug(
        db: sqlite3.Connection,
        title: str,
        project_id: int,
        version: str,
        module: str,
        platform: str,
        severity: str,
        priority: str,
        status: str,
        assignee_id: int,
        creator_id: int,
        previous_assignee_id: int | None,
        requirement_id: int | None,
        case_id: int | None,
        environment: str,
        description: str,
        expected_result: str,
        actual_result: str,
        resolution_note: str,
    ) -> int:
        now = current_time()
        creator_name = db.execute("SELECT name FROM users WHERE id = ?", (creator_id,)).fetchone()["name"]
        max_bug_no_row = db.execute(
            """
            SELECT MAX(CAST(bug_no AS INTEGER)) AS max_bug_no
            FROM bugs
            WHERE COALESCE(bug_no, '') <> '' AND bug_no GLOB '[0-9]*'
            """
        ).fetchone()
        next_bug_no = str(int(max_bug_no_row["max_bug_no"] or 0) + 1).zfill(3)
        cursor = db.execute(
            """
            INSERT INTO bugs (
                bug_no, title, project_id, version, module, platform, severity, priority, status, assignee_id,
                creator_id, previous_assignee_id, reporter, requirement_id, case_id,
                environment, description, expected_result, actual_result, resolution_note,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                next_bug_no,
                title,
                project_id,
                version,
                module,
                platform,
                severity,
                priority,
                status,
                assignee_id,
                creator_id,
                previous_assignee_id,
                creator_name,
                requirement_id,
                case_id,
                environment,
                description,
                expected_result,
                actual_result,
                resolution_note,
                now,
                now,
            ),
        )
        return int(cursor.lastrowid)

    def add_history(
        db: sqlite3.Connection,
        bug_id: int,
        action: str,
        detail: str,
        operator_name: str,
        environment_snapshot: str = "",
        status_snapshot: str = "",
        assignee_snapshot: str = "",
    ) -> None:
        db.execute(
            """
            INSERT INTO bug_history (
                bug_id, action, detail, operator_name, environment_snapshot,
                status_snapshot, assignee_snapshot, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                bug_id,
                action,
                detail,
                operator_name,
                environment_snapshot,
                status_snapshot,
                assignee_snapshot,
                current_time(),
            ),
        )

    def normalize_attachment_source(source: object) -> str:
        source_text = str(source or "").strip()
        if source_text in BUG_ATTACHMENT_SOURCE_FIELDS:
            return source_text
        return "attachments"

    def save_bug_attachments(db: sqlite3.Connection, bug_id: int, files: list, source_fields: list[str] | None = None) -> list[str]:
        upload_dir = Path(app.config["UPLOAD_FOLDER"])
        saved_names: list[str] = []
        source_fields = source_fields or []
        for index, file in enumerate(files):
            if file is None or not file.filename:
                continue
            source_field = normalize_attachment_source(source_fields[index] if index < len(source_fields) else "")
            original_name = secure_filename(file.filename) or f"attachment-{uuid.uuid4().hex}"
            stored_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex}{Path(original_name).suffix}"
            destination = upload_dir / stored_name
            file.save(destination)
            db.execute(
                """
                INSERT INTO bug_attachments (bug_id, filename, stored_name, content_type, source_field, file_path, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    bug_id,
                    file.filename,
                    stored_name,
                    file.mimetype or "application/octet-stream",
                    source_field,
                    str(destination),
                    current_time(),
                ),
            )
            saved_names.append(file.filename)
        return saved_names

    def normalize_bug_form(form, files) -> dict:
        severity = normalize_bug_severity_value(form.get("severity", ""), form.get("priority", ""))
        platform = form.get("platform", "").strip()
        return {
            "title": form.get("title", "").strip(),
            "version": form.get("version", "").strip(),
            "module": bug_notify_key_for_platform(platform) if platform else form.get("module", "").strip(),
            "platform": platform,
            "severity": severity,
            "priority": severity,
            "assignee_id": form.get("assignee_id", "").strip(),
            "requirement_id": form.get("requirement_id", "").strip(),
            "case_id": form.get("case_id", "").strip(),
            "environment": form.get("environment", "").strip(),
            "description": form.get("description", "").strip(),
            "expected_result": form.get("expected_result", "").strip(),
            "actual_result": form.get("actual_result", "").strip(),
            "attachments": files.getlist("attachments") if files else [],
            "inline_images": files.getlist("inline_images") if files else [],
            "inline_image_sources": form.getlist("inline_image_sources") if form else [],
        }

    def sync_users() -> None:
        db = get_db()
        existing = db.execute("SELECT id, name, role, role_code, account_type, username, password, email FROM users").fetchall()
        if not existing:
            now = current_time()
            for profile in SAMPLE_USER_PROFILES:
                db.execute(
                    """
                    INSERT INTO users (name, role, role_code, account_type, username, password, email, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        profile["name"],
                        profile["role"],
                        profile["role_code"],
                        profile["account_type"],
                        profile["username"],
                        profile["password"],
                        profile["email"],
                        now,
                    ),
                )
            db.commit()
            return

        existing_by_username = {row["username"]: row for row in existing if row["username"]}
        now = current_time()
        for profile in SAMPLE_USER_PROFILES:
            user = existing_by_username.get(profile["username"])
            if user:
                db.execute(
                    """
                    UPDATE users
                    SET
                        name = COALESCE(NULLIF(name, ''), ?),
                        role = ?,
                        role_code = ?,
                        account_type = COALESCE(NULLIF(account_type, ''), ?),
                        password = COALESCE(NULLIF(password, ''), ?),
                        email = COALESCE(NULLIF(email, ''), ?)
                    WHERE id = ?
                    """,
                    (
                        profile["name"],
                        profile["role"],
                        profile["role_code"],
                        profile["account_type"],
                        profile["password"],
                        profile["email"],
                        user["id"],
                    ),
                )
                continue
            if profile["username"] != "admin":
                continue
            db.execute(
                """
                INSERT INTO users (name, role, role_code, account_type, username, password, email, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    profile["name"],
                    profile["role"],
                    profile["role_code"],
                    profile["account_type"],
                    profile["username"],
                    profile["password"],
                    profile["email"],
                    now,
                ),
            )
        db.commit()

    def seed_projects() -> None:
        db = get_db()
        if db.execute("SELECT COUNT(*) FROM projects").fetchone()[0] == 0:
            now = current_time()
            db.executemany(
                "INSERT INTO projects (name, description, created_at) VALUES (?, ?, ?)",
                [(name, desc, now) for name, desc in SAMPLE_PROJECTS],
            )
            db.commit()

    def seed_requirements() -> None:
        db = get_db()
        if db.execute("SELECT COUNT(*) FROM requirements").fetchone()[0] == 0:
            now = current_time()
            for project_name, code, title in SAMPLE_REQUIREMENTS:
                project = fetch_project_by_name(project_name)
                if project is None:
                    continue
                db.execute(
                    """
                    INSERT INTO requirements (
                        project_id, code, title, version, status, priority, description,
                        acceptance_criteria, creator_id, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        project["id"],
                        code,
                        title,
                        "",
                        "pending",
                        "中",
                        f"{title}相关需求内容待补充。",
                        f"{title}上线前需补充验收标准。",
                        6,
                        now,
                        now,
                    ),
                )
            db.commit()

    def seed_cases() -> None:
        db = get_db()
        if db.execute("SELECT COUNT(*) FROM test_cases").fetchone()[0] == 0:
            now = current_time()
            for item in SAMPLE_CASES:
                project = fetch_project_by_name(item["project_name"])
                if project is None:
                    continue
                db.execute(
                    """
                    INSERT INTO test_cases (
                        project_id, version, folder_name, doc_name, case_no, title, priority_level, module_name,
                        steps, expected_result, ios_result, android_result, h5_result, remark,
                        source_type, doc_link, execute_status, creator_id, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        project["id"],
                        item["doc_name"].split("-")[0] if "-" in item["doc_name"] else "",
                        item["folder_name"],
                        item["doc_name"],
                        item["case_no"],
                        item["title"],
                        item["priority_level"],
                        item["module_name"],
                        item["steps"],
                        item["expected_result"],
                        item["ios_result"],
                        item["android_result"],
                        item["h5_result"],
                        item["remark"],
                        item["source_type"],
                        "在线文档",
                        item["execute_status"],
                        7,
                        now,
                        now,
                    ),
                )
            db.commit()

    def seed_bugs() -> None:
        db = get_db()
        if db.execute("SELECT COUNT(*) FROM bugs").fetchone()[0] == 0:
            for bug in SAMPLE_BUGS:
                project = fetch_project_by_name(bug["project_name"])
                if project is None:
                    continue
                requirement = fetch_requirement_by_code(bug["requirement_code"])
                case = fetch_case_by_no(bug["case_code"])
                bug_id = insert_bug(
                    db=db,
                    title=bug["title"],
                    project_id=project["id"],
                    version=bug["version"],
                    module=bug["module"],
                    platform=bug.get("platform", ""),
                    severity=bug["severity"],
                    priority=bug["priority"],
                    status=bug["status"],
                    assignee_id=find_user_id(db, bug["assignee_name"]),
                    creator_id=find_user_id(db, bug["creator_name"]),
                    previous_assignee_id=find_user_id(db, bug["previous_assignee_name"]),
                    requirement_id=requirement["id"] if requirement else None,
                    case_id=case["id"] if case else None,
                    environment=bug["environment"],
                    description=bug["description"],
                    expected_result=bug["expected_result"],
                    actual_result=bug["actual_result"],
                    resolution_note=bug["resolution_note"],
                )
                add_history(
                    db,
                    bug_id,
                    "初始化",
                    f"创建缺陷，当前状态为 {STATUS_LABELS[bug['status']]}",
                    bug["creator_name"],
                    environment_snapshot=bug["environment"],
                    status_snapshot=bug["status"],
                    assignee_snapshot=bug["assignee_name"],
                )
            db.commit()

    def seed_data() -> None:
        sync_users()
        seed_projects()
        seed_requirements()
        seed_cases()
        seed_bugs()

    def current_project_id() -> int | None:
        project_id = session.get("project_id")
        if project_id:
            return int(project_id)
        first_project = get_db().execute("SELECT id FROM projects ORDER BY id LIMIT 1").fetchone()
        return int(first_project["id"]) if first_project else None

    def set_current_project(project_id: int) -> None:
        session["project_id"] = project_id

    def fetch_current_project() -> sqlite3.Row | None:
        project_id = current_project_id()
        if project_id is None:
            return None
        return fetch_project(project_id)

    def build_bug_where(filters: dict) -> tuple[str, list[str]]:
        clauses = ["bugs.project_id = ?"]
        params: list[str] = [str(current_project_id() or 0)]
        if filters.get("version"):
            clauses.append("COALESCE(bugs.version, '') = ?")
            params.append(filters["version"])
        if filters.get("platform"):
            clauses.append("COALESCE(bugs.platform, '') = ?")
            params.append(filters["platform"])
        if filters.get("creator_id"):
            clauses.append("bugs.creator_id = ?")
            params.append(filters["creator_id"])
        if filters.get("assignee_id"):
            clauses.append("bugs.assignee_id = ?")
            params.append(filters["assignee_id"])
        if filters.get("status"):
            clauses.append("bugs.status = ?")
            params.append(filters["status"])
        if filters.get("created_from"):
            clauses.append("date(bugs.created_at) >= date(?)")
            params.append(filters["created_from"])
        if filters.get("created_to"):
            clauses.append("date(bugs.created_at) <= date(?)")
            params.append(filters["created_to"])
        if filters.get("keyword"):
            keyword = f"%{filters['keyword']}%"
            normalized_keyword = filters["keyword"].strip()
            padded_keyword = normalized_keyword.zfill(3) if normalized_keyword.isdigit() else normalized_keyword
            clauses.append("(bugs.bug_no LIKE ? OR bugs.title LIKE ? OR creator.name LIKE ? OR assignee.name LIKE ?)")
            params.extend([f"%{padded_keyword}%", keyword, keyword, keyword])
        return " AND ".join(clauses), params

    def fetch_filters() -> dict:
        return {
            "version": request.args.get("version", "").strip(),
            "platform": request.args.get("platform", "").strip(),
            "creator_id": request.args.get("creator_id", "").strip(),
            "assignee_id": request.args.get("assignee_id", "").strip(),
            "status": request.args.get("status", "").strip(),
            "created_from": request.args.get("created_from", "").strip(),
            "created_to": request.args.get("created_to", "").strip(),
            "keyword": request.args.get("keyword", "").strip(),
        }

    def fetch_bug_versions(project_id: int | None = None) -> list[str]:
        target_project_id = project_id or current_project_id()
        if target_project_id is None:
            return []
        rows = get_db().execute(
            """
            SELECT DISTINCT version
            FROM bugs
            WHERE project_id = ? AND COALESCE(version, '') <> ''
            ORDER BY version DESC
            """,
            (target_project_id,),
        ).fetchall()
        return [row["version"] for row in rows]

    def build_pagination_items(page: int, pages: int, side_count: int = 1) -> list[dict[str, object]]:
        if pages <= 1:
            return [{"type": "page", "page": 1, "current": True}]
        page_numbers = {1, pages}
        page_numbers.update(range(max(1, page - side_count), min(pages, page + side_count) + 1))
        if page <= 3:
            page_numbers.update(range(1, min(pages, 4) + 1))
        if page >= pages - 2:
            page_numbers.update(range(max(1, pages - 3), pages + 1))

        items: list[dict[str, object]] = []
        previous = 0
        for page_number in sorted(page_numbers):
            if previous and page_number - previous == 2:
                items.append({"type": "page", "page": previous + 1, "current": False})
            elif previous and page_number - previous > 2:
                items.append({"type": "ellipsis"})
            items.append({"type": "page", "page": page_number, "current": page_number == page})
            previous = page_number
        return items

    def request_page(default: int = 1) -> int:
        try:
            return max(1, int(request.args.get("page", str(default)) or default))
        except (TypeError, ValueError):
            return default

    def fetch_bug_page(filters: dict, page: int) -> dict:
        db = get_db()
        where_sql, params = build_bug_where(filters)
        total = db.execute(
            f"""
            SELECT COUNT(*) AS count
            FROM bugs
            LEFT JOIN users creator ON bugs.creator_id = creator.id
            LEFT JOIN users assignee ON bugs.assignee_id = assignee.id
            WHERE {where_sql}
            """,
            params,
        ).fetchone()["count"]
        page_size = app.config["BUG_PAGE_SIZE"]
        pages = max(1, math.ceil(total / page_size)) if total else 1
        page = max(1, min(page, pages))
        offset = (page - 1) * page_size
        items = db.execute(
            f"""
            SELECT
                bugs.*,
                projects.name AS project_name,
                creator.name AS creator_name,
                assignee.name AS assignee_name,
                requirements.code AS requirement_code,
                test_cases.case_no AS case_no
            FROM bugs
            JOIN projects ON bugs.project_id = projects.id
            LEFT JOIN users creator ON bugs.creator_id = creator.id
            LEFT JOIN users assignee ON bugs.assignee_id = assignee.id
            LEFT JOIN requirements ON bugs.requirement_id = requirements.id
            LEFT JOIN test_cases ON bugs.case_id = test_cases.id
            WHERE {where_sql}
            ORDER BY bugs.created_at DESC, bugs.id DESC
            LIMIT ? OFFSET ?
            """,
            params + [page_size, offset],
        ).fetchall()
        return {
            "items": items,
            "total": total,
            "page": page,
            "pages": pages,
            "start_index": offset + 1 if total else 0,
            "end_index": min(offset + page_size, total),
            "has_prev": page > 1,
            "has_next": page < pages,
            "page_items": build_pagination_items(page, pages),
        }

    def fetch_case_page(page: int) -> dict:
        db = get_db()
        project_id = current_project_id()
        total = db.execute("SELECT COUNT(*) AS count FROM test_cases WHERE project_id = ?", (project_id,)).fetchone()["count"]
        page_size = app.config["CASE_PAGE_SIZE"]
        pages = max(1, math.ceil(total / page_size)) if total else 1
        page = max(1, min(page, pages))
        offset = (page - 1) * page_size
        items = db.execute(
            """
            SELECT * FROM test_cases
            WHERE project_id = ?
            ORDER BY id DESC
            LIMIT ? OFFSET ?
            """,
            (project_id, page_size, offset),
        ).fetchall()
        return {
            "items": items,
            "page": page,
            "pages": pages,
            "total": total,
            "start_index": offset + 1 if total else 0,
            "end_index": min(offset + page_size, total),
        }

    def normalize_case_status(ios_result: str, android_result: str, h5_result: str) -> str:
        values = [value for value in [ios_result, android_result, h5_result] if value]
        if not values:
            return "未测"
        if "failed" in values:
            return "失败"
        if "block" in values:
            return "受阻"
        if all(value == "skip" for value in values):
            return "跳过"
        if any(value == "pass" for value in values):
            return "通过"
        return "未测"

    def sync_case_execute_statuses() -> int:
        rows = get_db().execute(
            """
            SELECT id, ios_result, android_result, h5_result, execute_status
            FROM test_cases
            WHERE COALESCE(ios_result, '') <> ''
                OR COALESCE(android_result, '') <> ''
                OR COALESCE(h5_result, '') <> ''
            """
        ).fetchall()
        updates: list[tuple[str, int]] = []
        for row in rows:
            next_status = normalize_case_status(
                row["ios_result"] or "",
                row["android_result"] or "",
                row["h5_result"] or "",
            )
            if next_status != (row["execute_status"] or ""):
                updates.append((next_status, int(row["id"])))
        if updates:
            get_db().executemany(
                "UPDATE test_cases SET execute_status = ? WHERE id = ?",
                updates,
            )
            get_db().commit()
        return len(updates)

    def normalize_excel_text(value: object) -> str:
        if value is None:
            return ""
        text = str(value).strip()
        if text.lower() == "none":
            return ""
        return text

    def normalize_header_key(value: object) -> str:
        text = normalize_excel_text(value)
        return "".join(char.lower() for char in text if char not in " \t\r\n_-/:：()[]【】")

    def looks_like_priority_level(value: object) -> bool:
        text = normalize_excel_text(value).upper().replace(" ", "")
        if not text:
            return False
        if text in {"高", "中", "低", "最高", "最低", "建议"}:
            return True
        return text.startswith("P") and text[1:].isdigit()

    def looks_like_step_text(value: object) -> bool:
        text = normalize_excel_text(value)
        if not text:
            return False
        compact = text.replace(" ", "")
        return any(
            marker in compact
            for marker in [
                "前置条件",
                "前提条件",
                "【前置】",
                "点击",
                "进入",
                "打开",
                "查看",
                "长按",
                "刷新页面",
                "1、",
                "1.",
            ]
        ) or ("\n" in text and any(char.isdigit() for char in text[:4]))

    def find_excel_header_index(sheet) -> tuple[int | None, dict[str, int]]:
        header_aliases = {
            "case_no": {"用例编号", "测试编号", "编号", "caseid", "case_no", "caseno", "testcaseid", "测试用例编号"},
            "title": {"用例标题", "标题", "测试标题", "用例名称", "名称", "title", "casetitle", "testcasetitle", "测试点", "功能点", "验证点", "测试项", "测试目标", "场景"},
            "priority_level": {"优先级", "优先级别", "priority", "prioritylevel", "优先级p"},
            "module_name": {"所属模块", "模块", "功能模块", "module", "modulename", "一级模块", "二级模块", "业务模块", "功能模块名称"},
            "steps": {"测试步骤", "步骤", "操作步骤", "step", "steps", "前置条件", "前提条件", "操作内容"},
            "expected_result": {"预期结果", "预期", "expected", "expectedresult"},
            "actual_result": {"实际结果", "实际", "actual", "actualresult"},
            "execute_status": {"执行结果", "执行状态", "结果", "状态", "executestatus", "status", "result"},
            "ios_result": {"ios", "ios结果", "ios执行结果", "苹果结果"},
            "android_result": {"android", "android结果", "android执行结果"},
            "h5_result": {"h5", "h5结果", "h5执行结果", "web结果"},
            "remark": {"备注", "说明", "remark", "note", "comment"},
            "version": {"版本", "version"},
            "executor": {"执行人", "测试人", "负责人", "执行者", "executor", "tester"},
        }
        normalized_aliases = {
            key: {normalize_header_key(item) for item in values}
            for key, values in header_aliases.items()
        }
        preview_rows = list(sheet.iter_rows(min_row=1, max_row=min(sheet.max_row, 24), values_only=True))
        best_row_index = None
        best_mapping: dict[str, int] = {}
        best_score = -1

        for row_index, row in enumerate(preview_rows, start=1):
            next_row = preview_rows[row_index] if row_index < len(preview_rows) else ()
            mapping: dict[str, int] = {}
            max_cols = max(len(row), len(next_row))
            for col_index in range(max_cols):
                cell_value = row[col_index] if col_index < len(row) else ""
                next_value = next_row[col_index] if col_index < len(next_row) else ""
                next_header_key = normalize_header_key(next_value)
                if next_header_key in normalized_aliases["ios_result"] and "ios_result" not in mapping:
                    mapping["ios_result"] = col_index
                    continue
                if next_header_key in normalized_aliases["android_result"] and "android_result" not in mapping:
                    mapping["android_result"] = col_index
                    continue
                if next_header_key in normalized_aliases["h5_result"] and "h5_result" not in mapping:
                    mapping["h5_result"] = col_index
                    continue
                header_candidates: list[str] = []
                for candidate in (
                    cell_value,
                    next_value,
                    f"{normalize_excel_text(cell_value)}{normalize_excel_text(next_value)}" if normalize_excel_text(cell_value) or normalize_excel_text(next_value) else "",
                    f"{normalize_excel_text(next_value)}{normalize_excel_text(cell_value)}" if normalize_excel_text(cell_value) or normalize_excel_text(next_value) else "",
                ):
                    header_key = normalize_header_key(candidate)
                    if header_key and header_key not in header_candidates:
                        header_candidates.append(header_key)
                if not header_candidates:
                    continue
                for field_name, aliases in normalized_aliases.items():
                    if field_name in mapping:
                        continue
                    if any(header_key in aliases for header_key in header_candidates):
                        mapping[field_name] = col_index
                        break
            if "case_no" not in mapping:
                continue
            major_keys = {
                "title",
                "priority_level",
                "module_name",
                "steps",
                "expected_result",
                "actual_result",
                "ios_result",
                "android_result",
                "h5_result",
                "remark",
                "version",
                "executor",
            }
            major_count = sum(1 for key in major_keys if key in mapping)
            if major_count < 2 and not {"steps", "expected_result"}.intersection(mapping.keys()):
                continue
            score = major_count
            if "steps" in mapping:
                score += 3
            if "expected_result" in mapping:
                score += 3
            if "module_name" in mapping:
                score += 2
            if "priority_level" in mapping:
                score += 1
            if score > best_score:
                best_score = score
                best_row_index = row_index
                best_mapping = mapping

        if best_row_index is None or "case_no" not in best_mapping:
            return None, {}
        return best_row_index, best_mapping

    def normalize_platform_result(raw_status: str) -> str:
        text = normalize_excel_text(raw_status).replace(" ", "").lower()
        result_map = {
            "pass": "pass",
            "passed": "pass",
            "通过": "pass",
            "成功": "pass",
            "ok": "pass",
            "√": "pass",
            "true": "pass",
            "yes": "pass",
            "fail": "failed",
            "failed": "failed",
            "失败": "failed",
            "x": "failed",
            "×": "failed",
            "false": "failed",
            "no": "failed",
            "block": "block",
            "blocked": "block",
            "受阻": "block",
            "skip": "skip",
            "skipped": "skip",
            "跳过": "skip",
        }
        return result_map.get(text, "")

    def extract_sheet_meta_info(sheet) -> dict[str, str]:
        preview_rows = min(sheet.max_row, 5)
        preview_cols = min(sheet.max_column, 6)
        lines: list[str] = []
        for row in sheet.iter_rows(min_row=1, max_row=preview_rows, max_col=preview_cols, values_only=True):
            line = " ".join(filter(None, (normalize_excel_text(value) for value in row)))
            if line:
                lines.append(line)
        return parse_case_meta_info("\n".join(lines))

    def infer_case_version(case_no: str, version: str = "") -> str:
        version_text = normalize_excel_text(version)
        if version_text:
            return version_text
        case_no_text = normalize_excel_text(case_no)
        if "-" in case_no_text:
            prefix = case_no_text.split("-", 1)[0].strip()
            if "." in prefix:
                return prefix
        return ""

    def normalize_case_execute_status(raw_status: str) -> tuple[str, str, str, str]:
        text = normalize_excel_text(raw_status).replace(" ", "").lower()
        status_map = {
            "": ("未测", "", "", ""),
            "未测": ("未测", "", "", ""),
            "notrun": ("未测", "", "", ""),
            "norun": ("未测", "", "", ""),
            "pass": ("通过", "pass", "", ""),
            "passed": ("通过", "pass", "", ""),
            "通过": ("通过", "pass", "", ""),
            "成功": ("通过", "pass", "", ""),
            "ok": ("通过", "pass", "", ""),
            "fail": ("失败", "failed", "", ""),
            "failed": ("失败", "failed", "", ""),
            "失败": ("失败", "failed", "", ""),
            "block": ("受阻", "block", "", ""),
            "blocked": ("受阻", "block", "", ""),
            "受阻": ("受阻", "block", "", ""),
            "skip": ("跳过", "skip", "", ""),
            "skipped": ("跳过", "skip", "", ""),
            "跳过": ("跳过", "skip", "", ""),
        }
        if text in status_map:
            return status_map[text]
        return normalize_excel_text(raw_status) or "未测", "", "", ""

    def has_meaningful_case_content(
        *,
        title: str,
        module_name: str,
        steps: str,
        expected_result: str,
        actual_result: str,
        remark: str,
        executor: str,
        execute_status: str,
        ios_result: str,
        android_result: str,
        h5_result: str,
    ) -> bool:
        return any(
            [
                title,
                module_name,
                steps,
                expected_result,
                actual_result,
                remark,
                executor,
                execute_status,
                ios_result,
                android_result,
                h5_result,
            ]
        )

    def is_sparse_imported_case_row(
        *,
        case_no: str,
        title: str,
        module_name: str,
        steps: str,
        expected_result: str,
        actual_result: str,
        remark: str,
        executor: str,
        ios_result: str,
        android_result: str,
        h5_result: str,
    ) -> bool:
        if not case_no:
            return False
        if any([steps, expected_result, actual_result, remark, executor, ios_result, android_result, h5_result]):
            return False
        title_text = normalize_excel_text(title)
        module_text = normalize_excel_text(module_name)
        if not title_text and not module_text:
            return True
        if title_text and title_text == case_no:
            return True
        return bool(title_text and module_text and title_text == module_text)

    def repair_misaligned_excel_cases(db: sqlite3.Connection, doc_names: list[str] | None = None) -> int:
        query = """
            SELECT
                id, doc_name, case_no, title, priority_level, module_name, steps, expected_result, actual_result,
                remark, executor, ios_result, android_result, h5_result
            FROM test_cases
            WHERE source_type = 'Excel上传'
        """
        params: list[str] = []
        if doc_names:
            valid_doc_names = [name for name in doc_names if name]
            if valid_doc_names:
                placeholders = ",".join("?" for _ in valid_doc_names)
                query += f" AND doc_name IN ({placeholders})"
                params.extend(valid_doc_names)
        query += " ORDER BY doc_name ASC, id ASC"
        rows = db.execute(query, params).fetchall()

        repaired = 0
        current_doc_name = ""
        current_module_name = ""

        for row in rows:
            doc_name = normalize_excel_text(row["doc_name"])
            if doc_name != current_doc_name:
                current_doc_name = doc_name
                current_module_name = ""

            title = normalize_excel_text(row["title"])
            priority_level = normalize_excel_text(row["priority_level"])
            module_name = normalize_excel_text(row["module_name"])
            steps = normalize_excel_text(row["steps"])
            expected_result = normalize_excel_text(row["expected_result"])
            actual_result = normalize_excel_text(row["actual_result"])
            remark = normalize_excel_text(row["remark"])
            executor = normalize_excel_text(row["executor"])
            ios_result = normalize_excel_text(row["ios_result"])
            android_result = normalize_excel_text(row["android_result"])
            h5_result = normalize_excel_text(row["h5_result"])

            if is_sparse_imported_case_row(
                case_no=normalize_excel_text(row["case_no"]),
                title=title,
                module_name=module_name,
                steps=steps,
                expected_result=expected_result,
                actual_result=actual_result,
                remark=remark,
                executor=executor,
                ios_result=ios_result,
                android_result=android_result,
                h5_result=h5_result,
            ):
                db.execute("DELETE FROM test_cases WHERE id = ?", (row["id"],))
                repaired += 1
                continue

            if title and module_name and title == module_name and steps and normalize_platform_result(expected_result):
                if priority_level and not looks_like_priority_level(priority_level):
                    current_module_name = priority_level
                fixed_module_name = current_module_name or (priority_level if not looks_like_priority_level(priority_level) else "") or module_name
                fixed_priority_level = priority_level if looks_like_priority_level(priority_level) else "P1"
                fixed_actual_result = "" if normalize_platform_result(actual_result) else actual_result
                db.execute(
                    """
                    UPDATE test_cases
                    SET title = ?, priority_level = ?, module_name = ?, steps = ?, expected_result = ?, actual_result = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        fixed_module_name or row["case_no"],
                        fixed_priority_level,
                        fixed_module_name,
                        title,
                        steps,
                        fixed_actual_result,
                        current_time(),
                        row["id"],
                    ),
                )
                repaired += 1
                continue

            if module_name and not looks_like_step_text(module_name) and not looks_like_priority_level(module_name):
                current_module_name = module_name
            elif priority_level and not looks_like_priority_level(priority_level) and not looks_like_step_text(priority_level):
                current_module_name = priority_level

        return repaired

    def parse_case_meta_info(raw_text: str) -> dict[str, str]:
        meta = {"environment_info": "", "device_info": "", "network_info": ""}
        for line in raw_text.splitlines():
            text = normalize_excel_text(line)
            if not text:
                continue
            if "测试环境" in text and "：" in text:
                meta["environment_info"] = text.split("：", 1)[1].strip()
            elif "测试设备" in text and "：" in text:
                meta["device_info"] = text.split("：", 1)[1].strip()
            elif "网络环境" in text and "：" in text:
                meta["network_info"] = text.split("：", 1)[1].strip()
        return meta

    def fetch_case_versions(project_id: int | None = None) -> list[str]:
        target_project_id = project_id or current_project_id()
        if target_project_id is None:
            return []
        rows = get_db().execute(
            """
            SELECT DISTINCT version
            FROM test_cases
            WHERE project_id = ? AND COALESCE(version, '') <> ''
            ORDER BY version DESC
            """,
            (target_project_id,),
        ).fetchall()
        return [row["version"] for row in rows]

    def fetch_report_versions(project_id: int | None = None) -> list[str]:
        values = set(fetch_bug_versions(project_id=project_id))
        values.update(fetch_case_versions(project_id=project_id))
        return sorted((value for value in values if value), reverse=True)

    def fetch_document_dynamic_columns(project_id: int, version: str, folder_name: str, doc_name: str) -> list[sqlite3.Row]:
        return get_db().execute(
            """
            SELECT *
            FROM case_document_columns
            WHERE project_id = ?
                AND COALESCE(version, '') = COALESCE(?, '')
                AND COALESCE(folder_name, '') = COALESCE(?, '')
                AND COALESCE(doc_name, '') = COALESCE(?, '')
            ORDER BY sort_order ASC, id ASC
            """,
            (project_id, version, folder_name, doc_name),
        ).fetchall()

    def fetch_document_dynamic_cell_map(case_ids: list[int], column_ids: list[int]) -> dict[tuple[int, int], str]:
        valid_case_ids = [case_id for case_id in case_ids if case_id > 0]
        valid_column_ids = [column_id for column_id in column_ids if column_id > 0]
        if not valid_case_ids or not valid_column_ids:
            return {}
        case_placeholders = ",".join("?" for _ in valid_case_ids)
        column_placeholders = ",".join("?" for _ in valid_column_ids)
        rows = get_db().execute(
            f"""
            SELECT column_id, case_id, cell_value
            FROM case_document_cells
            WHERE case_id IN ({case_placeholders})
                AND column_id IN ({column_placeholders})
            """,
            [*valid_case_ids, *valid_column_ids],
        ).fetchall()
        return {
            (int(row["case_id"]), int(row["column_id"])): str(row["cell_value"] or "")
            for row in rows
        }

    def suggest_next_document_case_no(document: sqlite3.Row | dict[str, Any]) -> str:
        last_rows = get_db().execute(
            """
            SELECT case_no
            FROM test_cases
            WHERE project_id = ?
                AND COALESCE(version, '') = COALESCE(?, '')
                AND COALESCE(folder_name, '') = COALESCE(?, '')
                AND COALESCE(doc_name, '') = COALESCE(?, '')
            ORDER BY id DESC
            """,
            (
                document["project_id"],
                document["version"],
                document["folder_name"],
                document["doc_name"],
            ),
        ).fetchall()
        for row in last_rows:
            case_no = str(row["case_no"] or "").strip()
            match = re.match(r"^(.*?)(\d+)$", case_no)
            if match:
                prefix, number = match.groups()
                return f"{prefix}{str(int(number) + 1).zfill(len(number))}"
        version = str(document["version"] or "").strip()
        if version:
            return f"{version}-TC-001"
        next_index = count_document_cases(
            int(document["project_id"]),
            str(document["version"] or ""),
            str(document["folder_name"] or ""),
            str(document["doc_name"] or ""),
        ) + 1
        return f"TC-{str(next_index).zfill(3)}"

    def create_case_document_row(document: sqlite3.Row | dict[str, Any], db: sqlite3.Connection | None = None) -> int:
        target_db = db or get_db()
        now = current_time()
        cursor = target_db.execute(
            """
            INSERT INTO test_cases (
                project_id, version, folder_name, doc_name, case_no, title, priority_level, module_name,
                steps, expected_result, ios_result, android_result, h5_result, remark, executor,
                environment_info, device_info, network_info, source_type, doc_link, execute_status,
                creator_id, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                document["project_id"],
                document["version"],
                document["folder_name"],
                document["doc_name"],
                suggest_next_document_case_no(document),
                "",
                "P1",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                document["environment_info"] or "",
                document["device_info"] or "",
                document["network_info"] or "",
                document["source_type"] or "在线文档",
                document["doc_link"] or "",
                "未测",
                int(g.current_user["id"]) if g.current_user is not None else None,
                now,
                now,
            ),
        )
        return int(cursor.lastrowid)

    def make_unique_document_column_name(
        document: sqlite3.Row | dict[str, Any],
        column_name: str,
        db: sqlite3.Connection | None = None,
    ) -> str:
        target_db = db or get_db()
        desired = column_name.strip()
        existing_names = {
            str(row["column_name"] or "").strip().lower()
            for row in target_db.execute(
                """
                SELECT column_name
                FROM case_document_columns
                WHERE project_id = ?
                    AND COALESCE(version, '') = COALESCE(?, '')
                    AND COALESCE(folder_name, '') = COALESCE(?, '')
                    AND COALESCE(doc_name, '') = COALESCE(?, '')
                """,
                (
                    document["project_id"],
                    document["version"],
                    document["folder_name"],
                    document["doc_name"],
                ),
            ).fetchall()
        }
        if desired.lower() not in existing_names:
            return desired
        suffix = 2
        while f"{desired}{suffix}".lower() in existing_names:
            suffix += 1
        return f"{desired}{suffix}"

    def create_case_document_column(
        document: sqlite3.Row | dict[str, Any],
        column_name: str,
        db: sqlite3.Connection | None = None,
    ) -> int:
        target_db = db or get_db()
        now = current_time()
        next_sort_order = int(
            target_db.execute(
                """
                SELECT COALESCE(MAX(sort_order), 0) AS max_sort_order
                FROM case_document_columns
                WHERE project_id = ?
                    AND COALESCE(version, '') = COALESCE(?, '')
                    AND COALESCE(folder_name, '') = COALESCE(?, '')
                    AND COALESCE(doc_name, '') = COALESCE(?, '')
                """,
                (
                    document["project_id"],
                    document["version"],
                    document["folder_name"],
                    document["doc_name"],
                ),
            ).fetchone()["max_sort_order"]
            or 0
        )
        cursor = target_db.execute(
            """
            INSERT INTO case_document_columns (
                project_id, version, folder_name, doc_name, column_name, sort_order,
                creator_id, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                document["project_id"],
                document["version"],
                document["folder_name"],
                document["doc_name"],
                make_unique_document_column_name(document, column_name, db=target_db),
                next_sort_order + 1,
                int(g.current_user["id"]) if g.current_user is not None else None,
                now,
                now,
            ),
        )
        return int(cursor.lastrowid)

    def fetch_case_documents(version: str = "") -> list[sqlite3.Row]:
        params: list[object] = [current_project_id()]
        where_parts = [
            "project_id = ?",
            "COALESCE(doc_name, '') <> ''",
        ]
        if version:
            where_parts.append("COALESCE(version, '') = ?")
            params.append(version)
        return get_db().execute(
            f"""
            SELECT
                MIN(id) AS id,
                version,
                folder_name,
                doc_name,
                MIN(creator_id) AS creator_id,
                COUNT(*) AS case_count,
                MAX(updated_at) AS updated_at
            FROM test_cases
            WHERE {' AND '.join(where_parts)}
            GROUP BY version, folder_name, doc_name
            ORDER BY updated_at DESC, doc_name ASC
            """,
            params,
        ).fetchall()

    def create_case_document(folder_name: str, doc_name: str) -> None:
        db = get_db()
        now = current_time()
        unique_case_no = f"DOC-{uuid.uuid4().hex[:8].upper()}"
        db.execute(
            """
            INSERT INTO test_cases (
                project_id, version, folder_name, doc_name, case_no, title, priority_level, module_name,
                steps, expected_result, ios_result, android_result, h5_result, remark,
                source_type, doc_link, execute_status, creator_id, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                current_project_id(),
                doc_name.split("-")[0] if "-" in doc_name else "",
                folder_name,
                doc_name,
                unique_case_no,
                "",
                "P1",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "在线文档",
                "",
                "未测",
                int(g.current_user["id"]) if g.current_user is not None else None,
                now,
                now,
            ),
        )
        db.commit()

    def rename_case_document(document_id: int, version: str, folder_name: str, doc_name: str) -> int:
        document = fetch_case_document(document_id)
        if document is None:
            return 0
        db = get_db()
        cursor = db.execute(
            """
            UPDATE test_cases
            SET version = ?, folder_name = ?, doc_name = ?, updated_at = ?
            WHERE project_id = ?
                AND COALESCE(version, '') = COALESCE(?, '')
                AND COALESCE(folder_name, '') = COALESCE(?, '')
                AND COALESCE(doc_name, '') = COALESCE(?, '')
            """,
            (
                version,
                folder_name,
                doc_name,
                current_time(),
                document["project_id"],
                document["version"],
                document["folder_name"],
                document["doc_name"],
            ),
        )
        db.execute(
            """
            UPDATE case_document_columns
            SET version = ?, folder_name = ?, doc_name = ?, updated_at = ?
            WHERE project_id = ?
                AND COALESCE(version, '') = COALESCE(?, '')
                AND COALESCE(folder_name, '') = COALESCE(?, '')
                AND COALESCE(doc_name, '') = COALESCE(?, '')
            """,
            (
                version,
                folder_name,
                doc_name,
                current_time(),
                document["project_id"],
                document["version"],
                document["folder_name"],
                document["doc_name"],
            ),
        )
        db.commit()
        return int(cursor.rowcount or 0)

    def delete_case_folder(folder_name: str) -> None:
        db = get_db()
        db.execute(
            """
            DELETE FROM test_cases
            WHERE project_id = ? AND folder_name = ?
            """,
            (current_project_id(), folder_name),
        )
        db.commit()

    def delete_case_document(document_id: int) -> int:
        document = fetch_case_document(document_id)
        if document is None:
            return 0
        db = get_db()
        case_rows = db.execute(
            """
            SELECT id
            FROM test_cases
            WHERE project_id = ?
                AND COALESCE(version, '') = COALESCE(?, '')
                AND COALESCE(folder_name, '') = COALESCE(?, '')
                AND COALESCE(doc_name, '') = COALESCE(?, '')
            """,
            (document["project_id"], document["version"], document["folder_name"], document["doc_name"]),
        ).fetchall()
        case_ids = [int(row["id"]) for row in case_rows]
        if case_ids:
            placeholders = ",".join("?" for _ in case_ids)
            db.execute(f"DELETE FROM case_document_cells WHERE case_id IN ({placeholders})", case_ids)
        db.execute(
            """
            DELETE FROM case_document_columns
            WHERE project_id = ?
                AND COALESCE(version, '') = COALESCE(?, '')
                AND COALESCE(folder_name, '') = COALESCE(?, '')
                AND COALESCE(doc_name, '') = COALESCE(?, '')
            """,
            (document["project_id"], document["version"], document["folder_name"], document["doc_name"]),
        )
        cursor = db.execute(
            """
            DELETE FROM test_cases
            WHERE project_id = ?
                AND COALESCE(version, '') = COALESCE(?, '')
                AND COALESCE(folder_name, '') = COALESCE(?, '')
                AND COALESCE(doc_name, '') = COALESCE(?, '')
            """,
            (document["project_id"], document["version"], document["folder_name"], document["doc_name"]),
        )
        db.commit()
        return int(cursor.rowcount or 0)

    def delete_case_item(case_id: int) -> tuple[int, int | None, str]:
        case_item = fetch_case(case_id)
        if case_item is None:
            return 0, None, ""
        db = get_db()
        now = current_time()
        cursor = db.execute("DELETE FROM test_cases WHERE id = ?", (case_id,))
        db.execute("DELETE FROM case_document_cells WHERE case_id = ?", (case_id,))
        db.execute("UPDATE bugs SET case_id = NULL, updated_at = ? WHERE case_id = ?", (now, case_id))
        next_row = db.execute(
            """
            SELECT id
            FROM test_cases
            WHERE project_id = ?
                AND COALESCE(version, '') = COALESCE(?, '')
                AND COALESCE(folder_name, '') = COALESCE(?, '')
                AND COALESCE(doc_name, '') = COALESCE(?, '')
            ORDER BY id ASC
            LIMIT 1
            """,
            (
                case_item["project_id"],
                case_item["version"],
                case_item["folder_name"],
                case_item["doc_name"],
            ),
        ).fetchone()
        db.commit()
        return int(cursor.rowcount or 0), int(next_row["id"]) if next_row is not None else None, str(case_item["version"] or "").strip()

    def save_case_document_dynamic_cells(
        *,
        document_columns: list[sqlite3.Row],
        document_cases: list[dict[str, object]],
        form,
        db: sqlite3.Connection,
        now: str,
    ) -> None:
        if not document_columns or not document_cases:
            return
        case_ids = [int(item["id"]) for item in document_cases]
        column_ids = [int(column["id"]) for column in document_columns]
        existing_cell_map = fetch_document_dynamic_cell_map(case_ids, column_ids)
        for item in document_cases:
            case_id = int(item["id"])
            for column in document_columns:
                column_id = int(column["id"])
                field_name = f"dynamic_{column_id}_{case_id}"
                cell_value = form.get(field_name, "").strip()
                existing_value = existing_cell_map.get((case_id, column_id), "")
                if cell_value == existing_value:
                    continue
                if cell_value:
                    if (case_id, column_id) in existing_cell_map:
                        db.execute(
                            """
                            UPDATE case_document_cells
                            SET cell_value = ?, updated_at = ?
                            WHERE column_id = ? AND case_id = ?
                            """,
                            (cell_value, now, column_id, case_id),
                        )
                    else:
                        db.execute(
                            """
                            INSERT INTO case_document_cells (column_id, case_id, cell_value, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?)
                            """,
                            (column_id, case_id, cell_value, now, now),
                        )
                elif (case_id, column_id) in existing_cell_map:
                    db.execute(
                        "DELETE FROM case_document_cells WHERE column_id = ? AND case_id = ?",
                        (column_id, case_id),
                    )

    def build_case_tree(documents: list[sqlite3.Row]) -> list[dict]:
        grouped: dict[str, list[sqlite3.Row]] = {}
        for item in documents:
            folder_name = item["folder_name"] or "测试用例"
            grouped.setdefault(folder_name, []).append(item)
        tree = []
        for folder_name, items in grouped.items():
            tree.append({"name": folder_name, "documents": items})
        tree.sort(key=lambda item: item["name"])
        return tree

    def fetch_case_document(document_id: int) -> sqlite3.Row | None:
        return get_db().execute(
            """
            SELECT
                test_cases.*,
                users.name AS creator_name
            FROM test_cases
            LEFT JOIN users ON test_cases.creator_id = users.id
            WHERE test_cases.id = ?
            """,
            (document_id,),
        ).fetchone()

    def fetch_case_document_meta(project_id: int, version: str, folder_name: str, doc_name: str) -> sqlite3.Row | None:
        return get_db().execute(
            """
            SELECT *
            FROM test_cases
            WHERE project_id = ?
                AND COALESCE(version, '') = COALESCE(?, '')
                AND COALESCE(folder_name, '') = COALESCE(?, '')
                AND COALESCE(doc_name, '') = COALESCE(?, '')
            ORDER BY id ASC
            LIMIT 1
            """,
            (project_id, version, folder_name, doc_name),
        ).fetchone()

    def fetch_document_cases(project_id: int, version: str, folder_name: str, doc_name: str) -> list[sqlite3.Row]:
        return get_db().execute(
            """
            SELECT *
            FROM test_cases
            WHERE project_id = ?
                AND COALESCE(version, '') = COALESCE(?, '')
                AND COALESCE(folder_name, '') = COALESCE(?, '')
                AND COALESCE(doc_name, '') = COALESCE(?, '')
            ORDER BY id ASC
            """,
            (project_id, version, folder_name, doc_name),
        ).fetchall()

    def fetch_bug_links_for_cases(project_id: int, case_ids: list[int]) -> dict[int, list[dict[str, object]]]:
        valid_case_ids = [case_id for case_id in case_ids if case_id > 0]
        if not valid_case_ids:
            return {}
        placeholders = ",".join("?" for _ in valid_case_ids)
        rows = get_db().execute(
            f"""
            SELECT id, case_id, bug_no, title
            FROM bugs
            WHERE project_id = ?
                AND case_id IN ({placeholders})
            ORDER BY CASE
                WHEN COALESCE(bug_no, '') <> '' AND bug_no GLOB '[0-9]*' THEN CAST(bug_no AS INTEGER)
                ELSE id
            END ASC, id ASC
            """,
            [project_id, *valid_case_ids],
        ).fetchall()
        case_bug_map: dict[int, list[dict[str, object]]] = {}
        for row in rows:
            case_bug_map.setdefault(int(row["case_id"]), []).append(
                {
                    "id": int(row["id"]),
                    "bug_no": str(row["bug_no"] or "").strip(),
                    "title": str(row["title"] or "").strip(),
                }
            )
        return case_bug_map

    def fetch_case_document_bundle(document_id: int) -> dict | None:
        document = fetch_case_document(document_id)
        if document is None:
            return None
        cases = fetch_document_cases(document["project_id"], document["version"], document["folder_name"], document["doc_name"])
        dynamic_columns = fetch_document_dynamic_columns(
            document["project_id"],
            document["version"],
            document["folder_name"],
            document["doc_name"],
        )
        dynamic_cell_map = fetch_document_dynamic_cell_map(
            [int(item["id"]) for item in cases],
            [int(column["id"]) for column in dynamic_columns],
        )
        case_bug_map = fetch_bug_links_for_cases(document["project_id"], [int(item["id"]) for item in cases])
        case_rows: list[dict[str, object]] = []
        for item in cases:
            row = dict(item)
            row["linked_bugs"] = case_bug_map.get(int(item["id"]), [])
            row["dynamic_values"] = {
                int(column["id"]): dynamic_cell_map.get((int(item["id"]), int(column["id"])), "")
                for column in dynamic_columns
            }
            case_rows.append(row)
        meta = fetch_case_document_meta(document["project_id"], document["version"], document["folder_name"], document["doc_name"])
        owner = g.current_user["name"] if g.current_user is not None else ""
        collaborators = fetch_users()[:4]
        return {
            "document": document,
            "cases": case_rows,
            "columns": dynamic_columns,
            "meta": meta,
            "owner": owner,
            "collaborators": collaborators,
        }

    def count_document_cases(project_id: int, version: str, folder_name: str, doc_name: str) -> int:
        return int(
            get_db()
            .execute(
                """
                SELECT COUNT(*) AS count
                FROM test_cases
                WHERE project_id = ?
                    AND COALESCE(version, '') = COALESCE(?, '')
                    AND COALESCE(folder_name, '') = COALESCE(?, '')
                    AND COALESCE(doc_name, '') = COALESCE(?, '')
                """,
                (project_id, version, folder_name, doc_name),
            )
            .fetchone()["count"]
        )

    def build_requirement_query(filters: dict | None = None) -> tuple[str, list[str | int]]:
        filters = filters or {}
        where_parts = ["requirements.project_id = ?"]
        params: list[str | int] = [current_project_id()]
        keyword = filters.get("keyword", "").strip()
        version = filters.get("version", "").strip()
        if keyword:
            where_parts.append(
                """
                (
                    requirements.code LIKE ?
                    OR requirements.title LIKE ?
                    OR COALESCE(requirements.requirement_doc_link, '') LIKE ?
                    OR COALESCE(requirements.design_doc_link, '') LIKE ?
                )
                """
            )
            keyword_like = f"%{keyword}%"
            params.extend([keyword_like, keyword_like, keyword_like, keyword_like])
        if version:
            where_parts.append("COALESCE(requirements.version, '') = ?")
            params.append(version)
        return " AND ".join(where_parts), params

    def build_requirement_display_name(requirement: sqlite3.Row | dict) -> str:
        version = str(requirement["version"] or "").strip()
        title = str(requirement["title"] or "").strip()
        if version and title:
            return f"{version} / {title}"
        return title or str(requirement["code"] or "")

    def generate_requirement_code(project_id: int) -> str:
        db = get_db()
        rows = db.execute("SELECT code FROM requirements WHERE project_id = ?", (project_id,)).fetchall()
        current_max = 0
        for row in rows:
            code = str(row["code"] or "").strip().upper()
            if code.startswith("REQ-"):
                suffix = code[4:]
                if suffix.isdigit():
                    current_max = max(current_max, int(suffix))
        return f"REQ-{str(current_max + 1).zfill(3)}"

    def fetch_requirements(filters: dict | None = None) -> list[sqlite3.Row]:
        where_sql, params = build_requirement_query(filters)
        return get_db().execute(
            f"""
            SELECT
                requirements.*,
                projects.name AS project_name,
                users.name AS creator_name,
                COUNT(bugs.id) AS linked_bug_count
            FROM requirements
            JOIN projects ON requirements.project_id = projects.id
            LEFT JOIN users ON requirements.creator_id = users.id
            LEFT JOIN bugs ON bugs.requirement_id = requirements.id
            WHERE {where_sql}
            GROUP BY requirements.id, projects.name, users.name
            ORDER BY datetime(requirements.created_at) DESC, requirements.id DESC
            """,
            params,
        ).fetchall()

    def fetch_requirement_versions() -> list[str]:
        rows = get_db().execute(
            """
            SELECT DISTINCT version
            FROM requirements
            WHERE project_id = ? AND COALESCE(version, '') <> ''
            ORDER BY version DESC
            """,
            (current_project_id(),),
        ).fetchall()
        return [row["version"] for row in rows]

    def fetch_requirement_summary() -> dict[str, int]:
        db = get_db()
        project_id = current_project_id()
        total = int(db.execute("SELECT COUNT(*) AS count FROM requirements WHERE project_id = ?", (project_id,)).fetchone()["count"])
        requirement_doc_count = int(
            db.execute(
                "SELECT COUNT(*) AS count FROM requirements WHERE project_id = ? AND COALESCE(requirement_doc_link, '') <> ''",
                (project_id,),
            ).fetchone()["count"]
        )
        design_doc_count = int(
            db.execute(
                "SELECT COUNT(*) AS count FROM requirements WHERE project_id = ? AND COALESCE(design_doc_link, '') <> ''",
                (project_id,),
            ).fetchone()["count"]
        )
        linked_bug_total = int(
            db.execute(
                """
                SELECT COUNT(*) AS count
                FROM bugs
                JOIN requirements ON bugs.requirement_id = requirements.id
                WHERE requirements.project_id = ?
                """,
                (project_id,),
            ).fetchone()["count"]
        )
        return {
            "total": total,
            "requirement_doc_count": requirement_doc_count,
            "design_doc_count": design_doc_count,
            "linked_bug_total": linked_bug_total,
        }

    def fetch_requirement_page(filters: dict | None = None, page: int = 1) -> dict:
        db = get_db()
        where_sql, params = build_requirement_query(filters)
        total = int(
            db.execute(
                f"""
                SELECT COUNT(*) AS count
                FROM requirements
                WHERE {where_sql}
                """,
                params,
            ).fetchone()["count"]
        )
        page_size = app.config["PAGE_SIZE"]
        pages = max(1, math.ceil(total / page_size)) if total else 1
        page = max(1, min(page, pages))
        offset = (page - 1) * page_size
        items = db.execute(
            f"""
            SELECT
                requirements.*,
                projects.name AS project_name,
                users.name AS creator_name,
                COUNT(bugs.id) AS linked_bug_count
            FROM requirements
            JOIN projects ON requirements.project_id = projects.id
            LEFT JOIN users ON requirements.creator_id = users.id
            LEFT JOIN bugs ON bugs.requirement_id = requirements.id
            WHERE {where_sql}
            GROUP BY requirements.id, projects.name, users.name
            ORDER BY datetime(requirements.created_at) DESC, requirements.id DESC
            LIMIT ? OFFSET ?
            """,
            [*params, page_size, offset],
        ).fetchall()
        return {
            "items": items,
            "total": total,
            "page": page,
            "pages": pages,
            "start_index": offset + 1 if total else 0,
            "end_index": min(offset + page_size, total),
            "has_prev": page > 1,
            "has_next": page < pages,
        }

    def fetch_requirement(requirement_id: int) -> sqlite3.Row | None:
        return get_db().execute(
            """
            SELECT
                requirements.*,
                projects.name AS project_name,
                users.name AS creator_name,
                COUNT(bugs.id) AS linked_bug_count
            FROM requirements
            JOIN projects ON requirements.project_id = projects.id
            LEFT JOIN users ON requirements.creator_id = users.id
            LEFT JOIN bugs ON bugs.requirement_id = requirements.id
            WHERE requirements.id = ? AND requirements.project_id = ?
            GROUP BY requirements.id, projects.name, users.name
            """,
            (requirement_id, current_project_id()),
        ).fetchone()

    def fetch_requirement_bugs(requirement_id: int) -> list[sqlite3.Row]:
        return get_db().execute(
            """
            SELECT
                bugs.*,
                creator.name AS creator_name,
                assignee.name AS assignee_name
            FROM bugs
            LEFT JOIN users creator ON bugs.creator_id = creator.id
            LEFT JOIN users assignee ON bugs.assignee_id = assignee.id
            WHERE bugs.requirement_id = ?
            ORDER BY datetime(bugs.created_at) DESC, bugs.id DESC
            """,
            (requirement_id,),
        ).fetchall()

    def fetch_cases_for_project() -> list[sqlite3.Row]:
        return get_db().execute(
            "SELECT * FROM test_cases WHERE project_id = ? ORDER BY id DESC",
            (current_project_id(),),
        ).fetchall()

    def count_test_cases(version: str = "", project_id: int | None = None) -> int:
        target_project_id = project_id or current_project_id()
        if target_project_id is None:
            return 0
        params: list[object] = [target_project_id]
        version_sql = ""
        if version:
            version_sql = " AND COALESCE(version, '') = ?"
            params.append(version)
        return int(
            get_db()
            .execute(
                f"""
                SELECT COUNT(*) AS count
                FROM test_cases
                WHERE project_id = ?{version_sql}
                """,
                params,
            )
            .fetchone()["count"]
        )

    def fetch_summary(version: str = "", project_id: int | None = None, user_id: int | None = None) -> dict:
        db = get_db()
        target_project_id = project_id or current_project_id()
        current_user = g.get("current_user")
        if target_project_id is None:
            return {
                "total": 0,
                "active_count": 0,
                "verification_count": 0,
                "closed_count": 0,
                "my_todo_count": 0,
            }
        version_sql = " AND COALESCE(version, '') = ?" if version else ""
        version_params = [version] if version else []
        total = db.execute(
            f"SELECT COUNT(*) AS count FROM bugs WHERE project_id = ?{version_sql}",
            [target_project_id, *version_params],
        ).fetchone()["count"]
        active_count = db.execute(
            f"SELECT COUNT(*) AS count FROM bugs WHERE project_id = ?{version_sql} AND status IN ('open', 'in_progress')",
            [target_project_id, *version_params],
        ).fetchone()["count"]
        verification_count = db.execute(
            f"SELECT COUNT(*) AS count FROM bugs WHERE project_id = ?{version_sql} AND status = 'pending_verification'",
            [target_project_id, *version_params],
        ).fetchone()["count"]
        closed_count = db.execute(
            f"SELECT COUNT(*) AS count FROM bugs WHERE project_id = ?{version_sql} AND status IN ('closed', 'duplicate', 'on_hold')",
            [target_project_id, *version_params],
        ).fetchone()["count"]
        my_todo_count = 0
        target_user_id = user_id or (int(current_user["id"]) if current_user is not None else None)
        if target_user_id is not None:
            my_todo_count = db.execute(
                f"""
                SELECT COUNT(*) AS count
                FROM bugs
                WHERE project_id = ? AND assignee_id = ?
                    {f"AND COALESCE(version, '') = ?" if version else ""}
                    AND status IN ('open', 'in_progress', 'pending_verification')
                """,
                [target_project_id, target_user_id, *version_params] if version else (target_project_id, target_user_id),
            ).fetchone()["count"]
        return {
            "total": total,
            "active_count": active_count,
            "verification_count": verification_count,
            "closed_count": closed_count,
            "my_todo_count": my_todo_count,
        }

    def fetch_recent_report_bugs(project_id: int, version: str = "", limit: int = 5) -> list[sqlite3.Row]:
        params: list[object] = [project_id]
        version_sql = ""
        if version:
            version_sql = " AND COALESCE(bugs.version, '') = ?"
            params.append(version)
        params.append(limit)
        return get_db().execute(
            f"""
            SELECT
                bugs.id,
                bugs.bug_no,
                bugs.title,
                bugs.severity,
                bugs.status,
                bugs.version,
                assignee.name AS assignee_name
            FROM bugs
            LEFT JOIN users assignee ON bugs.assignee_id = assignee.id
            WHERE bugs.project_id = ?
                {version_sql}
                AND bugs.status IN ('open', 'in_progress', 'pending_verification')
            ORDER BY
                CASE bugs.severity
                    WHEN '最高' THEN 0
                    WHEN '高' THEN 1
                    WHEN '中' THEN 2
                    WHEN '低' THEN 3
                    WHEN '最低' THEN 4
                    WHEN '建议' THEN 5
                    WHEN '严重' THEN 0
                    WHEN '一般' THEN 2
                    ELSE 9
                END,
                datetime(bugs.updated_at) DESC,
                bugs.id DESC
            LIMIT ?
            """,
            params,
        ).fetchall()

    def fetch_report_risk_bugs(project_id: int, version: str = "") -> list[sqlite3.Row]:
        params: list[object] = [project_id]
        version_sql = ""
        if version:
            version_sql = " AND COALESCE(bugs.version, '') = ?"
            params.append(version)
        return get_db().execute(
            f"""
            SELECT
                bugs.id,
                bugs.bug_no,
                bugs.title,
                bugs.severity,
                bugs.status,
                assignee.name AS assignee_name
            FROM bugs
            LEFT JOIN users assignee ON bugs.assignee_id = assignee.id
            WHERE bugs.project_id = ?
                {version_sql}
                AND COALESCE(bugs.severity, '') = '{MAIL_NOTIFY_SEVERITY}'
                AND bugs.status IN ('open', 'in_progress', 'pending_verification')
            ORDER BY
                CASE bugs.status
                    WHEN 'open' THEN 0
                    WHEN 'in_progress' THEN 1
                    WHEN 'pending_verification' THEN 2
                    ELSE 9
                END,
                datetime(bugs.updated_at) DESC,
                bugs.id DESC
            """,
            params,
        ).fetchall()

    def fetch_open_bug_counts_by_platform(project_id: int, version: str = "") -> list[dict[str, object]]:
        params: list[object] = [project_id]
        version_sql = ""
        if version:
            version_sql = " AND COALESCE(version, '') = ?"
            params.append(version)
        rows = get_db().execute(
            f"""
            SELECT COALESCE(NULLIF(platform, ''), '未填写') AS platform, COUNT(*) AS count
            FROM bugs
            WHERE project_id = ?
                {version_sql}
                AND status IN ('open', 'in_progress')
            GROUP BY COALESCE(NULLIF(platform, ''), '未填写')
            """,
            params,
        ).fetchall()
        counts_by_platform = {str(row["platform"]): int(row["count"] or 0) for row in rows}
        ordered_platforms = [*BUG_PLATFORM_OPTIONS, "未填写"]
        extras = sorted(platform for platform in counts_by_platform if platform not in ordered_platforms)
        result: list[dict[str, object]] = []
        for platform in [*ordered_platforms, *extras]:
            count = counts_by_platform.get(platform, 0)
            if count <= 0:
                continue
            result.append(
                {
                    "platform": platform,
                    "label": REPORT_PLATFORM_LABELS.get(platform, platform),
                    "count": count,
                }
            )
        return result

    def fetch_my_todos() -> list[sqlite3.Row]:
        if g.current_user is None:
            return []
        return get_db().execute(
            """
            SELECT
                bugs.*,
                projects.name AS project_name,
                assignee.name AS assignee_name,
                creator.name AS creator_name
            FROM bugs
            JOIN projects ON bugs.project_id = projects.id
            LEFT JOIN users assignee ON bugs.assignee_id = assignee.id
            LEFT JOIN users creator ON bugs.creator_id = creator.id
            WHERE bugs.project_id = ? AND bugs.assignee_id = ?
                AND bugs.status IN ('open', 'in_progress', 'pending_verification')
            ORDER BY bugs.updated_at DESC
            """,
            (current_project_id(), g.current_user["id"]),
        ).fetchall()

    def fetch_bug(bug_id: int) -> sqlite3.Row | None:
        return get_db().execute(
            """
            SELECT
                bugs.*,
                projects.name AS project_name,
                assignee.name AS assignee_name,
                creator.name AS creator_name,
                previous_user.name AS previous_assignee_name,
                requirements.code AS requirement_code,
                requirements.title AS requirement_title,
                test_cases.case_no AS case_no,
                test_cases.title AS case_title
            FROM bugs
            JOIN projects ON bugs.project_id = projects.id
            LEFT JOIN users assignee ON bugs.assignee_id = assignee.id
            LEFT JOIN users creator ON bugs.creator_id = creator.id
            LEFT JOIN users previous_user ON bugs.previous_assignee_id = previous_user.id
            LEFT JOIN requirements ON bugs.requirement_id = requirements.id
            LEFT JOIN test_cases ON bugs.case_id = test_cases.id
            WHERE bugs.id = ?
            """,
            (bug_id,),
        ).fetchone()

    def create_notification(
        user_id: int | None,
        category: str,
        title: str,
        body: str,
        link_path: str = "",
        bug_id: int | None = None,
        actor_id: int | None = None,
    ) -> int:
        if not user_id:
            return 0
        cursor = get_db().execute(
            """
            INSERT INTO notifications (
                user_id, actor_id, bug_id, category, title, body, link_path,
                is_read, created_at, read_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, NULL)
            """,
            (
                int(user_id),
                actor_id,
                bug_id,
                category,
                title,
                body,
                link_path,
                current_time(),
            ),
        )
        get_db().commit()
        return int(cursor.lastrowid)

    def fetch_notification(notification_id: int, user_id: int) -> sqlite3.Row | None:
        return get_db().execute(
            """
            SELECT *
            FROM notifications
            WHERE id = ? AND user_id = ?
            """,
            (notification_id, user_id),
        ).fetchone()

    def fetch_user_notifications(user_id: int, state: str = "", limit: int = 80) -> list[sqlite3.Row]:
        where_parts = ["notifications.user_id = ?"]
        params: list[object] = [user_id]
        if state == "unread":
            where_parts.append("notifications.is_read = 0")
        params.append(limit)
        return get_db().execute(
            f"""
            SELECT
                notifications.*,
                bugs.bug_no,
                bugs.title AS bug_title,
                bugs.status AS bug_status,
                bugs.severity AS bug_severity,
                projects.name AS project_name,
                actor.name AS actor_name
            FROM notifications
            LEFT JOIN bugs ON notifications.bug_id = bugs.id
            LEFT JOIN projects ON bugs.project_id = projects.id
            LEFT JOIN users actor ON notifications.actor_id = actor.id
            WHERE {' AND '.join(where_parts)}
            ORDER BY notifications.is_read ASC, datetime(notifications.created_at) DESC, notifications.id DESC
            LIMIT ?
            """,
            params,
        ).fetchall()

    def count_user_notifications(user_id: int, unread_only: bool = False) -> int:
        where_sql = "WHERE user_id = ?"
        params: list[object] = [user_id]
        if unread_only:
            where_sql += " AND is_read = 0"
        return int(
            get_db()
            .execute(f"SELECT COUNT(*) AS count FROM notifications {where_sql}", params)
            .fetchone()["count"]
        )

    def mark_notification_read(notification_id: int, user_id: int) -> bool:
        row = fetch_notification(notification_id, user_id)
        if row is None:
            return False
        if not int(row["is_read"] or 0):
            get_db().execute(
                "UPDATE notifications SET is_read = 1, read_at = ? WHERE id = ? AND user_id = ?",
                (current_time(), notification_id, user_id),
            )
            get_db().commit()
        return True

    def mark_all_notifications_read(user_id: int) -> int:
        cursor = get_db().execute(
            """
            UPDATE notifications
            SET is_read = 1, read_at = ?
            WHERE user_id = ? AND is_read = 0
            """,
            (current_time(), user_id),
        )
        get_db().commit()
        return int(cursor.rowcount or 0)

    def create_severe_bug_assignment_message(
        bug: sqlite3.Row | None,
        assignee_user_id: int | None,
        trigger_reason: str,
        operator_name: str,
    ) -> tuple[bool, str]:
        if bug is None:
            return False, "未找到对应 Bug。"
        if str(bug["severity"] or "") != MAIL_NOTIFY_SEVERITY:
            return False, "当前 Bug 非严重级别。"
        if str(bug["status"] or "") not in TODO_STATUS_CODES:
            return False, "当前状态无需发送严重 Bug 站内消息。"
        if not assignee_user_id:
            return False, "当前处理人为空，无法发送站内消息。"

        assignee_user = fetch_user(int(assignee_user_id))
        if assignee_user is None:
            return False, "当前处理人不存在。"

        bug_no = format_bug_no(bug["bug_no"] or bug["id"])
        status_label = STATUS_LABELS.get(str(bug["status"] or ""), str(bug["status"] or "-"))
        title = f"严重 Bug 已进入你的待办：{bug_no}"
        body = (
            f"{operator_name or '系统'} {trigger_reason}，"
            f"{bug_no}「{bug['title'] or '-'}」已进入你的待办。"
            f"项目：{bug['project_name'] or '-'}；状态：{status_label}。"
        )
        actor_id = int(g.current_user["id"]) if g.get("current_user") is not None else None
        create_notification(
            user_id=int(assignee_user_id),
            actor_id=actor_id,
            bug_id=int(bug["id"]),
            category="severe_bug",
            title=title,
            body=body,
            link_path=url_for("bug_detail", bug_id=int(bug["id"])),
        )
        return True, f"已发送站内消息给 {assignee_user['name']}。"

    def fetch_bug_history(bug_id: int) -> list[sqlite3.Row]:
        return get_db().execute(
            "SELECT * FROM bug_history WHERE bug_id = ? ORDER BY created_at DESC, id DESC",
            (bug_id,),
        ).fetchall()

    def fetch_bug_comments(bug_id: int) -> list[sqlite3.Row]:
        return get_db().execute(
            """
            SELECT
                bug_comments.*,
                COALESCE(users.name, bug_comments.author_name) AS commenter_name,
                COALESCE(users.role, '') AS commenter_role
            FROM bug_comments
            LEFT JOIN users ON bug_comments.user_id = users.id
            WHERE bug_comments.bug_id = ?
            ORDER BY bug_comments.created_at DESC, bug_comments.id DESC
            """,
            (bug_id,),
        ).fetchall()

    def fetch_bug_comment(comment_id: int, bug_id: int) -> sqlite3.Row | None:
        return get_db().execute(
            """
            SELECT
                bug_comments.*,
                COALESCE(users.name, bug_comments.author_name) AS commenter_name
            FROM bug_comments
            LEFT JOIN users ON bug_comments.user_id = users.id
            WHERE bug_comments.id = ? AND bug_comments.bug_id = ?
            """,
            (comment_id, bug_id),
        ).fetchone()

    def collect_comment_branch_ids(bug_id: int, root_comment_id: int) -> list[int]:
        rows = get_db().execute(
            "SELECT id, parent_id FROM bug_comments WHERE bug_id = ? ORDER BY id ASC",
            (bug_id,),
        ).fetchall()
        children_map: dict[int | None, list[int]] = {}
        for row in rows:
            parent_id = int(row["parent_id"]) if row["parent_id"] is not None else None
            children_map.setdefault(parent_id, []).append(int(row["id"]))

        result: list[int] = []
        stack = [root_comment_id]
        while stack:
            current_id = stack.pop()
            result.append(current_id)
            for child_id in reversed(children_map.get(current_id, [])):
                stack.append(child_id)
        return result

    def build_bug_comment_threads(comments: list[sqlite3.Row]) -> list[dict[str, object]]:
        nodes: list[dict[str, object]] = []
        by_id: dict[int, dict[str, object]] = {}
        roots: list[dict[str, object]] = []

        for item in comments:
            comment_id = int(item["id"])
            node = {
                "id": comment_id,
                "parent_id": int(item["parent_id"]) if item["parent_id"] is not None else None,
                "user_id": int(item["user_id"]),
                "actor_name": str(item["commenter_name"] or item["author_name"] or ""),
                "actor_role": str(item["commenter_role"] or ""),
                "created_at": str(item["created_at"] or ""),
                "content": str(item["content"] or ""),
                "reply_to_name": "",
                "replies": [],
            }
            nodes.append(node)
            by_id[comment_id] = node

        for node in nodes:
            parent_id = node["parent_id"]
            if parent_id and parent_id in by_id:
                parent_node = by_id[parent_id]
                node["reply_to_name"] = str(parent_node["actor_name"] or "")
                parent_node["replies"].append(node)
            else:
                roots.append(node)

        for node in nodes:
            node["replies"].sort(
                key=lambda reply: (
                    str(reply["created_at"]),
                    int(reply["id"]),
                ),
                reverse=True,
            )
        roots.sort(
            key=lambda root: (
                str(root["created_at"]),
                int(root["id"]),
            ),
            reverse=True,
        )
        return roots

    def build_bug_activity_items(history: list[sqlite3.Row], comments: list[sqlite3.Row]) -> list[dict[str, object]]:
        activity_items: list[dict[str, object]] = []
        for item in comments:
            activity_items.append(
                {
                    "type": "comment",
                    "id": int(item["id"]),
                    "created_at": str(item["created_at"] or ""),
                    "actor_name": str(item["commenter_name"] or item["author_name"] or ""),
                    "actor_role": str(item["commenter_role"] or ""),
                    "content": str(item["content"] or ""),
                }
            )
        for item in history:
            activity_items.append(
                {
                    "type": "history",
                    "id": int(item["id"]),
                    "created_at": str(item["created_at"] or ""),
                    "actor_name": str(item["operator_name"] or ""),
                    "actor_role": "",
                    "action": str(item["action"] or ""),
                    "content": str(item["detail"] or ""),
                    "status_snapshot": str(item["status_snapshot"] or ""),
                    "assignee_snapshot": str(item["assignee_snapshot"] or ""),
                    "environment_snapshot": str(item["environment_snapshot"] or ""),
                }
            )
        activity_items.sort(
            key=lambda item: (
                str(item["created_at"]),
                1 if item["type"] == "comment" else 0,
                int(item["id"]),
            ),
            reverse=True,
        )
        return activity_items

    def fetch_bug_attachments(bug_id: int) -> list[sqlite3.Row]:
        return get_db().execute(
            "SELECT * FROM bug_attachments WHERE bug_id = ? ORDER BY created_at ASC, id ASC",
            (bug_id,),
        ).fetchall()

    def is_image_attachment(attachment: sqlite3.Row) -> bool:
        return str(attachment["content_type"] or "").startswith("image/")

    def group_bug_attachments(attachments: list[sqlite3.Row]) -> tuple[dict[str, list[sqlite3.Row]], list[sqlite3.Row]]:
        attachments_by_field: dict[str, list[sqlite3.Row]] = {field: [] for field in BUG_INLINE_ATTACHMENT_FIELDS}
        general_attachments: list[sqlite3.Row] = []
        for attachment in attachments:
            source_field = normalize_attachment_source(attachment["source_field"])
            if source_field in attachments_by_field and is_image_attachment(attachment):
                attachments_by_field[source_field].append(attachment)
            else:
                general_attachments.append(attachment)
        return attachments_by_field, general_attachments

    def allowed_status_transitions(status: str) -> list[str]:
        return list(STATUS_LABELS.keys())

    def derive_previous_assignee_id_for_bug(
        bug: sqlite3.Row,
        next_assignee_id: int,
    ) -> int:
        current_previous_assignee_id = int(bug["previous_assignee_id"] or 0)
        if str(bug["status"] or "") == "pending_verification":
            return current_previous_assignee_id or next_assignee_id
        return next_assignee_id

    def apply_bug_action(
        db: sqlite3.Connection,
        bug: sqlite3.Row,
        action: str,
        operator_name: str,
        note: str = "",
        assignee_id: int | None = None,
    ) -> tuple[str, int, int | None, str, str]:
        new_status = bug["status"]
        new_assignee_id = int(bug["assignee_id"])
        new_previous_assignee_id = bug["previous_assignee_id"]
        detail = "补充了处理记录"
        action_label = "更新缺陷"

        if action == "start_progress":
            new_status = "in_progress"
            action_label = "开始处理"
            detail = f"{operator_name} 开始处理该缺陷"
        elif action == "resolve":
            new_status = "pending_verification"
            new_previous_assignee_id = bug["assignee_id"]
            new_assignee_id = int(bug["creator_id"] or bug["assignee_id"])
            action_label = "提交待验证"
            detail = f"{operator_name} 提交缺陷进入待验证，系统自动回到创建人 {bug['creator_name']} 的待办"
        elif action == "reject":
            new_status = "in_progress"
            new_assignee_id = int(bug["previous_assignee_id"] or bug["assignee_id"])
            action_label = "退回处理"
            reject_user = fetch_user(new_assignee_id)
            reject_name = reject_user["name"] if reject_user else "原处理人"
            detail = f"{operator_name} 将缺陷退回处理中，系统自动回到 {reject_name} 的待办"
        elif action == "close":
            new_status = "closed"
            new_assignee_id = int(bug["creator_id"] or bug["assignee_id"])
            action_label = "关闭缺陷"
            detail = f"{operator_name} 验证通过并关闭缺陷"
        elif action == "reassign":
            if not assignee_id:
                raise ValueError("请选择转交处理人。")
            new_assignee_id = assignee_id
            new_previous_assignee_id = derive_previous_assignee_id_for_bug(bug, assignee_id)
            action_label = "转交处理"
            target_user = fetch_user(assignee_id)
            target_name = target_user["name"] if target_user else "未命名成员"
            detail = f"{operator_name} 转交给 {target_name}"
        elif action == "change_status":
            selected_status = request.form.get("status", "").strip()
            if selected_status not in STATUS_LABELS:
                raise ValueError("请选择有效状态。")
            if selected_status not in allowed_status_transitions(bug["status"]):
                raise ValueError("当前状态不支持直接切换到该选项。")
            action_label = "更新状态"
            previous_status = STATUS_LABELS.get(bug["status"], bug["status"])
            new_status = selected_status
            if selected_status in {"open", "in_progress"} and str(bug["status"] or "") == "pending_verification":
                new_assignee_id = int(bug["previous_assignee_id"] or bug["assignee_id"])
                reject_user = fetch_user(new_assignee_id)
                reject_name = reject_user["name"] if reject_user else "原处理人"
                detail = f"{operator_name} 将状态更新为 {STATUS_LABELS[selected_status]}，系统自动回到 {reject_name} 的待办"
            elif selected_status == "pending_verification":
                new_previous_assignee_id = bug["assignee_id"]
                new_assignee_id = int(bug["creator_id"] or bug["assignee_id"])
                detail = f"{operator_name} 将状态更新为待验证，系统自动回到创建人 {bug['creator_name']} 的待办"
            elif selected_status == "closed":
                new_assignee_id = int(bug["creator_id"] or bug["assignee_id"])
                detail = f"{operator_name} 将状态更新为已关闭"
            else:
                detail = f"{operator_name} 将状态从 {previous_status} 更新为 {STATUS_LABELS[selected_status]}"

        if note:
            detail += f"；说明：{note}"

        return new_status, new_assignee_id, new_previous_assignee_id, action_label, detail

    def fetch_attachment(attachment_id: int) -> sqlite3.Row | None:
        return get_db().execute(
            "SELECT * FROM bug_attachments WHERE id = ?",
            (attachment_id,),
        ).fetchone()

    def execution_distribution(
        project_id: int | None = None,
        version: str | None = None,
        folder_name: str | None = None,
        doc_name: str | None = None,
    ) -> list[dict]:
        target_project_id = project_id or current_project_id()
        params: list[object] = [target_project_id]
        where_clauses = ["project_id = ?"]
        if version is not None and str(version).strip():
            where_clauses.append("COALESCE(version, '') = COALESCE(?, '')")
            params.append(str(version).strip())
        if doc_name is not None:
            where_clauses.append("COALESCE(folder_name, '') = COALESCE(?, '')")
            where_clauses.append("COALESCE(doc_name, '') = COALESCE(?, '')")
            params.extend([folder_name, doc_name])
        rows = get_db().execute(
            f"""
            SELECT execute_status, COUNT(*) AS count
            FROM test_cases
            WHERE {' AND '.join(where_clauses)}
            GROUP BY execute_status
            """,
            params,
        ).fetchall()
        total = sum(row["count"] for row in rows) or 1
        mapped = {row["execute_status"]: row["count"] for row in rows}
        result = []
        for status in CASE_STATUS_OPTIONS:
            count = mapped.get(status, 0)
            percent = f"{(count / total) * 100:.2f}%"
            result.append({"status": status, "count": count, "percent": percent, "color": CASE_STATUS_COLORS[status]})
        return result

    def build_case_chart_bytes(version: str = "") -> bytes:
        distribution = execution_distribution(version=version)
        max_count = max((item["count"] for item in distribution), default=0) or 1
        chart_height = 170
        base_y = 240
        left = 58
        bar_width = 74
        gap = 42
        bars = []
        labels = []
        for index, item in enumerate(distribution):
            x = left + index * (bar_width + gap)
            bar_height = 0 if item["count"] == 0 else round((item["count"] / max_count) * chart_height)
            y = base_y - bar_height
            bars.append(
                f'<rect x="{x}" y="{y}" width="{bar_width}" height="{bar_height}" rx="10" fill="{item["color"]}" />'
            )
            labels.append(
                f'<text x="{x + bar_width / 2}" y="{base_y + 28}" text-anchor="middle" font-size="13" fill="#606266">{escape(CASE_STATUS_CHART_LABELS[item["status"]])}</text>'
            )
            labels.append(
                f'<text x="{x + bar_width / 2}" y="{y - 10}" text-anchor="middle" font-size="12" fill="#303133">{item["count"]}</text>'
            )
            labels.append(
                f'<text x="{x + bar_width / 2}" y="{y - 28}" text-anchor="middle" font-size="11" fill="#909399">{escape(item["percent"])}</text>'
            )
        svg = f"""
        <svg xmlns="http://www.w3.org/2000/svg" width="{SVG_CHART_WIDTH}" height="{SVG_CHART_HEIGHT}" viewBox="0 0 {SVG_CHART_WIDTH} {SVG_CHART_HEIGHT}">
            <rect width="100%" height="100%" fill="#ffffff"/>
            <text x="34" y="38" font-size="20" font-weight="600" fill="#303133">执行结果分布</text>
            <line x1="40" y1="{base_y}" x2="{SVG_CHART_WIDTH - 34}" y2="{base_y}" stroke="#dcdfe6" stroke-width="1.2"/>
            <line x1="40" y1="70" x2="40" y2="{base_y}" stroke="#dcdfe6" stroke-width="1.2"/>
            {''.join(bars)}
            {''.join(labels)}
        </svg>
        """
        return svg.encode("utf-8")

    def fetch_report_page_url(page_number: int, version: str = "") -> str:
        query: dict[str, str | int] = {}
        if version:
            query["version"] = version
        query["page"] = page_number
        return url_for("testing_report", **query)

    def build_report_jump_url(version: str = "") -> str:
        query: dict[str, str] = {}
        if version:
            query["version"] = version
        return url_for("testing_report", **query)

    def fetch_report_data(version: str = "", page: int = 1) -> dict:
        project = fetch_current_project()
        report_filters = {"version": version} if version else {}
        report_bug_page = fetch_bug_page(report_filters, page)
        return {
            "project": project,
            "case_total": count_test_cases(version=version),
            "distribution": execution_distribution(version=version),
            "summary": fetch_summary(version),
            "open_bug_platform_counts": fetch_open_bug_counts_by_platform(project_id=int(project["id"]) if project else None, version=version) if project else [],
            "bugs": report_bug_page["items"],
            "bug_page": report_bug_page,
            "selected_version": version,
            "versions": fetch_report_versions(),
        }

    def is_admin() -> bool:
        return g.current_user is not None and (
            str(g.current_user["account_type"] or "") == "admin"
            or str(g.current_user["role_code"] or "") == ADMIN_ROLE_CODE
        )

    def build_page_url(page_number: int, filters: dict) -> str:
        query = {key: value for key, value in filters.items() if value}
        query["page"] = page_number
        return url_for("bug_list", **query)

    def build_page_jump_url(filters: dict) -> str:
        query = {key: value for key, value in filters.items() if value}
        return url_for("bug_list", **query)

    def build_requirement_page_url(page_number: int, filters: dict) -> str:
        query = {key: value for key, value in filters.items() if value}
        query["page"] = page_number
        return url_for("requirement_library", **query)

    def build_requirement_jump_url(filters: dict) -> str:
        query = {key: value for key, value in filters.items() if value}
        return url_for("requirement_library", **query)

    def build_case_page_url(page_number: int) -> str:
        return url_for("case_library", page=page_number)

    def wants_json_response() -> bool:
        accept = (request.headers.get("Accept") or "").lower()
        requested_with = (request.headers.get("X-Requested-With") or "").lower()
        return request.args.get("format") == "json" or "application/json" in accept or requested_with == "xmlhttprequest"

    @app.before_request
    def load_common_data() -> Response | None:
        g.status_options = STATUS_OPTIONS
        g.status_labels = STATUS_LABELS
        g.requirement_status_options = REQUIREMENT_STATUS_OPTIONS
        g.requirement_status_labels = REQUIREMENT_STATUS_LABELS
        g.current_user = None
        user_id = session.get("user_id")
        if user_id:
            g.current_user = fetch_user(int(user_id))
        endpoint = request.endpoint or ""
        if endpoint not in {"login", "static"} and g.current_user is None:
            return redirect(url_for("login"))
        g.projects = fetch_projects()
        g.current_project = fetch_current_project()
        return None

    @app.teardown_appcontext
    def close_db(_error: Exception | None) -> None:
        db = g.pop("db", None)
        if db is not None:
            db.close()

    @app.context_processor
    def inject_helpers() -> dict:
        summary = fetch_summary() if g.get("current_user") is not None else None
        return {
            "current_user": g.get("current_user"),
            "current_project": g.get("current_project"),
            "projects": g.get("projects", []),
            "summary": summary,
            "format_bug_no": format_bug_no,
            "build_page_url": build_page_url,
            "build_page_jump_url": build_page_jump_url,
            "build_requirement_page_url": build_requirement_page_url,
            "build_requirement_jump_url": build_requirement_jump_url,
            "fetch_report_page_url": fetch_report_page_url,
            "build_report_jump_url": build_report_jump_url,
            "build_case_page_url": build_case_page_url,
            "case_status_colors": CASE_STATUS_COLORS,
            "status_labels": STATUS_LABELS,
            "requirement_status_labels": REQUIREMENT_STATUS_LABELS,
            "severity_options": BUG_SEVERITY_OPTIONS,
            "bug_priority_options": BUG_PRIORITY_OPTIONS,
            "bug_priority_icon_map": BUG_PRIORITY_ICON_MAP,
            "bug_platform_options": BUG_PLATFORM_OPTIONS,
            "allowed_status_transitions": allowed_status_transitions,
            "can_edit_bug_platform": can_edit_bug_platform,
            "is_admin": is_admin(),
        }

    @app.route("/login", methods=["GET", "POST"])
    def login() -> str | Response:
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "").strip()
            user = fetch_user_by_credentials(username, password)
            if user is None:
                flash("账号或密码错误。", "error")
            else:
                session["user_id"] = user["id"]
                first_project = fetch_projects()[0]
                session["project_id"] = first_project["id"]
                flash(f"已登录为 {user['name']}。", "success")
                return redirect(url_for("bug_list"))
        return render_template("login.html")

    @app.route("/logout")
    def logout() -> Response:
        session.clear()
        flash("已退出登录。", "success")
        return redirect(url_for("login"))

    @app.route("/switch-project", methods=["POST"])
    def switch_project() -> Response:
        project_id = int(request.form.get("project_id", "0") or 0)
        if fetch_project(project_id):
            set_current_project(project_id)
        return redirect(request.referrer or url_for("bug_list"))

    @app.route("/")
    def home() -> Response:
        return redirect(url_for("bug_list"))

    @app.route("/bugs")
    def bug_list() -> str:
        filters = fetch_filters()
        page = request_page()
        bug_page = fetch_bug_page(filters, page)
        return render_template(
            "bug_list.html",
            bugs=bug_page["items"],
            bug_page=bug_page,
            users=fetch_users(),
            bug_versions=fetch_bug_versions(),
            filters=filters,
            summary=fetch_summary(filters.get("version", "").strip()),
            requirements=fetch_requirements(),
            cases=fetch_cases_for_project(),
            bug_form_values={"version": filters.get("version", "").strip()},
        )

    @app.route("/todos")
    def my_todo_page() -> str:
        return render_template("my_todos.html", my_todos=fetch_my_todos(), summary=fetch_summary())

    @app.route("/cases")
    def case_library() -> str:
        selected_version = request.args.get("version", "").strip()
        documents = fetch_case_documents(selected_version)
        document_ids = {int(item["id"]) for item in documents}
        selected_id = int(request.args.get("document_id", "0") or 0)
        if selected_id not in document_ids:
            selected_id = 0
        if selected_id == 0 and documents:
            selected_id = int(documents[0]["id"])
        selected_document = fetch_case_document(selected_id) if selected_id else None
        selected_document_count = 0
        if selected_document is not None:
            selected_document_count = count_document_cases(
                selected_document["project_id"],
                selected_document["version"],
                selected_document["folder_name"],
                selected_document["doc_name"],
            )
        selected_distribution = execution_distribution(
            project_id=selected_document["project_id"],
            version=selected_document["version"],
            folder_name=selected_document["folder_name"],
            doc_name=selected_document["doc_name"],
        ) if selected_document is not None else execution_distribution(version=selected_version)
        return render_template(
            "case_library.html",
            case_documents=documents,
            case_tree=build_case_tree(documents),
            selected_document=selected_document,
            selected_document_count=selected_document_count,
            distribution=selected_distribution,
            selected_version=selected_version,
            case_versions=fetch_case_versions(),
        )

    @app.route("/cases/<int:document_id>")
    def case_document_detail(document_id: int) -> str | Response:
        bundle = fetch_case_document_bundle(document_id)
        if bundle is None:
            flash("未找到对应的在线文档。", "error")
            return redirect(url_for("case_library"))
        editable = can_edit_case_execution(bundle["document"])
        manageable = can_manage_case_document(bundle["document"])
        return render_template(
            "case_document_v2.html",
            case_document=bundle["document"],
            document_cases=bundle["cases"],
            document_columns=bundle["columns"],
            case_meta=bundle["meta"],
            owner_name=bundle["owner"],
            collaborators=bundle["collaborators"],
            platform_result_options=PLATFORM_RESULT_OPTIONS,
            can_edit_execution=editable,
            can_manage_document=manageable,
        )

    @app.route("/cases/<int:document_id>/update", methods=["POST"])
    def update_case_document(document_id: int) -> Response:
        bundle = fetch_case_document_bundle(document_id)
        if bundle is None:
            flash("未找到对应的在线文档。", "error")
            return redirect(url_for("case_library"))
        if not can_edit_case_execution(bundle["document"]):
            flash("仅登录用户可编辑在线文档。", "error")
            return redirect(url_for("case_document_detail", document_id=document_id))
        db = get_db()
        now = current_time()
        document_action = request.form.get("document_action", "save").strip() or "save"
        for item in bundle["cases"]:
            case_id = item["id"]
            case_no = request.form.get(f"case_no_{case_id}", "").strip() or str(item["case_no"] or "")
            priority_level = request.form.get(f"priority_level_{case_id}", "").strip() or str(item["priority_level"] or "")
            module_name = request.form.get(f"module_name_{case_id}", "").strip()
            steps = request.form.get(f"steps_{case_id}", "").strip()
            expected_result = request.form.get(f"expected_result_{case_id}", "").strip()
            ios_result = request.form.get(f"ios_result_{case_id}", "").strip()
            android_result = request.form.get(f"android_result_{case_id}", "").strip()
            h5_result = request.form.get(f"h5_result_{case_id}", "").strip()
            remark = request.form.get(f"remark_{case_id}", "").strip()
            executor = request.form.get(f"executor_{case_id}", "").strip()
            execute_status = normalize_case_status(ios_result, android_result, h5_result)
            db.execute(
                """
                UPDATE test_cases
                SET case_no = ?, priority_level = ?, module_name = ?, steps = ?, expected_result = ?,
                    ios_result = ?, android_result = ?, h5_result = ?, remark = ?, executor = ?, execute_status = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    case_no,
                    priority_level,
                    module_name,
                    steps,
                    expected_result,
                    ios_result,
                    android_result,
                    h5_result,
                    remark,
                    executor,
                    execute_status,
                    now,
                    case_id,
                ),
            )
        save_case_document_dynamic_cells(
            document_columns=bundle["columns"],
            document_cases=bundle["cases"],
            form=request.form,
            db=db,
            now=now,
        )

        if document_action == "add_row":
            create_case_document_row(bundle["document"], db=db)
            message = "已新增一行。"
            category = "success"
        elif document_action == "add_column":
            new_column_name = request.form.get("new_column_name", "").strip()
            if new_column_name:
                create_case_document_column(bundle["document"], new_column_name, db=db)
                message = "已新增一列。"
                category = "success"
            else:
                message = "文档已保存，请先填写列名。"
                category = "error"
        else:
            message = "在线文档已保存。"
            category = "success"

        db.commit()
        flash(message, category)
        return redirect(url_for("case_document_detail", document_id=document_id))

    @app.route("/cases/<int:document_id>/items/<int:case_id>/delete", methods=["POST"])
    def delete_case_item_route(document_id: int, case_id: int) -> Response:
        bundle = fetch_case_document_bundle(document_id)
        if bundle is None:
            flash("未找到对应的在线文档。", "error")
            return redirect(url_for("case_library"))
        if not can_manage_case_document(bundle["document"]):
            flash("仅管理员或文档创建人可删除用例。", "error")
            return redirect(url_for("case_document_detail", document_id=document_id))
        case_item = fetch_case(case_id)
        if case_item is None:
            flash("未找到对应的用例。", "error")
            return redirect(url_for("case_document_detail", document_id=document_id))
        same_document = (
            int(case_item["project_id"] or 0) == int(bundle["document"]["project_id"] or 0)
            and str(case_item["version"] or "") == str(bundle["document"]["version"] or "")
            and str(case_item["folder_name"] or "") == str(bundle["document"]["folder_name"] or "")
            and str(case_item["doc_name"] or "") == str(bundle["document"]["doc_name"] or "")
        )
        if not same_document:
            flash("当前用例不属于这个在线文档。", "error")
            return redirect(url_for("case_document_detail", document_id=document_id))
        deleted, next_document_id, version = delete_case_item(case_id)
        if deleted <= 0:
            flash("用例删除失败。", "error")
            return redirect(url_for("case_document_detail", document_id=document_id))
        flash("用例已删除。", "success")
        if case_id != document_id:
            return redirect(url_for("case_document_detail", document_id=document_id))
        if next_document_id is not None:
            return redirect(url_for("case_document_detail", document_id=next_document_id))
        if version:
            return redirect(url_for("case_library", version=version))
        return redirect(url_for("case_library"))

    @app.route("/cases/<int:document_id>/rename", methods=["POST"])
    def rename_case_document_route(document_id: int) -> Response:
        version_filter = request.form.get("version_filter", "").strip()
        document = fetch_case_document(document_id)
        if document is None:
            flash("未找到对应的在线文档。", "error")
            return redirect(url_for("case_library", version=version_filter) if version_filter else url_for("case_library"))
        if not can_manage_case_document(document):
            flash("仅管理员或文档创建人可修改在线文档。", "error")
            return redirect(url_for("case_library", document_id=document_id, version=version_filter) if version_filter else url_for("case_library", document_id=document_id))
        version = request.form.get("version", "").strip()
        folder_name = request.form.get("folder_name", "").strip() or "测试用例"
        doc_name = request.form.get("doc_name", "").strip()
        if not version or not doc_name:
            flash("在线文档版本和名称不能为空。", "error")
        else:
            renamed = rename_case_document(document_id, version, folder_name, doc_name)
            flash("在线文档已更新。" if renamed > 0 else "在线文档更新失败。", "success" if renamed > 0 else "error")
        target_version = version or version_filter
        return redirect(url_for("case_library", document_id=document_id, version=target_version) if target_version else url_for("case_library", document_id=document_id))

    @app.route("/cases/upload", methods=["POST"])
    def upload_cases() -> Response:
        version_filter = request.form.get("version_filter", "").strip()
        file = request.files.get("excel_file")
        if file is None or not file.filename:
            flash("请选择 Excel 文件。", "error")
            return redirect(url_for("case_library", version=version_filter) if version_filter else url_for("case_library"))
        workbook = openpyxl.load_workbook(file, data_only=True)
        db = get_db()
        project_id = current_project_id()
        now = current_time()
        imported = 0
        default_doc_name = Path(file.filename).stem
        default_version = default_doc_name.split("-")[0] if "-" in default_doc_name else ""
        folder_name = "Excel导入"
        creator_id = int(g.current_user["id"]) if g.current_user is not None else None
        workbook_sheets = [sheet for sheet in workbook.worksheets if sheet.max_row > 0 and sheet.max_column > 0]
        multi_sheet_mode = len(workbook_sheets) > 1
        scanned_sheet_count = 0
        imported_sheet_names: list[str] = []
        imported_doc_names: list[str] = []

        db.execute(
            """
            DELETE FROM test_cases
            WHERE project_id = ?
                AND source_type = 'Excel上传'
                AND folder_name = ?
                AND (
                    COALESCE(doc_name, '') = COALESCE(?, '')
                    OR COALESCE(doc_name, '') LIKE ?
                )
            """,
            (project_id, folder_name, default_doc_name, f"{default_doc_name} / %"),
        )

        for sheet in workbook_sheets:
            if sheet.max_row == 0 or sheet.max_column == 0:
                continue
            scanned_sheet_count += 1
            meta_info = extract_sheet_meta_info(sheet)
            header_row_index, header_mapping = find_excel_header_index(sheet)
            current_module_name = ""
            seen_case_nos: set[str] = set()
            sheet_imported_count = 0
            sheet_doc_name = default_doc_name if not multi_sheet_mode else f"{default_doc_name} / {sheet.title}"

            def insert_case_row(
                *,
                case_no: str,
                version: str,
                title: str,
                priority_level: str,
                module_name: str,
                steps: str,
                expected_result: str,
                actual_result: str,
                ios_result: str,
                android_result: str,
                h5_result: str,
                remark: str,
                executor: str,
                execute_status: str,
            ) -> None:
                nonlocal imported, sheet_imported_count
                case_key = case_no.strip()
                if not case_key or case_key in seen_case_nos:
                    return
                seen_case_nos.add(case_key)
                db.execute(
                    """
                    INSERT INTO test_cases (
                        project_id, version, folder_name, doc_name, case_no, title, priority_level, module_name,
                        steps, expected_result, actual_result, ios_result, android_result, h5_result, remark,
                        executor, environment_info, device_info, network_info,
                        source_type, doc_link, execute_status, creator_id, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        project_id,
                        version or default_version,
                        folder_name,
                        sheet_doc_name,
                        case_no,
                        title,
                        priority_level or "P1",
                        module_name,
                        steps,
                        expected_result,
                        actual_result,
                        ios_result,
                        android_result,
                        h5_result,
                        remark,
                        executor,
                        meta_info["environment_info"],
                        meta_info["device_info"],
                        meta_info["network_info"],
                        "Excel上传",
                        "Excel上传",
                        execute_status,
                        creator_id,
                        now,
                        now,
                    ),
                )
                imported += 1
                sheet_imported_count += 1

            if header_row_index is not None:
                for row in sheet.iter_rows(min_row=header_row_index + 1, values_only=True):
                    if not row:
                        continue

                    def mapped_text(field_name: str) -> str:
                        column_index = header_mapping.get(field_name)
                        if column_index is None or column_index >= len(row):
                            return ""
                        return normalize_excel_text(row[column_index])

                    case_no = mapped_text("case_no")
                    if not case_no:
                        module_name_raw = mapped_text("module_name")
                        if module_name_raw:
                            current_module_name = module_name_raw
                        continue

                    title = mapped_text("title")
                    priority_level = mapped_text("priority_level") or "P1"
                    module_name_raw = mapped_text("module_name")
                    steps = mapped_text("steps")
                    expected_result = mapped_text("expected_result")
                    actual_result = mapped_text("actual_result")
                    remark = mapped_text("remark")
                    executor = mapped_text("executor")
                    version = infer_case_version(case_no, mapped_text("version")) or default_version

                    execute_status_raw = mapped_text("execute_status")
                    ios_result = normalize_platform_result(mapped_text("ios_result"))
                    android_result = normalize_platform_result(mapped_text("android_result"))
                    h5_result = normalize_platform_result(mapped_text("h5_result"))
                    if not has_meaningful_case_content(
                        title=title,
                        module_name=module_name_raw,
                        steps=steps,
                        expected_result=expected_result,
                        actual_result=actual_result,
                        remark=remark,
                        executor=executor,
                        execute_status=execute_status_raw,
                        ios_result=ios_result,
                        android_result=android_result,
                        h5_result=h5_result,
                    ):
                        continue

                    if module_name_raw:
                        current_module_name = module_name_raw
                    module_name = current_module_name or (title if title and not looks_like_step_text(title) else "")
                    title = title or module_name or case_no

                    if any([ios_result, android_result, h5_result]):
                        execute_status = normalize_case_status(ios_result, android_result, h5_result)
                        if execute_status == "未测" and execute_status_raw:
                            execute_status = normalize_case_execute_status(execute_status_raw)[0]
                    else:
                        execute_status = normalize_case_execute_status(execute_status_raw)[0]

                    if not any([title, steps, expected_result, actual_result, remark, module_name]):
                        continue

                    insert_case_row(
                        case_no=case_no,
                        version=version,
                        title=title,
                        priority_level=priority_level,
                        module_name=module_name,
                        steps=steps,
                        expected_result=expected_result,
                        actual_result=actual_result,
                        ios_result=ios_result,
                        android_result=android_result,
                        h5_result=h5_result,
                        remark=remark,
                        executor=executor,
                        execute_status=execute_status,
                    )
                if sheet_imported_count > 0:
                    imported_sheet_names.append(sheet.title)
                    imported_doc_names.append(sheet_doc_name)
                continue

            start_row = 4 if sheet.max_row >= 4 else 1
            for row in sheet.iter_rows(min_row=start_row, values_only=True):
                if not row:
                    continue
                case_no = normalize_excel_text(row[0]) if len(row) > 0 else ""
                if not case_no:
                    continue
                priority_level = normalize_excel_text(row[1]) if len(row) > 1 else "P1"
                module_name_raw = normalize_excel_text(row[2]) if len(row) > 2 else ""
                title = normalize_excel_text(row[2]) if len(row) > 2 else ""
                steps = normalize_excel_text(row[3]) if len(row) > 3 else ""
                expected_result = normalize_excel_text(row[4]) if len(row) > 4 else ""
                actual_result = normalize_excel_text(row[5]) if len(row) > 5 else ""
                ios_result = normalize_platform_result(row[5] if len(row) > 5 else "")
                android_result = normalize_platform_result(row[6] if len(row) > 6 else "")
                h5_result = normalize_platform_result(row[7] if len(row) > 7 else "")
                remark = normalize_excel_text(row[8]) if len(row) > 8 else ""
                executor = normalize_excel_text(row[9]) if len(row) > 9 else ""
                if not has_meaningful_case_content(
                    title=title,
                    module_name=module_name_raw,
                    steps=steps,
                    expected_result=expected_result,
                    actual_result=actual_result,
                    remark=remark,
                    executor=executor,
                    execute_status="",
                    ios_result=ios_result,
                    android_result=android_result,
                    h5_result=h5_result,
                ):
                    continue
                if module_name_raw:
                    current_module_name = module_name_raw
                module_name = current_module_name
                execute_status = normalize_case_status(ios_result, android_result, h5_result)

                insert_case_row(
                    case_no=case_no,
                    version=infer_case_version(case_no, default_version),
                    title=title or case_no,
                    priority_level=priority_level,
                    module_name=module_name,
                    steps=steps,
                    expected_result=expected_result,
                    actual_result=actual_result,
                    ios_result=ios_result,
                    android_result=android_result,
                    h5_result=h5_result,
                    remark=remark,
                    executor=executor,
                    execute_status=execute_status,
                )
            if sheet_imported_count > 0:
                imported_sheet_names.append(sheet.title)
                imported_doc_names.append(sheet_doc_name)

        if scanned_sheet_count == 0:
            flash("Excel 中没有可读取的工作表，无法导入。", "error")
            db.commit()
            return redirect(url_for("case_library", version=version_filter) if version_filter else url_for("case_library"))
        if imported == 0:
            flash("未识别到可导入的用例数据，请检查各工作表表头中是否包含“用例编号”等核心字段。", "error")
            db.commit()
            return redirect(url_for("case_library", version=version_filter) if version_filter else url_for("case_library"))
        repaired_count = repair_misaligned_excel_cases(db, imported_doc_names)
        db.commit()
        flash(
            f"已同步 {imported} 条用例，来自 {len(imported_sheet_names)} 个工作表。"
            + (f" 已自动修正 {repaired_count} 条错位数据。" if repaired_count > 0 else ""),
            "success",
        )
        return redirect(url_for("case_library", version=version_filter) if version_filter else url_for("case_library"))

    @app.route("/cases/manage", methods=["POST"])
    def manage_case_library() -> Response:
        action = request.form.get("action", "").strip()
        folder_name = request.form.get("folder_name", "").strip()
        doc_name = request.form.get("doc_name", "").strip()
        document_id = int(request.form.get("document_id", "0") or 0)
        version_filter = request.form.get("version_filter", "").strip()
        if action == "create_folder":
            if not folder_name:
                flash("请输入文件夹名称。", "error")
            else:
                default_doc_name = f"{folder_name}-在线文档"
                create_case_document(folder_name, default_doc_name)
                flash("文件夹已创建。", "success")
        elif action == "create_document":
            if not doc_name:
                flash("请输入在线文档名称。", "error")
            else:
                create_case_document(folder_name or "测试用例", doc_name)
                flash("在线文档已创建。", "success")
        elif action == "delete_folder":
            if not folder_name:
                flash("未找到要删除的文件夹。", "error")
            elif not is_admin():
                flash("仅管理员可删除整个文件夹。", "error")
            else:
                delete_case_folder(folder_name)
                flash("文件夹已删除。", "success")
        elif action == "delete_document":
            if document_id <= 0:
                flash("未找到要删除的在线文档。", "error")
            else:
                document = fetch_case_document(document_id)
                if not can_manage_case_document(document):
                    flash("仅管理员或文档创建人可删除在线文档。", "error")
                else:
                    deleted = delete_case_document(document_id)
                    if deleted > 0:
                        flash("在线文档已删除。", "success")
                    else:
                        flash("在线文档删除失败。", "error")
        return redirect(url_for("case_library", version=version_filter) if version_filter else url_for("case_library"))

    @app.route("/requirements")
    def requirement_library() -> str:
        filters = {
            "keyword": request.args.get("keyword", "").strip(),
            "version": request.args.get("version", "").strip(),
        }
        try:
            page = int(request.args.get("page", "1") or "1")
        except ValueError:
            page = 1
        requirement_page = fetch_requirement_page(filters, page)
        return render_template(
            "requirements.html",
            requirements=requirement_page["items"],
            requirement_page=requirement_page,
            filters=filters,
            requirement_versions=fetch_requirement_versions(),
            requirement_summary=fetch_requirement_summary(),
        )

    @app.route("/requirements/<int:requirement_id>")
    def requirement_detail(requirement_id: int) -> str | Response:
        requirement = fetch_requirement(requirement_id)
        if requirement is None:
            flash("未找到对应需求。", "error")
            return redirect(url_for("requirement_library"))
        return render_template(
            "requirement_detail.html",
            requirement=requirement,
            linked_bugs=fetch_requirement_bugs(requirement_id),
        )

    @app.route("/requirements/create", methods=["POST"])
    def create_requirement() -> Response:
        code = request.form.get("code", "").strip()
        title = request.form.get("title", "").strip()
        version = request.form.get("version", "").strip()
        status = request.form.get("status", "").strip() or "pending"
        priority = request.form.get("priority", "").strip() or "中"
        description = request.form.get("description", "").strip()
        acceptance_criteria = request.form.get("acceptance_criteria", "").strip()
        requirement_doc_link = request.form.get("requirement_doc_link", "").strip()
        design_doc_link = request.form.get("design_doc_link", "").strip()
        project_id = current_project_id()
        code = code or generate_requirement_code(project_id)
        if not title or not version:
            flash("请至少填写需求标题和版本。", "error")
        elif get_db().execute("SELECT 1 FROM requirements WHERE project_id = ? AND code = ?", (project_id, code)).fetchone():
            flash("当前项目下需求编号已存在。", "error")
        else:
            now = current_time()
            cursor = get_db().execute(
                """
                INSERT INTO requirements (
                    project_id, code, title, version, status, priority, description,
                    acceptance_criteria, requirement_doc_link, design_doc_link,
                    creator_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    code,
                    title,
                    version,
                    status,
                    priority,
                    description,
                    acceptance_criteria,
                    requirement_doc_link,
                    design_doc_link,
                    int(g.current_user["id"]),
                    now,
                    now,
                ),
            )
            get_db().commit()
            flash("需求已创建。", "success")
            return redirect(url_for("requirement_detail", requirement_id=cursor.lastrowid))
        return redirect(url_for("requirement_library"))

    @app.route("/requirements/<int:requirement_id>/update", methods=["POST"])
    def update_requirement(requirement_id: int) -> Response:
        requirement = fetch_requirement(requirement_id)
        if requirement is None:
            flash("未找到对应需求。", "error")
            return redirect(url_for("requirement_library"))
        if not can_manage_requirement(requirement):
            flash("仅管理员或需求创建人可编辑需求。", "error")
            return redirect(url_for("requirement_library"))
        code = request.form.get("code", "").strip()
        title = request.form.get("title", "").strip()
        version = request.form.get("version", "").strip()
        status = request.form.get("status", "").strip() or str(requirement["status"] or "pending")
        priority = request.form.get("priority", "").strip() or str(requirement["priority"] or "中")
        description = request.form.get("description", "").strip() if "description" in request.form else str(requirement["description"] or "")
        acceptance_criteria = request.form.get("acceptance_criteria", "").strip() if "acceptance_criteria" in request.form else str(requirement["acceptance_criteria"] or "")
        requirement_doc_link = request.form.get("requirement_doc_link", "").strip()
        design_doc_link = request.form.get("design_doc_link", "").strip()
        next_url = request.form.get("next", "").strip() or url_for("requirement_detail", requirement_id=requirement_id)
        edit_url = url_for("requirement_detail", requirement_id=requirement_id, edit="1")
        code = code or str(requirement["code"] or "").strip() or generate_requirement_code(current_project_id())
        if not title or not version:
            flash("请至少填写需求标题和版本。", "error")
            return redirect(edit_url)
        elif get_db().execute(
            "SELECT 1 FROM requirements WHERE project_id = ? AND code = ? AND id != ?",
            (current_project_id(), code, requirement_id),
        ).fetchone():
            flash("当前项目下需求编号已存在。", "error")
            return redirect(edit_url)
        else:
            get_db().execute(
                """
                UPDATE requirements
                SET code = ?, title = ?, version = ?, status = ?, priority = ?, description = ?,
                    acceptance_criteria = ?, requirement_doc_link = ?, design_doc_link = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    code,
                    title,
                    version,
                    status,
                    priority,
                    description,
                    acceptance_criteria,
                    requirement_doc_link,
                    design_doc_link,
                    current_time(),
                    requirement_id,
                ),
            )
            get_db().commit()
            flash("需求已更新。", "success")
        return redirect(next_url)

    @app.route("/requirements/<int:requirement_id>/delete", methods=["POST"])
    def delete_requirement(requirement_id: int) -> Response:
        requirement = fetch_requirement(requirement_id)
        next_url = request.form.get("next", "").strip() or url_for("requirement_library")
        if requirement is None:
            flash("未找到对应需求。", "error")
            return redirect(next_url)
        if not can_manage_requirement(requirement):
            flash("仅管理员或需求创建人可删除需求。", "error")
            return redirect(next_url)
        bug_ref_count = int(get_db().execute("SELECT COUNT(*) AS count FROM bugs WHERE requirement_id = ?", (requirement_id,)).fetchone()["count"])
        if bug_ref_count > 0:
            flash("该需求已被 Bug 关联，暂不可删除。", "error")
            return redirect(next_url)
        get_db().execute("DELETE FROM requirements WHERE id = ?", (requirement_id,))
        get_db().commit()
        flash("需求已删除。", "success")
        return redirect(next_url)

    @app.route("/bugs/new", methods=["GET", "POST"])
    def create_bug() -> str | Response:
        db = get_db()
        users = fetch_users()
        requirements = fetch_requirements()
        cases = fetch_cases_for_project()
        back_url = local_back_url(url_for("bug_list"))
        prefill_case = None
        if request.method == "GET":
            prefill_case_id_text = request.args.get("case_id", "").strip()
            if prefill_case_id_text.isdigit():
                prefill_case = fetch_case(int(prefill_case_id_text))
                if prefill_case is not None and int(prefill_case["project_id"] or 0) != int(current_project_id() or 0):
                    prefill_case = None
        if request.method == "POST":
            bug_form = normalize_bug_form(request.form, request.files)
            title = bug_form["title"]
            version = bug_form["version"]
            module = bug_form["module"]
            platform = bug_form["platform"]
            severity = bug_form["severity"]
            priority = bug_form["priority"]
            assignee_id = bug_form["assignee_id"]
            requirement_id = bug_form["requirement_id"]
            case_id = bug_form["case_id"]
            environment = bug_form["environment"]
            description = bug_form["description"]
            expected_result = bug_form["expected_result"]
            actual_result = bug_form["actual_result"]
            attachments = bug_form["attachments"]
            inline_images = bug_form["inline_images"]
            inline_image_sources = bug_form["inline_image_sources"]
            if not all([title, version, module, platform, severity, assignee_id, description]):
                if wants_json_response():
                    return jsonify({"ok": False, "message": "请完整填写必填项。"}), 400
                flash("请完整填写必填项。", "error")
            else:
                bug_id = insert_bug(
                    db=db,
                    title=title,
                    project_id=current_project_id(),
                    version=version,
                    module=module,
                    platform=platform,
                    severity=severity,
                    priority=priority,
                    status="open",
                    assignee_id=int(assignee_id),
                    creator_id=int(g.current_user["id"]),
                    previous_assignee_id=int(assignee_id),
                    requirement_id=int(requirement_id) if requirement_id else None,
                    case_id=int(case_id) if case_id else None,
                    environment=environment,
                    description=description,
                    expected_result=expected_result,
                    actual_result=actual_result,
                    resolution_note="",
                )
                assignee_name = db.execute("SELECT name FROM users WHERE id = ?", (assignee_id,)).fetchone()["name"]
                saved_names = save_bug_attachments(db, bug_id, attachments)
                saved_inline_names = save_bug_attachments(db, bug_id, inline_images, inline_image_sources)
                detail = f"{g.current_user['name']} 创建缺陷并指派给 {assignee_name}"
                if saved_names:
                    detail += f"；上传附件 {len(saved_names)} 个"
                if saved_inline_names:
                    detail += f"；插入正文图片 {len(saved_inline_names)} 张"
                add_history(
                    db,
                    bug_id,
                    "创建缺陷",
                    detail,
                    g.current_user["name"],
                    environment_snapshot=environment,
                    status_snapshot="open",
                    assignee_snapshot=assignee_name,
                )
                db.commit()
                bump_bug_sync_token()
                group_notify_sent, group_notify_message = maybe_send_new_bug_group_notification(
                    bug_id=bug_id,
                    operator_name=str(g.current_user["name"] or ""),
                )
                should_show_group_notify_result = (
                    group_notify_sent
                    or group_notify_message != "当前项目未开启新建 Bug 群通知。"
                )
                if wants_json_response():
                    response_message = "创建成功"
                    if should_show_group_notify_result:
                        response_message = (
                            response_message + f"，{group_notify_message}"
                            if group_notify_sent
                            else response_message + f"，但新建Bug群通知未发送：{group_notify_message}"
                        )
                    return jsonify(
                        {
                            "ok": True,
                            "message": response_message,
                            "bug_id": bug_id,
                            "redirect_url": url_for("bug_detail", bug_id=bug_id, next=back_url),
                        }
                    )
                flash("Bug 已创建。", "success")
                if should_show_group_notify_result:
                    flash(
                        f"新建Bug群通知已发送，{group_notify_message}"
                        if group_notify_sent
                        else f"新建Bug群通知未发送：{group_notify_message}",
                        "success" if group_notify_sent else "error",
                    )
                return redirect(url_for("bug_detail", bug_id=bug_id, next=back_url))
        return render_template(
            "bug_form.html",
            users=users,
            requirements=requirements,
            cases=cases,
            back_url=back_url,
            bug_form_values=locals().get("bug_form", build_bug_form_prefill_from_request(prefill_case)),
        )

    @app.route("/bugs/<int:bug_id>")
    def bug_detail(bug_id: int) -> str | Response:
        bug = fetch_bug(bug_id)
        if bug is None:
            flash("未找到对应的 Bug。", "error")
            return redirect(url_for("bug_list"))
        back_url = local_back_url(url_for("bug_list"))
        active_tab = request.args.get("tab", "detail").strip() or "detail"
        if active_tab not in {"detail", "process", "history"}:
            active_tab = "detail"
        history = fetch_bug_history(bug_id)
        comments = fetch_bug_comments(bug_id)
        attachments = fetch_bug_attachments(bug_id)
        attachments_by_field, general_attachments = group_bug_attachments(attachments)
        return render_template(
            "bug_detail.html",
            bug=bug,
            history=history,
            comments=comments,
            comment_threads=build_bug_comment_threads(comments),
            users=fetch_users(),
            requirements=fetch_requirements(),
            cases=fetch_cases_for_project(),
            attachments=attachments,
            attachments_by_field=attachments_by_field,
            general_attachments=general_attachments,
            active_tab=active_tab,
            back_url=back_url,
        )

    @app.route("/bugs/<int:bug_id>/comments", methods=["POST"])
    def add_bug_comment(bug_id: int) -> Response:
        bug = fetch_bug(bug_id)
        default_target = url_for("bug_detail", bug_id=bug_id, tab="detail") + "#bug-comments"
        redirect_target = request.form.get("redirect_to", "").strip()
        if not redirect_target.startswith("/"):
            redirect_target = default_target
        if bug is None:
            flash("未找到对应的 Bug。", "error")
            return redirect(url_for("bug_list"))
        content = request.form.get("content", "").strip()
        parent_id_text = request.form.get("parent_id", "").strip()
        parent_id = int(parent_id_text) if parent_id_text.isdigit() else None
        if not content:
            flash("评论内容不能为空。", "error")
            return redirect(redirect_target)
        db = get_db()
        if parent_id is not None:
            parent_comment = db.execute(
                "SELECT id FROM bug_comments WHERE id = ? AND bug_id = ?",
                (parent_id, bug_id),
            ).fetchone()
            if parent_comment is None:
                parent_id = None
        now = current_time()
        db.execute(
            """
            INSERT INTO bug_comments (bug_id, user_id, parent_id, author_name, content, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                bug_id,
                int(g.current_user["id"]),
                parent_id,
                str(g.current_user["name"] or ""),
                content,
                now,
                now,
            ),
        )
        db.commit()
        flash("回复已发布。" if parent_id else "评论已发布。", "success")
        return redirect(redirect_target)

    @app.route("/bugs/<int:bug_id>/comments/<int:comment_id>/delete", methods=["POST"])
    def delete_bug_comment(bug_id: int, comment_id: int) -> Response:
        bug = fetch_bug(bug_id)
        if bug is None:
            flash("未找到对应的 Bug。", "error")
            return redirect(url_for("bug_list"))
        comment = fetch_bug_comment(comment_id, bug_id)
        if comment is None:
            flash("评论不存在或已删除。", "error")
            return redirect(url_for("bug_detail", bug_id=bug_id, tab="detail"))
        if not can_manage_bug_comment(comment):
            flash("仅评论人本人或管理员可删除评论。", "error")
            return redirect(url_for("bug_detail", bug_id=bug_id, tab="detail"))

        comment_ids = collect_comment_branch_ids(bug_id, comment_id)
        placeholders = ",".join("?" for _ in comment_ids)
        get_db().execute(f"DELETE FROM bug_comments WHERE id IN ({placeholders})", comment_ids)
        get_db().commit()
        flash("评论及回复已删除。" if len(comment_ids) > 1 else "评论已删除。", "success")
        return redirect(url_for("bug_detail", bug_id=bug_id, tab="detail") + "#bug-comments")

    @app.route("/bugs/<int:bug_id>/edit", methods=["POST"])
    def edit_bug(bug_id: int) -> Response:
        db = get_db()
        bug = fetch_bug(bug_id)
        back_url = local_back_url(url_for("bug_list"))
        if bug is None:
            flash("未找到对应的 Bug。", "error")
            return redirect(url_for("bug_list"))
        if not can_manage_bug(bug):
            flash("仅管理员或创建人可编辑该 Bug。", "error")
            return redirect(url_for("bug_detail", bug_id=bug_id, next=back_url))

        bug_form = normalize_bug_form(request.form, request.files)
        title = bug_form["title"]
        version = bug_form["version"]
        module = bug_form["module"]
        platform = bug_form["platform"]
        severity = bug_form["severity"]
        priority = bug_form["priority"]
        assignee_id = bug_form["assignee_id"]
        requirement_id = bug_form["requirement_id"]
        case_id = bug_form["case_id"]
        environment = bug_form["environment"]
        description = bug_form["description"]
        expected_result = bug_form["expected_result"]
        actual_result = bug_form["actual_result"]
        attachments = bug_form["attachments"]
        inline_images = bug_form["inline_images"]
        inline_image_sources = bug_form["inline_image_sources"]

        if not all([title, version, module, platform, severity, assignee_id, description]):
            flash("请完整填写必填项。", "error")
            return redirect(url_for("bug_detail", bug_id=bug_id, tab="detail", edit="1", next=back_url))

        saved_names = save_bug_attachments(db, bug_id, attachments)
        saved_inline_names = save_bug_attachments(db, bug_id, inline_images, inline_image_sources)
        previous_severity = str(bug["severity"] or "")
        previous_assignee_id = int(bug["assignee_id"] or 0)
        next_assignee_id = int(assignee_id)
        next_previous_assignee_id = derive_previous_assignee_id_for_bug(bug, next_assignee_id)
        db.execute(
            """
            UPDATE bugs
            SET title = ?, version = ?, module = ?, platform = ?, severity = ?, priority = ?, assignee_id = ?, previous_assignee_id = ?,
                requirement_id = ?, case_id = ?, environment = ?, description = ?, expected_result = ?,
                actual_result = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                title,
                version,
                module,
                platform,
                severity,
                priority,
                next_assignee_id,
                next_previous_assignee_id,
                int(requirement_id) if requirement_id else None,
                int(case_id) if case_id else None,
                environment,
                description,
                expected_result,
                actual_result,
                current_time(),
                bug_id,
            ),
        )
        detail = f"{g.current_user['name']} 编辑了缺陷信息"
        if saved_names:
            detail += f"；新增附件 {len(saved_names)} 个"
        if saved_inline_names:
            detail += f"；插入正文图片 {len(saved_inline_names)} 张"
        target_user = fetch_user(next_assignee_id)
        add_history(
            db,
            bug_id,
            "编辑缺陷",
            detail,
            g.current_user["name"],
            environment_snapshot=environment,
            status_snapshot=bug["status"],
            assignee_snapshot=target_user["name"] if target_user else bug["assignee_name"],
        )
        db.commit()
        bump_bug_sync_token()
        flash("Bug 信息已更新。", "success")
        if (
            severity == MAIL_NOTIFY_SEVERITY
            and bug["status"] in TODO_STATUS_CODES
            and (previous_severity != MAIL_NOTIFY_SEVERITY or previous_assignee_id != next_assignee_id)
        ):
            notify_sent, notify_message = maybe_send_severe_bug_assignment_notification(
                bug_id=bug_id,
                assignee_user_id=next_assignee_id,
                trigger_reason="编辑后进入待办",
                operator_name=str(g.current_user["name"] or ""),
            )
            flash(
                f"严重Bug通知已发送，{notify_message}" if notify_sent else f"严重Bug通知未发送：{notify_message}",
                "success" if notify_sent else "error",
            )
        return redirect(url_for("bug_detail", bug_id=bug_id, tab="detail", next=back_url))

    @app.route("/bugs/<int:bug_id>/delete", methods=["POST"])
    def delete_bug(bug_id: int) -> Response:
        db = get_db()
        bug = fetch_bug(bug_id)
        if bug is None:
            flash("未找到对应的 Bug。", "error")
            return redirect(url_for("bug_list"))
        if not can_manage_bug(bug):
            flash("仅管理员或创建人可删除该 Bug。", "error")
            return redirect(url_for("bug_detail", bug_id=bug_id))
        db.execute("DELETE FROM bug_attachments WHERE bug_id = ?", (bug_id,))
        db.execute("DELETE FROM bug_history WHERE bug_id = ?", (bug_id,))
        db.execute("DELETE FROM bug_comments WHERE bug_id = ?", (bug_id,))
        db.execute("DELETE FROM bugs WHERE id = ?", (bug_id,))
        db.commit()
        bump_bug_sync_token()
        flash("Bug 已删除。", "success")
        return redirect(url_for("bug_list"))

    @app.route("/attachments/<int:attachment_id>")
    def view_attachment(attachment_id: int) -> str | Response:
        attachment = fetch_attachment(attachment_id)
        if attachment is None:
            flash("附件不存在。", "error")
            return redirect(url_for("bug_list"))
        file_path = Path(attachment["file_path"])
        if not file_path.exists():
            flash("附件文件不存在。", "error")
            return redirect(url_for("bug_list"))
        preview_mode = request.args.get("preview", "").strip() == "1"
        if preview_mode:
            return render_template("attachment_preview.html", attachment=attachment)
        return send_file(file_path, mimetype=attachment["content_type"] or "application/octet-stream", as_attachment=False, download_name=attachment["filename"])

    @app.route("/bugs/<int:bug_id>/update", methods=["POST"])
    def update_bug(bug_id: int) -> Response:
        db = get_db()
        bug = fetch_bug(bug_id)
        if bug is None:
            flash("未找到对应的 Bug。", "error")
            return redirect(url_for("bug_list"))
        action = request.form.get("action", "").strip()
        redirect_target = request.form.get("redirect_to", "").strip() or url_for("bug_detail", bug_id=bug_id)
        if action == "change_platform":
            if not can_edit_bug_platform(bug):
                flash("仅当前处理人、提Bug人或管理员可修改端。", "error")
                return redirect(redirect_target)
            selected_platform = request.form.get("platform", "").strip()
            if selected_platform not in BUG_PLATFORM_OPTIONS:
                flash("请选择有效的端。", "error")
                return redirect(redirect_target)
            if selected_platform == (bug["platform"] or ""):
                flash("端未发生变化。", "success")
                return redirect(redirect_target)
            selected_module = bug_notify_key_for_platform(selected_platform)
            db.execute(
                "UPDATE bugs SET platform = ?, module = ?, updated_at = ? WHERE id = ?",
                (selected_platform, selected_module, current_time(), bug_id),
            )
            add_history(
                db,
                bug_id,
                "更新端",
                f"{g.current_user['name']} 将端更新为 {selected_platform}",
                g.current_user["name"],
                environment_snapshot=bug["environment"] or "",
                status_snapshot=bug["status"],
                assignee_snapshot=bug["assignee_name"] or "",
            )
            db.commit()
            bump_bug_sync_token()
            flash("端信息已更新。", "success")
            return redirect(redirect_target)
        note = request.form.get("resolution_note", "").strip()
        assignee_target = int(request.form.get("assignee_id", "0") or 0)
        try:
            new_status, new_assignee_id, new_previous_assignee_id, action_label, detail = apply_bug_action(
                db=db,
                bug=bug,
                action=action,
                operator_name=g.current_user["name"],
                note=note,
                assignee_id=assignee_target or None,
            )
        except ValueError as exc:
            flash(str(exc), "error")
            return redirect(redirect_target)
        db.execute(
            """
            UPDATE bugs
            SET status = ?, assignee_id = ?, previous_assignee_id = ?, resolution_note = ?, updated_at = ?
            WHERE id = ?
            """,
            (new_status, new_assignee_id, new_previous_assignee_id, note or bug["resolution_note"], current_time(), bug_id),
        )
        target_user = fetch_user(new_assignee_id)
        add_history(
            db,
            bug_id,
            action_label,
            detail,
            g.current_user["name"],
            environment_snapshot=bug["environment"] or "",
            status_snapshot=new_status,
            assignee_snapshot=target_user["name"] if target_user else bug["assignee_name"],
        )
        db.commit()
        bump_bug_sync_token()
        flash("Bug 流转已更新。", "success")
        should_notify_assignee = (
            str(bug["severity"] or "") == MAIL_NOTIFY_SEVERITY
            and new_status in TODO_STATUS_CODES
            and (
                new_assignee_id != int(bug["assignee_id"] or 0)
                or action in {"resolve", "reject", "reassign"}
                or (action == "change_status" and new_status == "pending_verification")
            )
        )
        if should_notify_assignee:
            notify_sent, notify_message = maybe_send_severe_bug_assignment_notification(
                bug_id=bug_id,
                assignee_user_id=new_assignee_id,
                trigger_reason=action_label,
                operator_name=str(g.current_user["name"] or ""),
            )
            flash(
                f"严重Bug通知已发送，{notify_message}" if notify_sent else f"严重Bug通知未发送：{notify_message}",
                "success" if notify_sent else "error",
            )
        return redirect(redirect_target)

    @app.route("/reports/testing")
    def testing_report() -> str:
        version = request.args.get("version", "").strip()
        page = max(1, int(request.args.get("page", "1") or 1))
        return render_template("report.html", report=fetch_report_data(version, page))

    @app.route("/reports/testing/chart.png")
    def testing_report_chart() -> Response:
        version = request.args.get("version", "").strip()
        image = build_case_chart_bytes(version=version)
        return Response(image, mimetype="image/svg+xml")

    @app.route("/reports/testing/export")
    def export_testing_report() -> Response:
        version = request.args.get("version", "").strip()
        report = fetch_report_data(version)
        html = render_template("report_export.html", report=report)
        filename = f"testing-report-{datetime.now().strftime('%Y%m%d-%H%M')}.html"
        return Response(html, mimetype="text/html; charset=utf-8", headers={"Content-Disposition": f'attachment; filename=\"{filename}\"'})

    @app.route("/profile", methods=["GET", "POST"])
    def profile_page() -> str | Response:
        if g.current_user is None:
            return redirect(url_for("login"))
        db = get_db()
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip()
            password = request.form.get("password", "").strip()
            if not name:
                flash("姓名不能为空。", "error")
            else:
                if password:
                    db.execute(
                        "UPDATE users SET name = ?, email = ?, password = ? WHERE id = ?",
                        (name, email, password, g.current_user["id"]),
                    )
                else:
                    db.execute(
                        "UPDATE users SET name = ?, email = ? WHERE id = ?",
                        (name, email, g.current_user["id"]),
                    )
                db.commit()
                if password:
                    session.clear()
                    flash("密码已修改，请使用新密码重新登录。", "success")
                    return redirect(url_for("login"))
                flash("个人信息已更新。", "success")
                return redirect(url_for("profile_page"))
        return render_template("profile.html", profile_user=fetch_user(int(g.current_user["id"])))

    @app.route("/admin", methods=["GET", "POST"])
    def admin_center() -> str | Response:
        denied = require_admin_access()
        if denied is not None:
            return denied
        db = get_db()
        if request.method == "POST":
            redirect_target = admin_redirect_target()
            entity = request.form.get("entity", "").strip()
            action = request.form.get("action", "").strip()
            if entity == "project":
                project_id = int(request.form.get("project_id", "0") or 0)
                name = request.form.get("name", "").strip()
                description = request.form.get("description", "").strip()
                bug_notify_enabled = 1 if request.form.get("bug_notify_enabled") == "1" else 0
                bug_notify_webhook = request.form.get("bug_notify_webhook", "").strip()
                bug_notify_secret = request.form.get("bug_notify_secret", "").strip()
                bug_notify_base_url = request.form.get("bug_notify_base_url", "").strip()
                bug_notify_rules: list[dict[str, object]] = []
                if action in {"create", "update"}:
                    try:
                        validate_project_bug_notify_settings(
                            bug_notify_enabled,
                            bug_notify_webhook,
                            bug_notify_base_url,
                            label="默认新建 Bug 群通知",
                        )
                        bug_notify_rules = parse_project_bug_notify_rule_form(request.form)
                    except ValueError as exc:
                        flash(str(exc), "error")
                        return redirect(redirect_target)
                if action == "create":
                    if not name:
                        flash("项目名称不能为空。", "error")
                    elif db.execute("SELECT 1 FROM projects WHERE name = ?", (name,)).fetchone():
                        flash("项目名称已存在。", "error")
                    else:
                        cursor = db.execute(
                            """
                            INSERT INTO projects (
                                name, description, bug_notify_enabled, bug_notify_webhook,
                                bug_notify_secret, bug_notify_base_url, created_at
                            )
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                name,
                                description,
                                bug_notify_enabled,
                                bug_notify_webhook,
                                bug_notify_secret,
                                bug_notify_base_url,
                                current_time(),
                            ),
                        )
                        save_project_bug_notify_rules(int(cursor.lastrowid), bug_notify_rules)
                        db.commit()
                        flash("项目已创建。", "success")
                elif action == "update":
                    project = fetch_project(project_id)
                    if project is None:
                        flash("未找到对应项目。", "error")
                    elif not name:
                        flash("项目名称不能为空。", "error")
                    elif db.execute("SELECT 1 FROM projects WHERE name = ? AND id != ?", (name, project_id)).fetchone():
                        flash("项目名称已存在。", "error")
                    else:
                        db.execute(
                            """
                            UPDATE projects
                            SET name = ?, description = ?, bug_notify_enabled = ?,
                                bug_notify_webhook = ?, bug_notify_secret = ?, bug_notify_base_url = ?
                            WHERE id = ?
                            """,
                            (
                                name,
                                description,
                                bug_notify_enabled,
                                bug_notify_webhook,
                                bug_notify_secret,
                                bug_notify_base_url,
                                project_id,
                            ),
                        )
                        save_project_bug_notify_rules(project_id, bug_notify_rules)
                        db.commit()
                        if current_project_id() == project_id:
                            set_current_project(project_id)
                        flash("项目已更新。", "success")
                elif action == "delete":
                    project = fetch_project(project_id)
                    if project is None:
                        flash("未找到对应项目。", "error")
                    else:
                        deleted_summary = delete_project_with_related_data(project_id)
                        if current_project_id() == project_id:
                            remaining = fetch_projects()
                            if remaining:
                                set_current_project(int(remaining[0]["id"]))
                            else:
                                session.pop("project_id", None)
                        flash(
                            f"项目已删除，并清理 Bug {deleted_summary['bugs']} 条、需求 {deleted_summary['requirements']} 条、用例 {deleted_summary['cases']} 条。",
                            "success",
                        )
            elif entity == "user":
                user_id = int(request.form.get("user_id", "0") or 0)
                name = request.form.get("name", "").strip()
                account_type, role_code, role = resolve_user_role_from_form(request.form)
                username = request.form.get("username", "").strip()
                password = request.form.get("password", "").strip()
                email = request.form.get("email", "").strip()
                valid_role_codes = set(ROLE_LABELS) | {ADMIN_ROLE_CODE}
                if action == "create":
                    if account_type not in {"member", "admin"}:
                        flash("请选择有效的账号类型。", "error")
                    elif role_code not in valid_role_codes or not role:
                        flash("请选择有效的成员角色。", "error")
                    elif account_type == "member" and role_code == ADMIN_ROLE_CODE:
                        flash("普通成员不能使用管理员角色。", "error")
                    elif not all([name, username, password, email]):
                        flash("请完整填写账号信息，邮箱为必填。", "error")
                    elif db.execute("SELECT 1 FROM users WHERE name = ?", (name,)).fetchone():
                        flash("姓名已存在。", "error")
                    elif db.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone():
                        flash("账号已存在。", "error")
                    else:
                        db.execute(
                            """
                            INSERT INTO users (name, role, role_code, account_type, username, password, email, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (name, role, role_code, account_type, username, password, email, current_time()),
                        )
                        db.commit()
                        flash("账号已创建。", "success")
                elif action == "update":
                    target_user = fetch_user(user_id)
                    if target_user is None:
                        flash("未找到对应账号。", "error")
                    elif role_code not in valid_role_codes or not role:
                        flash("请选择有效的成员角色。", "error")
                    elif account_type == "member" and role_code == ADMIN_ROLE_CODE:
                        flash("普通成员不能使用管理员角色。", "error")
                    elif not all([name, username, email]):
                        flash("请完整填写账号信息，邮箱为必填。", "error")
                    elif db.execute("SELECT 1 FROM users WHERE name = ? AND id != ?", (name, user_id)).fetchone():
                        flash("姓名已存在。", "error")
                    elif db.execute("SELECT 1 FROM users WHERE username = ? AND id != ?", (username, user_id)).fetchone():
                        flash("账号已存在。", "error")
                    elif account_type not in {"member", "admin"}:
                        flash("请选择有效的账号类型。", "error")
                    else:
                        if password:
                            db.execute(
                                """
                                UPDATE users
                                SET name = ?, role = ?, role_code = ?, account_type = ?, username = ?, password = ?, email = ?
                                WHERE id = ?
                                """,
                                (name, role, role_code, account_type, username, password, email, user_id),
                            )
                        else:
                            db.execute(
                                """
                                UPDATE users
                                SET name = ?, role = ?, role_code = ?, account_type = ?, username = ?, email = ?
                                WHERE id = ?
                                """,
                                (name, role, role_code, account_type, username, email, user_id),
                            )
                        db.commit()
                        flash("账号已更新。", "success")
                elif action == "delete":
                    target_user = fetch_user(user_id)
                    if target_user is None:
                        flash("未找到对应账号。", "error")
                    elif g.current_user is not None and int(g.current_user["id"]) == user_id:
                        flash("当前登录账号不可删除。", "error")
                    elif user_usage_count(user_id) > 0:
                        flash("该账号仍被 Bug 流转使用，暂不可删除。", "error")
                    else:
                        db.execute("DELETE FROM users WHERE id = ?", (user_id,))
                        db.commit()
                        flash("账号已删除。", "success")
            elif entity == "mail":
                flash("邮件发送已取消，请使用项目新建 Bug 群通知。", "error")
            elif entity == "report_notify":
                if action == "update":
                    try:
                        update_group_report_settings(request.form)
                    except ValueError as exc:
                        flash(str(exc), "error")
                    else:
                        flash("群测试报告通知设置已保存。", "success")
                elif action == "send_test":
                    try:
                        manual_note = request.form.get("manual_note", "").strip()
                        project_name, version_name, _sent_at = send_testing_report_to_group(
                            force=True,
                            mark_daily_sent=False,
                            manual_note=manual_note,
                        )
                    except Exception as exc:
                        flash(f"群测试报告发送失败：{exc}", "error")
                    else:
                        note_suffix = "，已附带手动备注" if manual_note else ""
                        flash(f"测试发送成功，已发送 {project_name} / {version_name} 测试报告到群{note_suffix}。", "success")
            return redirect(redirect_target)
        return render_template("admin.html", admin_cards=admin_dashboard_cards())

    @app.route("/admin/projects")
    def admin_projects_page() -> str | Response:
        denied = require_admin_access()
        if denied is not None:
            return denied
        return render_template("admin_projects.html", projects=fetch_projects())

    @app.route("/admin/users")
    def admin_users_page() -> str | Response:
        denied = require_admin_access()
        if denied is not None:
            return denied
        return render_template("admin_users.html", users=fetch_users())

    @app.route("/admin/mail")
    def admin_mail_page() -> str | Response:
        denied = require_admin_access()
        if denied is not None:
            return denied
        flash("邮件发送已取消，请使用项目新建 Bug 群通知。", "error")
        return redirect(url_for("admin_projects_page"))

    @app.route("/admin/report-notify")
    def admin_report_notify_page() -> str | Response:
        denied = require_admin_access()
        if denied is not None:
            return denied
        settings = fetch_group_report_settings()
        selected_project_id = int(settings["project_id"]) if settings["project_id"].isdigit() else 0
        return render_template(
            "admin_report_notify.html",
            report_notify_settings=settings,
            report_projects=fetch_projects(),
            report_versions=fetch_report_versions(project_id=selected_project_id or None),
        )

    @app.route("/admin/projects/<int:project_id>")
    def admin_project_detail(project_id: int) -> str | Response:
        denied = require_admin_access()
        if denied is not None:
            return denied
        project = fetch_project(project_id)
        if project is None:
            flash("未找到对应项目。", "error")
            return redirect(url_for("admin_projects_page"))
        return render_template(
            "admin_project_detail.html",
            project=project,
            usage_count=project_usage_count(project_id),
            bug_notify_rules=fetch_project_bug_notify_rule_options(project_id),
        )

    @app.route("/admin/users/<int:user_id>")
    def admin_user_detail(user_id: int) -> str | Response:
        denied = require_admin_access()
        if denied is not None:
            return denied
        target_user = fetch_user(user_id)
        if target_user is None:
            flash("未找到对应账号。", "error")
            return redirect(url_for("admin_users_page"))
        return render_template(
            "admin_user_detail.html",
            target_user=target_user,
            usage_count=user_usage_count(user_id),
        )

    with app.app_context():
        init_db()
        run_migrations()
        seed_data()
        sync_case_execute_statuses()
        repaired_case_count = repair_misaligned_excel_cases(get_db())
        if repaired_case_count > 0:
            get_db().commit()

    return app


app = create_app()


if __name__ == "__main__":
    app.run(
        debug=False,
        use_reloader=False,
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "5050")),
    )
