# 数据和输出规范

## 导入

支持 XLSX/CSV/TSV；旧 XLS 先用当前表格工具转换。运行示例：

```text
python scripts/normalize_exports.py export.xlsx --handle-column 达人昵称 --grain video --output input.json
python scripts/normalize_exports.py creators.csv --grain creator --output input.json
```

--header-row 为 1 起算；默认在前 30 行找表头。多工作表明确选择 --sheet。账号列可用表头或 #1 列序号；不明确时不把显示昵称或 ID 当用户名。

video 粒度：同文件 handle+视频 ID 完全重复行只计一次；同 ID 指标冲突要保留并标记，不默默选高值。无视频 ID 的行不能自动认定不重复。

creator 粒度：同一账号多行快照不相加；保留全部来源行，选最新需要明确时间及口径。不同报表期间/快照也不能直接相加。保留源文件及原行号，缺少账号行单列。

输入 JSON 包含 sources、stats、creators、unmapped。每位 creator 包含 handle、profile_url、source_refs、records（原始字段）、warnings、status=pending。长 ID 始终文本。异常数字 ID=0 的记录不叫有效视频。

## 研究结果 JSON

```json
{
  "research_date": "2026-11-13",
  "creators": [{
    "handle": "example",
    "status": "email_found",
    "contacts": [{
      "kind": "email", "value": "business@example.com",
      "source_url": "https://www.tiktok.com/@example",
      "evidence": "Business: business@example.com",
      "access_date": "2026-11-13", "source_type": "profile_bio",
      "ownership": "direct_profile", "public_business": true,
      "verified_public": true
    }],
    "leads": [],
    "checks": [{"stage": "profile", "url": "https://www.tiktok.com/@example", "outcome": "completed"}],
    "followup_status": "未联系", "notes": "投递未验证"
  }]
}
```

状态：pending、email_found、other_contact、needs_review、not_found_public、blocked_login、page_unavailable、identity_unresolved。

步骤：profile、bio_links、associated_accounts、targeted_search；结果 completed、not_applicable、blocked。not_applicable 给出 reason。待复核邮箱、未打开 IG 等放 leads：kind、value、source_url、reason，不充当已核实联系方式。

## Excel

“达人联系表”至少含：达人昵称、主页链接、公开商务邮箱、其他合作入口、查找状态、跟进状态、备注。按需要加入来源真实的业务指标。没有要求就不添加粉丝/均播，不套用筛选门槛。跟进状态默认未联系，可选已联系/已回复/已合作/暂不合作；续作保留用户修改。

“数据来源”按每条联系信息记录：达人昵称、联系方式种类、联系方式值、来源URL、证据、来源类型、检索日期、核查层级、限制。无邮箱者也至少保留检查/状态记录。

“缺少账号记录”保留原文件、sheet、原行号、必要字段、视频/达人 ID（文本）和无法定位原因。对账源行数，不猜归属。

URL 保留完整文本与原生可点击链接；多个入口分行或分列，不隐藏第二条地址。冻结表头、筛选、合理列宽；金额、计数、日期用对应类型，长 ID 用文本。VV 合计、报表期间表现和账号均播分开，不把未知数值填零。

```text
python scripts/validate_enrichment.py input.json --results results.json
python scripts/validate_enrichment.py input.json --results results.json --workbook contacts.xlsx
```

实际受阻时可用 --allow-incomplete 输出明确的部分完成报告；它不会忽略虚假证据、重复达人或丢失输入记录。交付应说清主页首轮与完整深挖的区别，不把 IG 线索数算成核实邮箱数。
