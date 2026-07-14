# Codex ChemDraw Skill

[English](../README.md)

这是一个面向 Windows 的 Codex Skill 与 MCP 服务，用于调用 ChemDraw 和 `cdxml-toolkit` 完成结构绘制、反应式处理、格式转换、图片识别、Office 嵌入和部分实验数据工作流。

本项目是独立社区项目，与 Revvity、OpenAI、Anthropic 或 DECIMER 项目没有隶属或背书关系。

## 主要功能

- 根据名称、SMILES、InChI 等标识解析并绘制结构。
- 清理、合并、润色、拆分和渲染 CDXML 反应式。
- 使用本地 DECIMER，或在明确确认后调用远程图片识别。
- 在支持的 Windows 环境中将 CDXML 嵌入 PowerPoint 和 Word。
- 处理选定的 LCMS、SciFinder RDF 和实验记录工作流。

## 环境要求

- Windows 10 或更高版本。
- Python 3.10 或更高版本，推荐使用独立 Conda 环境。
- 已授权并激活的 ChemDraw；Office 功能还需要对应的 Microsoft Office 应用。
- Codex CLI 或 Codex 桌面版。

本仓库不包含 ChemDraw、Office 或 DECIMER 本地模型权重。

## 快速安装

```powershell
git clone https://github.com/ZiChenWang114514/codex-chemdraw-skill.git
Set-Location codex-chemdraw-skill

conda create -n cdxml python=3.12 -y
conda run -n cdxml python -m pip install "cdxml-toolkit==0.5.17"
$python = (conda run -n cdxml python -c "import sys; print(sys.executable)" | Select-Object -Last 1)
Set-ExecutionPolicy -Scope Process Bypass
& .\scripts\install.ps1 -Python $python -Apply -ConfigureMcp
```

重启 Codex 后验证：

```powershell
codex mcp get cdxml-toolkit --json
& "$HOME\.codex\skills\chemdraw\scripts\health_check.ps1" -Python $python
```

安装器只有在指定 `-Apply` 时才会写入；覆盖前会备份已有 Skill 和 MCP 配置。

## 使用与维护

完整的安装诊断、架构、测试、安全和第三方边界统一放在[项目指南](guide.md)中。参与开发请阅读[贡献说明](../.github/contributing.md)，安全问题请按[安全策略](../.github/SECURITY.md)私下报告。

远程识图默认拒绝上传，必须由调用者明确确认。所有生成或识别出的化学结构在科研使用前都应与原始资料核对。

项目自有代码和文档采用 [MIT License](../LICENSE)；ChemDraw、Office、`cdxml-toolkit` 和 DECIMER 仍分别遵循各自的授权条款。
