# AI_CONTEXT.md

> 本文件是本项目所有 AI Coding Agent 共用的持久化项目上下文。
>
> This file is the shared persistent project context for all AI coding agents.
>
> 本文件只记录对未来 Agent 有长期价值的信息，保持简洁、准确、当前有效。
>
> Keep this file concise, accurate, and representative of the current project state.

---

# 1. 项目概览 / Project Overview

## 项目用途 / Purpose

**AI 智装管家（SmartHome Planner）**：面向大众业主、独立工长与小型系统集成商的"空间排雷与弱电规划"轻量化推演沙盒。帮助用户在家装前排查空间干涉、精算物料用量与预算、规划全屋弱电网络拓扑，并通过 AI（第三方大模型）提供一句话记账分类、网络拓扑诊断报告、物料行情估价等能力。

商业化方向（规划中）：CPS 导购佣金、流量主广告、Pro 专家版 SaaS 订阅。详见 `README.md` / `SmartHome_Planner_Project_Plan.md`。

## 当前阶段 / Current Stage

开发阶段（Development）。所有核心功能模块已可用，但无账号体系、无云端数据同步、无自动化测试。

## 技术栈 / Technology Stack

- 主要语言：JavaScript（前端，原生无框架）、Python 3（后端）
- 前端框架：**无框架、无构建系统**，纯静态 HTML/CSS/JS 多页结构；2D 沙盒使用 HTML5 Canvas/DOM 拖拽
- 后端框架：FastAPI + uvicorn（pydantic v2）
- AI 引擎：第三方 OpenAI 兼容格式大模型 API（`openai` 包的 `AsyncOpenAI` 客户端），**不做本地推理**
- 数据库：**无**。全部数据持久化依赖浏览器 `localStorage` / `sessionStorage`（规划中：Supabase / 云开发）
- 基础设施：本地运行（后端 `127.0.0.1:8000`，前端纯静态文件）

---

# 2. 项目架构 / Architecture

## 整体架构 / High-Level Architecture

"前端 UI 驱动 + 轻量后端代理"架构：

- **前端**：静态多页应用。`index.html`（独立官网/落地页）→ `app.html`（工作台 Shell，侧边栏 + 单 `<iframe id="app-frame">` 承载 5 个业务模块，Hash 路由 `#calculator` / `#network` / `#sandbox` / `#compare` / `#ledger`，支持 hashchange 前进后退）。
- **模块隔离**：每个子模块页面头部都有一行防套壳脚本 `if (window.self === window.top) window.location.replace('app.html#xxx')`，直接访问会被重定向回工作台对应路由。**新增子模块必须保留该机制。**
- **主题同步**：`app.html` 通过 `localStorage('shp_theme')` + `postMessage` 广播向各 iframe 同步 light/dark 主题，各模块内均有 `initThemeSync` 监听。
- **后端**：`backend/main.py` 单文件 FastAPI 服务，作为 LLM 调用代理层（Prompt 工程 + 输入拦截 + 密钥隔离），密钥全部经 `.env` 注入（`LLM_API_URL` / `LLM_API_KEY` / `LLM_MODEL_NAME`），`.gitignore` 已排除 `.env`。
- **前后端通信**：前端 `fetch` 硬编码 `http://127.0.0.1:8000`，后端 CORS 全开放（`allow_origins=["*"]`）。

## 主要模块 / Important Modules

| 模块 / Module | 作用 / Purpose | 当前状态 / Status |
| ------------- | -------------- | ----------------- |
| `index.html` | 独立官网/落地页，CTA 与卡片跳转至 `app.html#route` | 已完成 |
| `app.html` | 工作台 Shell：Hash 路由、iframe 加载、防抖/竞态处理、侧边栏折叠、主题广播、移动端动态胶囊导航 | 已完成 |
| `smart_calculator.html`（算料管家） | 逐房间录入尺寸，实时汇总墙漆/地砖/墙砖/柔性防水/刚性防水用量（含门窗扣减与损耗系数） | 已完成 |
| `network_planner.html`（弱电预演） | Mesh / AC+AP 组网选型、设备清单勾选、PoE/非 PoE 交换机与路由器推荐、弱电箱预设、安全警告 | 已完成 |
| `2d_sandbox.html`（空间沙盒，最大模块 ~3000 行） | mm 制全局比例尺、图元拖拽与碰撞干涉检测、Wi-Fi 信号环、户型图上传/标定/锁定、全局相机（缩放/平移/无限画布）、AI 网络拓扑诊断（双模式）、AI 物料估价（BOM 流转）、双轨打印导出、localStorage 自动保存 | 已完成，持续迭代中 |
| `material_compare.html`（建材知识库） | 建材科普：国标术语、优缺点横评、避坑指南，支持 PDF 导出 | 已完成 |
| `ai_ledger.html`（智能记账本） | 账单管理 + 预算管控（默认 30 万，`shp_ledger_budget`），调用后端实现一句话记账自动分类 | 已完成 |
| `backend/main.py` | FastAPI LLM 代理层（见下方 API 清单） | 已完成 |

