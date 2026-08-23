# Codex ChemDraw Skill

[English](../README.md)

这是一个面向 Windows 的 Codex Skill 与 MCP 服务，用于调用 ChemDraw 和 `cdxml-toolkit` 完成结构绘制、反应式处理、格式转换、图片识别、Office 嵌入和部分实验数据工作流。测试环境使用 MCP Python SDK 2.0.0，同时兼容现有的 SDK 1.x 环境。

本项目是独立社区项目，与 Revvity、OpenAI、Anthropic 或 DECIMER 项目没有隶属或背书关系。

## 主要功能

- 根据名称、SMILES、InChI 等标识解析并绘制结构。
- 使用 ChemScript 结构标识和 RDKit 指纹比较单个分子或有限批次。
- 清理、合并、润色、拆分和渲染 CDXML 反应式。
- 使用本地 DECIMER，或在明确确认后调用远程图片识别。
- 在支持的 Windows 环境中将 CDXML 嵌入 PowerPoint 和 Word。
- 处理选定的 LCMS、SciFinder RDF 和实验记录工作流。
- 查询并调用本机 ChemScript SDK 的全部公开接口目录。
- 可选用带鉴权的 Streamable HTTP 向另一台电脑提供服务，并提供健康状态和 Prometheus 指标。

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
conda run -n cdxml python -m pip install "mcp==2.0.0" "cdxml-toolkit==0.5.17"
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

stdio 仍是默认模式。如需让另一台电脑调用安装了 ChemDraw 的 Windows 主机，请先阅读[项目指南中的 Streamable HTTP 配置](guide.md#streamable-http)，并优先使用加密的专用网络。

## 使用与维护

完整的安装诊断、架构、测试、安全和第三方边界统一放在[项目指南](guide.md)中。参与开发请阅读[贡献说明](../.github/contributing.md)，安全问题请按[安全策略](../.github/SECURITY.md)私下报告。

远程识图默认拒绝上传，必须由调用者明确确认。所有生成或识别出的化学结构在科研使用前都应与原始资料核对。

项目自有代码和文档采用 [MIT License](../LICENSE)；ChemDraw、Office、`cdxml-toolkit` 和 DECIMER 仍分别遵循各自的授权条款。
