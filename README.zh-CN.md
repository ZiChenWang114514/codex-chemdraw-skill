# 面向 Codex 的 ChemDraw Skill

[English](README.md)

这是一个以 Windows 为主要平台的 Codex Skill 与 MCP 适配层，用于有依据地绘制和修改分子、处理反应式、调用 DECIMER 识别图片、解析分析文件，以及在 Word/PowerPoint 中嵌入可编辑的 ChemDraw 对象。

> 本项目是独立集成项目，不隶属于 Revvity，也不分发 ChemDraw 软件或许可证。

## 主要能力

- 采用渐进式披露：Codex 先读取简短路由，再按任务加载工作流、接口签名和领域文档。
- 提供 27 个 MCP 工具，覆盖分子解析与修改、CDX/CDXML、反应式清理与合并、Office OLE、ELN/RDF、LCMS/NMR 和 DECIMER。
- 工具在隔离进程中执行，支持硬超时、进程树终止和结构化错误。
- 修改型任务默认写入新文件；远程 DECIMER 必须显式确认上传。
- 自动发现 Conda/Python 运行时和 Windows 已注册的 ChemDraw。

Skill 的权威入口是 [`skill/chemdraw/SKILL.md`](skill/chemdraw/SKILL.md)，精确接口以自动生成的 [`mcp-signatures.md`](skill/chemdraw/references/mcp-signatures.md) 为准。

## 快速安装

```powershell
git clone https://github.com/ZiChenWang114514/codex-chemdraw-skill.git
cd codex-chemdraw-skill

conda create -n cdxml python=3.12 -y
conda run -n cdxml python -m pip install "cdxml-toolkit==0.5.17"

# 先预览，不写文件、不修改 Codex 配置。
.\scripts\install.ps1 -Python (conda run -n cdxml python -c "import sys; print(sys.executable)")

# 安装 Skill，并在备份后注册 MCP。
.\scripts\install.ps1 -Apply -ConfigureMcp `
  -Python (conda run -n cdxml python -c "import sys; print(sys.executable)")
```

现有 Skill 会先移动到带时间戳的备份目录。只有同时提供 `-Apply` 和 `-ConfigureMcp` 才会更新 Codex MCP 配置。

## 重要说明

- Skill 不会要求你另购或重新激活 ChemDraw。原生 COM 功能只要求当前 Windows 用户会话中的 ChemDraw 已正常激活。
- “已激活但自动化失败”通常是 Python/ChemDraw 位数不匹配、COM 注册指向另一版本、ChemDraw 正在阻塞自动化，或桌面会话权限不同，并不等同于许可证失效。
- 不依赖 ChemDraw 的纯解析与文档工作流仍可使用；原生渲染、CDX 转换和可编辑 OLE 需要 ChemDraw。

完整说明见[安装与诊断](docs/installation.md)、[架构](docs/architecture.md)、[测试门槛](docs/testing.md)和[隐私安全](docs/privacy-and-safety.md)。

## 许可证

本仓库原创代码和文档使用 [MIT License](LICENSE)。ChemDraw、`cdxml-toolkit`、DECIMER、Microsoft Office 和 Codex 分别遵循其自身许可证，详见[第三方声明](THIRD_PARTY_NOTICES.md)。