## 后端 API 清单 / Backend API

| 路由 | 方法 | 说明 |
| ---- | ---- | ---- |
| `/api/health` | GET | 健康检查 |
| `/api/parse-ledger` | POST | 一句话记账分类：本地拦截（≤100 字符 + 敏感词黑名单）→ 记账提取引擎 Prompt → JSON 输出（max_tokens=150） |
| `/api/analyze-layout` | POST | 网络拓扑诊断：入参 `layout_data` / `report_mode`（normal/geek）/ `spatial_relations`；安全前言 + 模式分支 + 空间防幻觉条款动态组装 Prompt（max_tokens=800） |
| `/api/estimate` | POST | 物料估价：入参 `location` / `items`；造价师人设，输出 `{html_report, total_cost}`，动态注入当前日期、一线/二线品牌分层报价要求与免责声明（max_tokens=1500） |

## 重要依赖 / Important Dependencies

- 后端：`fastapi`、`uvicorn[standard]`、`pydantic`、`python-dotenv`、`openai`（见 `backend/requirements.txt`，仅此五个）
- 前端：零第三方依赖（无任何 npm 包、无 CDN 库）

---

# 3. 项目开发规则 / Development Rules

- **密钥安全**：任何真实 API 密钥严禁写入代码或 `.env.example`，只允许存在于本地 `.env`（已被 `.gitignore` 排除）。
- **防套壳**：子模块页面头部第 5 行的 `window.self === window.top` 重定向脚本必须保留。
- **文案规范（去焦虑化）**：面向用户的 UI 文案与报错信息须专业、客观，禁止制造焦虑的表述；后端报错信息纯文本、无表情符号。
- **`<script>` 注释禁忌**：script 标签内的注释中禁止出现 `</script>` 字面量（会导致 HTML 解析提前截断）。
- **多级弹窗时序**：连续弹出多个弹窗必须使用 `setTimeout` 异步队列（约 350~400ms），等待上一弹窗关闭动画结束后再弹下一层，否则会争抢 DOM 导致节点丢失。
- **最小修改原则**：本项目无测试覆盖，修改大文件（尤其 `2d_sandbox.html`）前必须先 Read 同步真实内容，避免基于过期文本替换。

---

# 4. 当前项目状态 / Current Status

## 整体状态 / Overall Status

五大前端模块与后端三条 AI 业务链路（记账分类 / 拓扑诊断 / 物料估价）均已跑通，处于持续体验打磨阶段。最近提交集中在移动端导航适配、主题样式与 AI 诊断/估价的重做按钮逻辑。

## 已完成 / Completed

- 官网 → 工作台 → 五模块的完整产品闭环（Hash 路由、防套壳、主题同步）
- 算料管家、弱电预演、建材知识库的纯前端计算/展示逻辑
- 2D 沙盒：相机系统、干涉检测、户型标定、AI 诊断三级前置校验（信号源 → 墙体警告 → 分析区域框选）、BOM 估价缓存与按钮三态、双轨打印导出与动态 PDF 文件名
- 智能记账本：localStorage 持久化、预算管理、后端一句话分类联调
- 后端：输入物理拦截层、OpenAI 兼容调用引擎、空间防幻觉与时效性报价 Prompt 工程

## 进行中 / In Progress

- 2D 沙盒交互与 AI 报告质量的持续调优（近期多轮迭代焦点）

