import os
import json
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import openai

# --- 配置 ---
# 从 .env 文件加载环境变量
load_dotenv()
API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not API_KEY:
    raise ValueError("未找到 DeepSeek API Key，请检查你的 .env 文件。")

# --- 初始化 ---
app = FastAPI()

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# 初始化客户端，指向 DeepSeek API
client = openai.OpenAI(
    api_key=API_KEY,
    base_url="https://api.deepseek.com/v1"
)

DATA_FILE = "data/user_profile.json"

# --- 数据持久化函数 ---
def load_user_data():
    """加载用户数据和聊天记录"""
    if not os.path.exists(DATA_FILE):
        # 如果文件不存在，可能需要一个初始化函数来创建它
        return {"base_persona": "", "experts": {}}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_user_data(data):
    """保存用户数据和聊天记录"""
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# --- Pydantic 模型 ---
class ChatMessage(BaseModel):
    message: str
    mode: str

class ProcessPersonaRequest(BaseModel):
    question: str
    answer: str

class Config(BaseModel):
    base_persona: str
    experts: dict

class PersonaUpdateRequest(BaseModel):
    update_string: str


# --- 系统提示 (System Prompts) ---
CLARIFICATION_PROMPT = """
---
1. 核心身份与使命 (Core Identity & Mission)
你是一个名为 "Echo" 的高级AI，专精于用户画像建模 (User Persona Modeling)。你的唯一使命是：通过对话，被动地、非侵入性地构建和维护一个关于用户的、动态更新的、事实驱动的画像。
你的行为准则基于一条黄金法则：“多听，少问，精准记录”。
2. 核心指令 (Core Directives)
你必须无条件遵守以下规则：
观察优先于盘问 (Observation Over Interrogation): 你的信息来源首选是用户主动给出的信息。[ASK_FOR_CLARIFICATION] 是在万不得已时才使用的最后手段。
格式是绝对的 (Formatting is Absolute): 所有工具的输出必须严格遵循 [TAG]Content 的格式，前后绝不允许有任何多余的解释、前缀或后缀。
最新消息原则 (Latest Message Principle): 你的所有洞察（[SUGGEST_UPDATE]）必须且只能基于用户的最新一条消息。不要回顾历史信息来做新的推断。
只记录有效信息 (Meaningful Information Only): 只对构成用户画像的事实、偏好、目标、关系、重要事件等信息进行洞察。必须忽略日常闲聊、情绪表达或无具体信息的对话填充词（如“好的”、“嗯”）。
原子化更新 (Atomic Updates): 每次 [SUGGEST_UPDATE] 只针对一个Key-Value对。如果用户一句话透露了多条信息，请分多行进行建议。
3. 工具定义与工作流程 (Tools & Workflow)
你在对话中拥有两个工具。在每次回复的结尾，根据以下逻辑决定是否使用它们。
功能: 从用户最新消息中提炼画像信息，并建议新增或更新。
触发条件: 当且仅当 (IF AND ONLY IF) 用户的最新一条消息中，包含可以明确提取为 Key: Value 形式的新画像信息，或与现有画像有冲突/可更新的信息。
执行逻辑:
扫描: 分析用户最新消息，寻找有效信息。
比对: 检查该信息是否关联到“核心人设”中的已有Key。
决策:
更新 (Update): 若Key已存在，生成对该Key的新Value。
新增 (Add): 若Key为全新领域，生成新的Key: Value对。
行动: 在正常对话回复的末尾，另起一行，使用以下格式输出。
格式与要求 (Strict Schema):
格式: [SUGGEST_UPDATE]Key: Value
Key: 必须是一个简短、标准化的名词（例如：职业, 爱好, 目标, 居住地）。禁止使用句子或描述性短语作为Key。
Value: 必须是提炼后的客观信息。
冒号: 必须是英文半角冒号 (:)，其后可跟一个空格。
示例:
场景1 (更新):
核心人设: 体重: 100kg
用户: "我最近健身，体重变成了90公斤。"
你的回复: (正常对话...)
[SUGGEST_UPDATE]体重: 90kg
场景2 (新增):
核心人设: (空)
用户: "我周末要去学Python编程课。"
你的回复: (正常对话...)
[SUGGEST_UPDATE]技能学习: Python
场景3 (不触发):
核心人设: 姓名: 小王
用户: "你好啊"
你的回复: (正常对话，不附加任何工具)
功能: 在信息不足以完成用户明确请求时，进行提问。
触发条件: 当且仅当 (IF AND ONLY IF) 如果不获取一个特定的信息，就绝对无法对用户当前提出的具体问题给出任何有效步骤或建议时。
执行逻辑:
这是一个被动技能。绝不能为了“让回答更完美”或“出于好奇”而使用。如果能给出一个模糊或初步的回答，就不要提问。
格式与要求 (Strict Schema):
格式: [ASK_FOR_CLARIFICATION]问题正文
行动: 在正常对话回复的末尾，另起一行，使用此格式。
示例:
场景1 (合法使用):
用户: "帮我规划一个为期5年的理财计划。"
你的回复: "好的，制定一个长期的理财计划非常棒。不过，计划的风格会因人而异。
[ASK_FOR_CLARIFICATION]为了给您定制计划，我需要了解您能接受的风险等级是高、中、还是低？
场景2 (非法使用):
用户: "我今天心情不好。"
你的回复 (错误示范): [ASK_FOR_CLARIFICATION]为什么心情不好呀？
你的回复 (正确示范): "听到你这么说我很难过，希望你能尽快好起来。如果有什么我能帮忙的，随时告诉我。" (不使用工具)
4. 高级用法：组合指令
触发条件: 当用户的输入同时满足了 [SUGGEST_UPDATE] 和 [ASK_FOR_CLARIFICATION] 的触发条件时。
执行原则: 你必须同时使用这两个工具，并遵循固定顺序。
顺序: 总是先提问，后洞察。
正常对话
[ASK_FOR_CLARIFICATION]
[SUGGEST_UPDATE]
组合示例:
核心人设: (空)
用户: "我最近跟我女朋友闹矛盾了，我该怎么办？"
你的回复:
听到这个消息我感到很遗憾，感情中的矛盾确实很令人揪心。不同的矛盾需要不同的处理方式，如果能了解更多细节，我也许能提供更有针对性的建议。
[ASK_FOR_CLARIFICATION]可以具体说说，是为什么事情闹矛盾吗？
[SUGGEST_UPDATE]情感状况: 恋爱中
---
"""

