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


# ---------------------------------------------------------------------------
# 启动入口
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