## 阻塞问题 / Blocked

- 无 / None

## 已知问题 / Known Issues

- CORS 全开放（`allow_origins=["*"]`），上线前必须收敛为具体前端域名
- 前端硬编码 `http://127.0.0.1:8000`，无环境配置机制，无法直接部署到远程
- 无任何自动化测试；后端启动依赖用户手工配置 `.env`
- 无账号体系与云端同步（Roadmap Phase 5 未启动）

---

# 5. 当前任务 / Active Tasks

当前无由 Agent 记录的进行中任务。最近工作（见 Git 历史）：移动端导航栏样式优化、主题切换样式、AI 诊断/估价重做按钮逻辑、全局相机系统。

---

# 6. 重要技术决策 / Important Decisions

## 决策 1：纯静态前端 + 单文件后端代理，不引入构建系统与框架

**日期 / Date:** 项目立项起（2026 上半年）

**决定 / Decision:** 前端保持原生 HTML/CSS/JS 多页 + iframe 路由；后端仅作为 LLM 代理层，不承担业务数据持久化。

**原因 / Reason:** 控制运维与迁移成本，快速验证产品；LLM 密钥不能暴露在前端，必须经后端代理。

**影响 / Impact:** 修改任何功能都在对应单文件内完成；跨模块共享能力靠约定的 `localStorage` 键名（`shp_theme`、`shp_ledger_*`、`shp_sandbox_state_v1` 等）与 `postMessage` 广播，不存在公共模块文件。

## 决策 2：AI 幻觉遏制采用"前端预计算 + Prompt 注入"双层防御

**日期 / Date:** 2026-08

**决定 / Decision:** 设备间物理距离由前端预计算为自然语言（`spatial_relations`）注入后端 Prompt；后端 Prompt 明确"面积仅为跨度包围盒""仅 2D 俯视、无 Z 轴信息"等限制条款，禁止模型输出绝对面积与臆想高度。

**原因 / Reason:** 直接让 LLM 从坐标推算距离/面积会产生幻觉，影响报告可信度。

**影响 / Impact:** 修改诊断链路时须同时维护前端预计算与后端 `build_spatial_guard` 条款的一致性。

---

# 7. 重要约束 / Important Constraints

- 后端服务固定监听 `127.0.0.1:8000`（`python backend/main.py`）；`.env` 三项配置（`LLM_API_URL` / `LLM_API_KEY` / `LLM_MODEL_NAME`）缺失时服务拒绝启动。
- LLM 调用均为 OpenAI 兼容的 `chat.completions` + `response_format={"type": "json_object"}`，并强制 `max_tokens` 上限（150 / 800 / 1500）防滥用。
- 用户输入拦截标准：记账文本 ≤100 字符 + 敏感词黑名单，拦截发生在调用大模型之前。
- 项目运行于 Windows（PowerShell），命令行不支持 `&&`，须用 `;` 分隔。

---

# 8. 最近的重要变化 / Recent Significant Changes

- 2026-08 — 建立跨 Agent 协作规范：新增 `AGENTS.md` 与本文件（未跟踪，未提交）。
- 2026-08 — 后端新增 `/api/estimate` 物料估价端点（造价师 Prompt + 动态时间注入 + 分层报价）；`/api/analyze-layout` 增加 `spatial_relations` 防幻觉参数。
- 近期（见 `git log`）：移动端动态胶囊导航重构、主题切换样式优化、AI 诊断/估价"重新诊断/重新估价"按钮、全局相机系统（缩放/平移/无限画布）、建材对比重构为知识库。

---

# 9. 下一步建议 / Next Recommended Actions

1. 收敛 CORS 白名单并将后端地址抽为前端可配置常量，为部署做准备。
2. 为后端三条 API 链路补充最小自动化测试（如 pytest + httpx 的输入拦截与响应结构测试）。
3. 按 Roadmap Phase 5 推进账号体系与云端数据同步（Supabase / 云开发）选型。

---

# 10. 上下文维护规则 / Context Maintenance

本文件描述"项目现在是什么状态"，而不是"项目过去发生过什么"。信息过期时应更新、删除或合并，不要无限追加历史。未知信息标记为 `UNKNOWN`，不猜测。

维护总则见 `AGENTS.md`。