# 这个字典现在只作为新创建专家的默认模板
DEFAULT_PROMPTS = {
    "casual_chat": "你是一个友好、乐于助人的AI助手，可以和用户进行任何话题的闲聊。",
    "emotional_master": "你是一位情感生活大师，深刻理解人类情感，善于倾听、共情，并能提供富有智慧和同理心的建议。请以关怀、温暖的语气与用户交流。",
    "finance_master": "你是一位金融大师，精通个人理财、投资策略和市场分析。请使用专业、严谨但易于理解的语言，为用户提供金融建议。",
    "tech_master": "你是一位技术大师，对各种前沿科技、编程语言和软件架构都有深入了解。请以清晰、有条理的方式解答用户的技术问题。",
    "career_master": "你是一位职业规划大师，洞悉行业趋势和职场动态。请帮助用户分析自身优势，并为他们的职业发展提供战略性指导。"
}


# --- API 端点 ---
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """提供前端HTML页面"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/config", response_model=Config)
async def get_config():
    """获取所有可编辑的配置信息"""
    user_data = load_user_data()
    # JSON中的提示词现在是干净的，直接返回即可
    return user_data

@app.post("/api/config")
async def update_config(config: Config):
    """更新并保存所有配置信息"""
    # 这里需要采用"读取-修改-写入"模式，以保留聊天记录
    user_data = load_user_data()

    # 更新人设和专家配置
    user_data["base_persona"] = config.base_persona
    
    # 更新专家信息，但保留历史记录
    for expert_key, expert_data in config.experts.items():
        if expert_key in user_data["experts"]:
            user_data["experts"][expert_key]["name"] = expert_data["name"]
            user_data["experts"][expert_key]["prompt"] = expert_data["prompt"]
        else:
            # 如果是新增的专家，初始化其数据结构
            user_data["experts"][expert_key] = {
                "name": expert_data["name"],
                "prompt": expert_data["prompt"],
                "history": []
            }
    
    # 处理被删除的专家
    # 创建一个当前配置中存在的专家键的集合
    current_expert_keys = set(config.experts.keys())
    # 创建一个需要删除的专家键的列表
    deleted_expert_keys = [key for key in user_data["experts"] if key not in current_expert_keys]
    # 删除这些专家
    for key in deleted_expert_keys:
        del user_data["experts"][key]

    save_user_data(user_data)
    return {"message": "配置更新成功"}

@app.post("/api/persona/update")
async def update_persona(request: PersonaUpdateRequest):
    """处理单条人设的更新或新增"""
    update_string = request.update_string.strip()
    try:
        # 按第一个冒号分割，确保Value中可以包含冒号
        key_to_update, new_value = [part.strip() for part in update_string.split(":", 1)]
    except ValueError:
        # 如果格式不正确，则无法处理
        raise HTTPException(status_code=400, detail="更新格式错误，必须为 'Key: Value'")

    user_data = load_user_data()
    # 用 .splitlines() 来正确处理各种换行符
    persona_lines = user_data.get("base_persona", "").splitlines()
    
    updated = False
    new_persona_lines = []
    
    # 遍历现有的每一条人设
    for line in persona_lines:
        stripped_line = line.strip()
        if not stripped_line:
            continue
        try:
            current_key, _ = [part.strip() for part in stripped_line.split(":", 1)]
            if current_key.lower() == key_to_update.lower():
                # 如果key匹配（不区分大小写），则更新该行
                new_persona_lines.append(f"{key_to_update}: {new_value}")
                updated = True
            else:
                new_persona_lines.append(line)
        except ValueError:
            # 保留那些不符合 "Key: Value" 格式的行
            new_persona_lines.append(line)

    # 如果遍历完后发现没有更新任何现有行，说明是新增
    if not updated:
        new_persona_lines.append(f"{key_to_update}: {new_value}")
        
    user_data["base_persona"] = "\n".join(new_persona_lines)
    save_user_data(user_data)
    
    return {"message": "人设更新成功", "new_persona": user_data["base_persona"]}

@app.post("/api/chat")
async def chat(chat_message: ChatMessage):
    """处理聊天请求"""
    mode = chat_message.mode
    user_message = chat_message.message

    user_data = load_user_data()
    
    # 从 user_data 中获取当前模式的干净提示词
    expert_prompt = user_data.get("experts", {}).get(mode, {}).get("prompt")
    if not expert_prompt:
         raise HTTPException(status_code=400, detail="无效的聊天模式或未找到提示词")

    # 在运行时动态拼接完整的系统提示
    full_system_prompt = f"{expert_prompt}\n{CLARIFICATION_PROMPT}\n以下是用户的核心人设，请在回答中始终参考此人设：\n{user_data['base_persona']}"
    
    # 2. 准备上下文
    if mode not in user_data["experts"]:
        user_data["experts"][mode] = {"history": []}
        
    history = user_data["experts"][mode]["history"]
    
    messages = [
        {"role": "system", "content": full_system_prompt}
    ]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    try:
        # 3. 调用LLM
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=1.3,
        )
        
        raw_reply = response.choices[0].message.content
        
        reply = raw_reply
        suggestion = None
        question = None

        # 5. 检查是否触发了建议和提问（可以同时触发）
        if "[SUGGEST_UPDATE]" in reply:
            parts = reply.split("[SUGGEST_UPDATE]", 1)
            reply = parts[0].strip()
            suggestion = parts[1].strip().split("[ASK_FOR_CLARIFICATION]")[0].strip()
            
        if "[ASK_FOR_CLARIFICATION]" in reply:
            parts = reply.split("[ASK_FOR_CLARIFICATION]", 1)
            reply = parts[0].strip()
            question = parts[1].strip()

        # 4. 保存对话历史
        history.append({"role": "user", "content": user_message})
        # 只保存纯粹的对话回复，不含标签
        history.append({"role": "assistant", "content": reply}) 
        save_user_data(user_data)

        return {"reply": reply, "suggestion": suggestion, "question": question}

    except openai.APIError as e:
        print(f"DeepSeek API Error: {e}")
        raise HTTPException(status_code=500, detail=f"DeepSeek 服务暂时不可用: {e.strerror}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")

@app.get("/api/history/{mode}")
async def get_history(mode: str):
    """获取指定模式的聊天记录"""
    user_data = load_user_data()
    history = user_data.get("experts", {}).get(mode, {}).get("history", [])
    return {"history": history}

@app.delete("/api/history/{mode}")
async def clear_history(mode: str):
    """清空指定模式的聊天记录"""
    user_data = load_user_data()
    if user_data.get("experts", {}).get(mode):
        user_data["experts"][mode]["history"] = []
        save_user_data(user_data)
        return {"message": f"模式 '{mode}' 的聊天记录已清空。"}
    else:
        raise HTTPException(status_code=404, detail=f"模式 '{mode}' 不存在。")

@app.post("/api/process_persona_info")
async def process_persona_info(request: ProcessPersonaRequest):
    """接收AI的问题和用户的回答，提炼成结构化的 'Key: Value' 人设。"""
    
    processing_prompt = f"""
你是一位专业的人设档案分析师。你的任务是将AI提出的问题和用户的口语化回答，提炼成一个简洁、客观的 "Key: Value" 格式的陈述。
- Key应该是这个信息点的核心主题（例如：风险偏好, 职业, 爱好）。
- Value是基于用户回答的总结。
- 不要进行任何对话或反问。
- 只输出最终的那一行 "Key: Value"。

---
AI 的问题: "{request.question}"
用户的回答: "{request.answer}"
---

你的输出:
"""
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": processing_prompt},
            ],
            temperature=0.3,
        )
        processed_text = response.choices[0].message.content.strip()
        # 基本的格式验证
        if ":" not in processed_text or len(processed_text.split(':')) != 2:
            print(f"LLM未能生成有效的Key:Value格式，输出为: {processed_text}")
            # 即使格式不理想，也尝试将其作为普通文本处理，而不是直接报错
            # 这可以处理一些意外情况，例如LLM只返回了一个值
            return {"processed_text": f"备注: {processed_text}"}

        return {"processed_text": processed_text}
    except Exception as e:
        print(f"Error processing persona info: {e}")
        raise HTTPException(status_code=500, detail="处理人设信息时出错") 