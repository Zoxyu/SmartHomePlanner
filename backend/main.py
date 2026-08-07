"""
AI 智装管家 - 轻量级后端服务
职责：为前端提供"一句话智能记账"的语义解析能力（对接 OpenAI 兼容格式的大语言模型）。

安全架构：
1. 本地物理拦截层：长度限制 + 敏感词黑名单，在调用大模型前先行过滤。
2. 大模型调用引擎：严格的 System Prompt 约束 + JSON 强制输出 + max_tokens 限流。
3. 密钥管理：全部敏感配置通过 .env 环境变量注入，代码中不出现任何真实密钥。
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from openai import APIError, AsyncOpenAI
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# 环境变量加载（python-dotenv 读取同目录下的 .env 文件）
# ---------------------------------------------------------------------------
load_dotenv()

LLM_API_URL = os.getenv("LLM_API_URL")
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME")

if not all([LLM_API_URL, LLM_API_KEY, LLM_MODEL_NAME]):
    raise RuntimeError(
        "环境变量缺失：请复制 .env.example 为 .env，并完整填写 "
        "LLM_API_URL、LLM_API_KEY、LLM_MODEL_NAME 三项配置。"
    )

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("smart_home_backend")

# ---------------------------------------------------------------------------
# 任务二：第一道防线 - 本地物理拦截
# ---------------------------------------------------------------------------
# 用户输入最大字符数（按 Unicode 字符计，中文同样按 1 字符计算）
MAX_INPUT_LENGTH = 100

# 基础敏感词黑名单（测试词，命中即拒绝，不进入大模型调用）
SENSITIVE_WORDS = [
    "政治",
    "暴力",
    "枪支",
    "恐怖",
    "赌博",
    "毒品",
    "色情",
]


def sanitize_user_input(text: str) -> str:
    """
    本地物理拦截：在调用大模型之前对用户输入做前置校验。
    - 去除首尾空白后为空，视为无效输入。
    - 长度超过 MAX_INPUT_LENGTH，返回 HTTP 400。
    - 命中敏感词黑名单，返回 HTTP 400。
    """
    cleaned = text.strip()

    if not cleaned:
        raise HTTPException(status_code=400, detail="输入内容为空，请填写有效的记账描述。")

    if len(cleaned) > MAX_INPUT_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"输入内容过长（最多支持 {MAX_INPUT_LENGTH} 个字符），请精简后重试。",
        )

    for word in SENSITIVE_WORDS:
        if word in cleaned:
            logger.warning("敏感词拦截命中：%s", word)
            raise HTTPException(status_code=400, detail="输入内容包含不合规词汇，无法处理。")

    return cleaned


# ---------------------------------------------------------------------------
# 任务三：大模型调用引擎（OpenAI 兼容格式，AsyncOpenAI 异步客户端）
# ---------------------------------------------------------------------------
# 严苛的 System Prompt：限定模型只做装修记账提取，杜绝跑题与注入滥用
SYSTEM_PROMPT = (
    '你是一个且仅是一个装修记账提取引擎。如果用户输入与装修记账无关，'
    '必须严格返回 JSON {"status": "error", "msg": "非记账场景"}。'
    '如果判定为记账，必须返回 JSON '
    '{"status": "success", "amount": 数字, "category": "大类", '
    '"subcategory": "小类", "summary": "摘要"}，'
    "其中 amount 必须为数字类型，其余字段为字符串。"
    "只输出一个合法 JSON 对象，禁止输出任何其他文字、解释或 Markdown 标记。"
)

# AsyncOpenAI 客户端：base_url 与 api_key 均来自环境变量，全程不落盘、不硬编码
llm_client = AsyncOpenAI(api_key=LLM_API_KEY, base_url=LLM_API_URL)


async def call_llm_api(user_text: str) -> dict:
    """
    调用大语言模型解析用户的一句话记账描述。
    约束：
    - response_format 强制 JSON 输出；
    - max_tokens=150 防白嫖限流；
    - temperature=0 保证输出稳定。
    返回解析后的 dict；解析失败或服务异常时抛出 HTTPException。
    """
    try:
        completion = await llm_client.chat.completions.create(
            model=LLM_MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_text},
            ],
            response_format={"type": "json_object"},
            max_tokens=150,
            temperature=0,
        )
    except APIError as exc:
        logger.error("大模型服务调用失败：%s", exc)
        raise HTTPException(status_code=502, detail="记账解析服务暂时不可用，请稍后重试。")

    raw_content = completion.choices[0].message.content or ""
    try:
        result = json.loads(raw_content)
    except json.JSONDecodeError:
        logger.error("大模型返回内容不是合法 JSON：%s", raw_content)
        raise HTTPException(status_code=502, detail="记账解析服务返回异常，请稍后重试。")

    return result


# ---------------------------------------------------------------------------
# 2D 空间布局分析：Prompt 动态组装（"小白" / "极客"双模式分发）
# ---------------------------------------------------------------------------
# 公共安全指令：任何模式下都必须前置注入，确保结论严谨、客观、免责
LAYOUT_SAFETY_PREAMBLE = (
    "分析必须极其严谨、客观。必须明确声明：本结论仅基于 2D 理论推演，"
    "缺乏真实材质射频数据，需结合现场实测。"
    "严禁使用“绝对无死角”“百分之百覆盖”等绝对化词汇。"
    "重要物理限制：你接收到的坐标数据仅为 2D 俯视平面（X/Y轴），"
    "绝对无法获知设备的三维高度（Z轴）。"
    "严禁在报告中出现类似“放置在屋子中间偏上/偏下”这种基于平面图臆想高度的幻觉描述。"
    "但你可以给出通用的施工建议，例如“建议 AP 尽量高挂”。"
)

# 分支 A：小白模式 —— 通俗易懂的家装顾问
LAYOUT_NORMAL_PROMPT = (
    "你的角色是一位通俗易懂的家装顾问。"
    "重点关注：在不同房间刷短视频/玩游戏的延迟体验、路由器穿墙能力评估、光猫位置建议。"
    "语言必须是大白话，让完全没有网络知识的业主也能看懂。"
    "绝对禁止出现 VLAN、PoE、漫游协议、AC+AP、Mesh、核心交换机等任何专业词汇，"
    "如需表达专业概念，必须用生活化比喻替代。"
)

# 分支 B：极客模式 —— 资深弱电工程师
LAYOUT_GEEK_PROMPT = (
    "你的角色是一位资深弱电工程师。"
    "重点关注：AC+AP 与 Mesh 组网的利弊对比与选型建议、"
    "核心交换机端口数量与 PoE 供电预算评估、"
    "智能家居与核心数据的 VLAN 二层隔离建议。"
    "语言可以专业、直接，允许并鼓励使用行业术语，给出可落地的工程参数。"
)

# 模式 -> 分支 Prompt 映射表（便于未来扩展更多报告模式）
LAYOUT_MODE_PROMPTS = {
    "normal": LAYOUT_NORMAL_PROMPT,
    "geek": LAYOUT_GEEK_PROMPT,
}

# 统一输出格式约束：两种模式共用同一 JSON 结构，方便前端统一渲染
LAYOUT_OUTPUT_SCHEMA = (
    "只输出一个合法 JSON 对象，格式严格为："
    '{"summary": "整体评估", "suggestions": ["建议1", "建议2"]}，'
    "其中 summary 为字符串，suggestions 为字符串数组。"
    "禁止输出任何其他文字、解释或 Markdown 标记。"
)


def build_spatial_guard(spatial_relations: str) -> str:
    """
    空间幻觉遏制条款：引入“区域跨度”概念，严禁模型输出绝对面积，
    并要求报告精简聚焦于设备相对距离与信号衰减。
    """
    if not spatial_relations:
        return ""
    return (
        "【严控空间幻觉】前端传给你的面积仅为分析区域的『最大物理跨度包围盒』，绝对不是真实的得房面积，因为真实户型大多是不规则多边形！"
        "你必须严格遵循以下三条原则："
        "1. 报告必须精简！不要输出没用的废话，更不要去分析房屋的长宽比形状。"
        "2. 直接针对该『区域跨度』内的设备相对距离、WiFi 信号穿墙衰减情况做一个精准概述即可。"
        "3. 绝对禁止在报告中直接宣称“您的房子是 XX 平方米”。"
        + spatial_relations
    )


def assemble_layout_system_prompt(report_mode: str, spatial_relations: str = "") -> str:
    """按报告模式动态组装 System Prompt：安全指令 + 模式分支 + 空间防幻觉 + 输出格式。"""
    branch = LAYOUT_MODE_PROMPTS[report_mode]
    return (
        LAYOUT_SAFETY_PREAMBLE
        + branch
        + build_spatial_guard(spatial_relations)
        + LAYOUT_OUTPUT_SCHEMA
    )


async def call_llm_layout_api(
    report_mode: str,
    layout_data: List[Dict[str, Any]],
    spatial_relations: str = "",
) -> dict:
    """
    调用大语言模型分析 2D 空间布局（网络规划推演）。
    约束：
    - response_format 强制 JSON 输出；
    - max_tokens=800 控制报告体量与成本；
    - temperature=0 保证输出稳定。
    返回解析后的 dict；解析失败或服务异常时抛出 HTTPException。
    """
    try:
        completion = await llm_client.chat.completions.create(
            model=LLM_MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": assemble_layout_system_prompt(report_mode, spatial_relations),
                },
                {
                    "role": "user",
                    "content": "以下是设备坐标与尺寸信息（JSON），请据此分析："
                    + json.dumps(layout_data, ensure_ascii=False),
                },
            ],
            response_format={"type": "json_object"},
            max_tokens=800,
            temperature=0,
        )
    except APIError as exc:
        logger.error("大模型服务调用失败（布局分析）：%s", exc)
        raise HTTPException(status_code=502, detail="布局分析服务暂时不可用，请稍后重试。")

    raw_content = completion.choices[0].message.content or ""
    try:
        result = json.loads(raw_content)
    except json.JSONDecodeError:
        logger.error("大模型返回内容不是合法 JSON：%s", raw_content)
        raise HTTPException(status_code=502, detail="布局分析服务返回异常，请稍后重试。")

    return result


# ---------------------------------------------------------------------------
# 任务四：API 路由
# ---------------------------------------------------------------------------
app = FastAPI(
    title="AI 智装管家 后端服务",
    description="提供一句话智能记账语义解析等轻量能力。",
    version="0.1.0",
)

# CORS 中间件：允许前端跨域调用（上线前建议收敛 allow_origins 为具体域名）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class LedgerParseRequest(BaseModel):
    """一句话记账请求体。"""

    text: str = Field(..., description="用户的一句话记账描述", min_length=1)


class LayoutRequest(BaseModel):
    """2D 空间布局分析请求体。"""

    layout_data: List[Dict[str, Any]] = Field(
        ...,
        description="设备坐标与尺寸信息列表，每项包含名称/坐标/尺寸等字段",
        min_length=1,
    )
    report_mode: str = Field(
        default="normal",
        description='报告模式："normal"（小白通俗版）或 "geek"（极客专业版）',
    )
    spatial_relations: str = Field(
        default="",
        description="前端预计算的设备间物理距离自然语言描述，用于注入防幻觉 Prompt",
    )


@app.get("/api/health")
async def health_check():
    """健康检查接口，供部署监控使用。"""
    return {"status": "ok"}


@app.post("/api/parse-ledger")
async def parse_ledger(request: LedgerParseRequest):
    """
    一句话智能记账入口：
    1. 本地物理拦截（长度 / 敏感词）；
    2. 调用大模型提取记账要素；
    3. 非记账场景返回 422，记账成功返回结构化数据。
    """
    safe_text = sanitize_user_input(request.text)
    result = await call_llm_api(safe_text)

    if result.get("status") == "success":
        return result

    # 大模型判定为非记账场景：原样透传错误信息，使用 422 与系统错误区分
    msg = result.get("msg", "非记账场景")
    return JSONResponse(status_code=422, content={"status": "error", "msg": msg})


@app.post("/api/analyze-layout")
async def analyze_layout(request: LayoutRequest):
    """
    2D 空间布局分析（网络规划推演）入口：
    1. 校验报告模式合法性，动态组装对应 Prompt；
    2. 调用大模型输出结构化分析结论；
    3. 统一返回 {"summary": ..., "suggestions": [...]}。
    """
    if request.report_mode not in LAYOUT_MODE_PROMPTS:
        raise HTTPException(
            status_code=400,
            detail='report_mode 取值非法，仅支持 "normal" 或 "geek"。',
        )

    result = await call_llm_layout_api(
        request.report_mode, request.layout_data, request.spatial_relations
    )

    # 兜底校验：确保返回结构符合约定，缺字段时补齐，避免前端解析报错
    summary = result.get("summary", "")
    suggestions = result.get("suggestions", [])
    if not isinstance(suggestions, list):
        suggestions = []

    return {"summary": summary, "suggestions": suggestions}


# ---------------------------------------------------------------------------
# 区域估价：接收沙盒流转的 BOM 清单，调用大模型生成当地行情概算单
# ---------------------------------------------------------------------------
class EstimateRequest(BaseModel):
    """区域估价请求体"""

    location: Dict[str, str] = Field(..., description="省市信息")
    items: List[Dict[str, Any]] = Field(..., description="图元清单")


ESTIMATE_PROMPT = (
    "你是一个专业的家装预算造价师。"
    "用户会提供所在的省市，以及2D图纸上提取的硬装/软装/家电清单（包含物理长宽，单位mm）。"
    "请结合当地近一年的真实物价、人工费行情，给出一份概算单。"
    "要求："
    "1. 必须以 HTML 格式输出排版（使用 <table>, <th>, <td>, <p>, <ul> 标签），直接可以在前端 div 中渲染。"
    "2. 严禁使用任何 Markdown 标记（不要有 ```html 这种外壳）。"
    "3. 强制输出一个合法的 JSON 对象，格式为：{\"html_report\": \"<p>你的HTML内容</p>\", \"total_cost\": 25000}，其中 total_cost 为你估算的整体开销总价（必须为纯数字）。"
)


@app.post("/api/estimate")
async def estimate_bom(request: EstimateRequest):
    """
    接收沙盒流转的数据，调用大模型生成当地行情估价报告。
    动态注入当前系统时间，使模型结合最新宏观经济与物价走势给出时效性预估。
    """
    user_content = json.dumps(request.model_dump(), ensure_ascii=False)
    current_date = datetime.now().strftime("%Y年%m月%d日")

    dynamic_prompt = ESTIMATE_PROMPT + (
        f"\n\n当前系统时间是：{current_date}。请务必结合该时间节点近期的宏观经济、房地产市场走向及当期物价，"
        "预估最新人工与辅材成本。请在概算单中，通过添加备注说明或者单价区间的方式，"
        "展示【全国一线大牌】与【二线/本地高性价比品牌】的价格分层差异。"
        "允许价格基于不同地域和真实行情产生合理浮动，但须保持相对的逻辑连贯性。"
        "在报告最末尾，必须以显著格式添加免责声明："
        "“注：以上价格基于当前时效（及市场趋势）预估，受地域、品牌定级及实际施工条件影响，仅供采购决策参考。”"
    )

    try:
        completion = await llm_client.chat.completions.create(
            model=LLM_MODEL_NAME,
            messages=[
                {"role": "system", "content": dynamic_prompt},
                {"role": "user", "content": user_content},
            ],
            response_format={"type": "json_object"},
            max_tokens=1500,
            temperature=0.2,
        )
    except APIError as exc:
        logger.error("大模型估价调用失败：%s", exc)
        raise HTTPException(status_code=502, detail="估价服务不可用")

    raw_content = completion.choices[0].message.content or ""
    try:
        result = json.loads(raw_content)
    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail="大模型返回格式错误")

    return result


# ---------------------------------------------------------------------------
# 启动入口
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False, use_colors=False)
