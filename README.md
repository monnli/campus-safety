# 黔视护苗 · 校园安全智能监控系统

竞赛项目「黔视护苗」主程序位于 **`campus-safety/`** 目录。

## 快速开始

环境准备、手动启动与 **Windows 一键启动（`start.bat`）** 见：

[campus-safety/docs/部署说明.md](campus-safety/docs/部署说明.md)

功能说明见 [campus-safety/docs/用户手册.md](campus-safety/docs/用户手册.md)。

## 推送到 GitHub（首次）

1. 在 GitHub 网页新建仓库：**New repository**，仓库名自定（例如 `qianshi-humiao`），**不要**勾选「Add a README」（保持空仓库即可）。
2. 在本机 `code` 目录打开终端，执行（将 `你的用户名` 与 `仓库名` 换成实际值）：

```bash
git remote add origin https://github.com/你的用户名/仓库名.git
git push -u origin main
```

若 GitHub 要求登录，可使用 **Personal Access Token** 代替密码（GitHub → Settings → Developer settings → Personal access tokens），或使用 **GitHub Desktop**、**SSH 密钥** 等方式推送。

当前默认分支为 **`main`**。

## 仓库说明

- 请勿将含真实密钥的 `backend/.env` 提交到公开仓库；使用 `backend/.env.example` 自行复制配置。
- `*.pt` 模型权重、录像与告警片段等已列入 `.gitignore`，克隆后请按部署说明自行准备。
