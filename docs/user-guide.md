# App Review Planner 使用教程

把美国区 App Store 用户评论，自动变成：**问题发现 → PRD/版本计划 → 测试用例**，并校验评论到用例的完整追溯链。

---

## 产品能做什么

| 功能 | 说明 |
|------|------|
| 分析范围设定 | 根据 App 链接和分析目标，确定本次关注点 |
| 评论采集 | 支持实时拉取美区评论、离线样例、导入 JSON/CSV |
| 清洗结构化 | 去重、规范化字段，产出清洗报告 |
| 智能 Findings | 用大模型从评论中动态归纳问题（非固定关键词表），并挂证据评论 ID |
| PRD / 版本规划 | 生成需求、优先级（P0/P1/P2）与版本拆分（vNext-1 / vNext-2 / Research） |
| 测试用例 | 为每条需求生成可执行测试思路，并关联需求与原始评论 |
| 追溯校验 | 自动检查：评论 → findings → 需求 → 测试用例是否断链 |
| 可视化进度 | 页面展示各阶段状态与最终交付物 |

---

## 使用前准备

1. 已安装 Python 3.10+  
2. 配置 Moonshot API Key（分析/规划/用例阶段需要）  
3. 启动服务：

```bat
cd /d d:\yuanxue\backend
.\.venv\Scripts\activate.bat
uvicorn app.main:app --reload --port 8001
```

4. 浏览器打开产品页：

**http://127.0.0.1:8001/**

> API 文档（可选）：http://127.0.0.1:8001/docs

---

## 快速上手（推荐演示）

适合第一次使用、无外网或想稳定演示：

1. 打开 http://127.0.0.1:8001/  
2. **App Store URL** 保持默认示例链接即可  
3. **Analysis goal** 填写目标，例如：  
   `improve retention and billing clarity`  
4. **Data source** 选择 `sample（离线缓存演示）`  
5. 点击 **Start**  
6. 等待 1–3 分钟（会调用大模型；若遇限流可能稍慢或走规则兜底）  
7. 页面从上到下查看：  
   - Stages（进度）  
   - Findings（问题发现）  
   - PRD / Version plan（需求与版本）  
   - Test cases（测试用例）  
   - Traceability（追溯是否 OK）  
8. 需要原始 JSON 时，点 **Show JSON**

### 演示成功长什么样

- Overall status 为 `succeeded`  
- Findings、PRD、Test cases 都有内容  
- Traceability 显示 **OK**  
- 每条需求/用例都能看到关联的 review ID  

---

## 三种数据来源怎么选

| 选项 | 何时用 |
|------|--------|
| **sample** | 离线演示、面试官无美区网络、稳定复现 |
| **live** | 有外网，想拉真实最新美区评论 |
| **import** | 面试官提供 JSON/CSV，或你要测「未见过」的数据集 |

### 使用 import

1. Data source 选 `import`  
2. Import path 填仓库相对路径，例如：  
   `data/imports/example_reviews.csv`  
3. 点击 Start  

JSON / CSV 字段说明见：`docs/data-collection.md`。

---

## 页面结果怎么读

### Stages（阶段）
依次为：范围 → 采集 → 清洗 → 分析 → PRD → 测试用例 → 追溯校验。  
某阶段若提示 `[fallback]`，表示大模型暂时失败/限流，系统用规则兜底生成了可追溯结果，任务仍可成功。

### Findings
- 归纳出的用户问题  
- severity / confidence / support  
- 对应的证据评论 ID  

### PRD / Version plan
- 背景与目标  
- 版本计划（先做什么、后做什么、哪些需调研）  
- 每条需求的优先级、关联 finding 与评论  

### Test cases
- 验证目标、步骤、期望结果  
- 关联的需求 ID 与评论 ID  

### Traceability
- `OK`：评论到用例链路完整  
- 若有 issues，说明哪一层断链或覆盖不足  

---

## 分析目标怎么写（示例）

目标越具体，优先级越聚焦，例如：

- `improve retention and billing clarity`  
- `subscription conversion`  
- `low-rating workout usability`  
- `focus on version 8.4.x complaints`  

系统不会写死某个 App 的分类表；换链接、换目标、换导入数据都应能重新分析。

---

## 常见问题

**Q: 打开不了页面？**  
确认 uvicorn 已启动，地址是 `http://127.0.0.1:8001/`（不是 5173）。

**Q: 任务失败，提示缺 API Key？**  
在 `backend/.env` 配置 `MOONSHOT_API_KEY`，然后重启后端。

**Q: testcases 带 fallback？**  
多为接口限流（429）。等一分钟再跑；或接受兜底结果（仍可追溯，可用于演示）。

**Q: live 采不到评论？**  
美区接口可能波动；可改用 `sample` 或 `import` 继续完成分析流程。

**Q: 还需要装 Node 吗？**  
不需要。产品页由 Python/FastAPI 直接提供。

---

## 给面试官的最短路径

1. 配置 `.env` 中的 `MOONSHOT_API_KEY`  
2. `uvicorn app.main:app --port 8001`  
3. 打开 `/`，选 `sample`，点 Start  
4. 查看 Findings → PRD → Test cases → Traceability OK  
