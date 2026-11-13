# 达人联系方式深挖

读取导出的 TikTok 达人名单，整理并去重账号，核实公开商务联系方式，生成带来源与跟进状态的 Excel。

## 项目内容

- [技能说明](SKILL.md)：处理流程与使用要求。
- [数据和输出规范](references/data-and-output.md)：输入格式、研究记录和交付规范。
- [联系研究规则](references/research.md)：联系方式归属与公开来源核查规则。
- `scripts/normalize_exports.py`：整理导出的达人名单。
- `scripts/validate_enrichment.py`：校验覆盖范围、联系证据及输出工作簿。
- `agents/openai.yaml`：技能展示信息。

## 使用方式

在支持该技能的环境中安装后，提供 XLSX、CSV 或 TSV 达人名单，并使用 `$enrich-creator-contacts` 调用。完整要求见 [SKILL.md](SKILL.md)。

本项目只查找公开商务联系方式；不自动发送邮件或私信。公开来源核实不等于邮箱投递验证。

## 分类

电商运营与利润核算 / 达人运营工具。

