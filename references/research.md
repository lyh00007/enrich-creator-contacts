# 联系研究规则

## 归属和联系路径

| 层级 | 查找内容 | 判断依据 |
|---|---|---|
| profile | TikTok 简介邮箱、商务说明、实际外链 | 当前主页 handle 与输入一致 |
| bio_links | Linktree/Beacons/LinkMe、官网、媒体资料及公开联系按钮 | 原主页明确指向 |
| associated_accounts | Instagram、YouTube、主号的公开商务简介与官网 | 原主页指向、互链或官方经纪页明确关联 |
| targeted_search | 精确用户名 + business/email/contact/management | 打开实际页面核实，摘要不能单独作证 |

没有外链时记录 not_applicable 及依据，不虚构已访问网址。只有上述四层均有 completed/not_applicable 记录且无阻塞，才可标 not_found_public；某层阻塞时保留 blocked_login/page_unavailable，而不是“无邮箱”。找到可靠邮箱则无需耗尽所有层级。

同名跨平台账号只是候选，头像相似不能单独证明身份。原主页提供 IG 用户名时可以生成链接，但没核实目标页就只叫“主页提供的 IG 线索”。避免抓到推荐账号、用户已关注列表、音乐作者、评论者或视频中品牌客服的邮箱。

## 联系方式判定

- 邮箱保留原始大小写，另用小写排重。依据包括信封图标、Business、Collab、Partnership、Booking、Management、PR、Contact，或清晰的本人公开联系用途。
- 连字符/点可以属于合法邮箱，不自动删除。用途前缀粘连时人工判断，保留原文及理由。语法完整不证明域名正确或可投递。
- 残缺的 `name@gmail` 放 leads，不补后缀。疑似 `gmal.com` 同样放待复核线索，不放已核实商务邮箱列。无法归属本人的地址不接受。
- 普通电话不是 WhatsApp；只有明确商务用途及 WhatsApp 标识/官方 wa.me 才收录。国家码未知就记未知，不根据地区猜测。
- 表单和公开合作私信入口属于其他联系方式，不是邮箱；只记录，不提交。不要把任何普通社交主页都算成“已找到合作入口”。
- 经纪公司通用邮箱可多人共用，保留每位达人的归属证据和团队角色，提醒避免重复发送。不因相同邮箱就删除达人。
- 不使用私人泄露信息，不上传报表给未授权的收费挖掘服务，不做测试外联。个人达人不使用品牌售后/客服邮箱冒充合作地址。

## 证据

每条联系信息保存 kind、value、source_url、evidence、access_date、source_type、ownership、public_business、verified_public。证据仅摘取必要的邮箱邻近文字，不复制完整私人简介。

verified_public 仅表示打开并核实公开来源。SMTP 投递、邮箱存在性和已送达都需要另外的授权与证据；默认没有验证。

## 阻塞

核查超时后的实际页面，区分加载中、登录、失效与错误。允许有限、针对性的重试，不循环猜 URL 或无限搜索。按当时浏览器规则处理登录和验证码，不换账号、浏览器或第三方镜像绕过。继续不依赖阻塞的账号，并保留剩余路径供续作。
