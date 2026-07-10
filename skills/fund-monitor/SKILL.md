---
name: fund-monitor
description: "基金持仓异动监控 — 按板块汇总推送 Bark 通知"
triggers:
  - "基金"
  - "异动"
  - "基金监控"
---

# 基金持仓异动监控

监控用户持有基金涉及的核心股票，按板块分组推送 Bark 异动通知。

## 设计原则

**Skill = 使用说明，不是代码仓库。** 脚本放在 `scripts/`，Skill 只包含：怎么用、注意事项、Cron 配置。不要把 `.py` 文件塞进 Skill 目录。

## 使用方法

### 运行监控
```bash
python ~/AppData/Local/hermes/scripts/fund_monitor.py
```

### 管理基金
```bash
python ~/AppData/Local/hermes/scripts/fund_manager.py list    # 查看列表
python ~/AppData/Local/hermes/scripts/fund_manager.py add <代码>  # 添加
python ~/AppData/Local/hermes/scripts/fund_manager.py remove <代码>  # 删除
```

## 文件结构

```
scripts/
├── fund_monitor.py          # 主监控脚本
├── fund_manager.py          # 基金管理工具
├── my_funds.json            # 基金列表配置
└── stock_utils.py           # 行情获取工具库
```

## 告警规则

| 条件 | 说明 |
|------|------|
| 涨跌 ≥ 3% | 板块内个股大幅波动 |
| 涨跌 ≥ 5% | 突破5%关口 |
| 涨跌 ≥ 9.9% | 涨停/跌停 |

## Cron 配置

```yaml
schedule: "*/5 9-15 * * 1-5"   # 周一~五 9:00-15:59 每5分钟
no_agent: true
script: "fund_monitor.py"
deliver: "origin"
```

## Pitfalls

### Cron 输出中文乱码
Windows 系统用 GBK 编码显示 UTF-8 中文，会导致乱码。**解决**：脚本输出用英文，或无告警时静默退出。

### GitHub Token 被掩码
Terminal 会自动掩码 token、密码等。**解决**：写入临时文件，用完删除。
