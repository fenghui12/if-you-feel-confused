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
    raw_info: str

class Config(BaseModel):
    base_persona: str
    experts: dict


# --- 系统提示 (System Prompts) ---
CLARIFICATION_PROMPT = """
---
【人设洞察与补全指令】
你的核心任务是深入理解用户，并在对话中持续完善对他的认知。你拥有两种工具来更新用户人设：

1.  **洞察建议 (Suggest Update)**:
    -   **触发时机**: **严格地仅当用户的最新一条消息中**，包含了**新的、且在提供给你的"核心人设"中未被记录**的信息时，你才能使用此工具。
    -   **判断依据**: 你必须将**用户的最新回复**作为**唯一**的判断依据。**严禁**根据你自己的回复、历史对话或已有的"核心人设"信息本身来提炼建议。这是一个发现"新大陆"的过程，而不是总结"已知地图"。
    -   **行动**: 你**必须**在正常回答的结尾处，另起一行，并严格使用以下格式，提出一个陈述句建议：
        `[SUGGEST_UPDATE]根据您提到的信息，我建议将"<提炼后的人设标签>"加入您的人设档案，可以吗？`
    -   **例子**:
        -   核心人设: (空) | 用户最新消息: "我周末要去学Python编程课。" -> LLM正常回复... `[SUGGEST_UPDATE]根据您提到的信息，我建议将"技能：正在学习Python"加入您的人设档案，可以吗？`
        -   核心人设: "家庭情况：已育" | 用户最新消息: "我今天送我女儿上学迟到了。" -> (不触发，因为"已育"信息已存在)
        -   核心人设: (任意) | 用户最新消息: "你好啊" -> (不触发，因为没有新信息)

2.  **必要提问 (Ask for Clarification)**:
    -   **时机**: **仅当**你认为缺少某个**关键信息**就**无法给出有意义的回答**时，才能使用此工具。这是一个**被动**技能，不能滥用。
    -   **行动**: 在你的正常回答结尾处，另起一行，并严格使用以下格式提问：
        `[ASK_FOR_CLARIFICATION]为了更好地规划您的理财，我需要了解您能接受的风险等级是高、中、还是低？`

**核心原则**: 你的目标是成为一个聪明的倾听者，而不是一个健忘的复读机或一个盘问者。始终优先从用户的**新输入**中洞察信息。
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
    # 从前端收到的配置已经是完整的，且提示词是干净的，直接保存
    user_data = {
        "base_persona": config.base_persona,
        "experts": config.experts
    }
    # 不再将CLARIFICATION_PROMPT保存到文件中
    save_user_data(user_data)
    return {"message": "配置更新成功"}

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
        update_info = None
        update_type = None
        
        # 5. 检查是否触发了人设补全或建议
        if "[ASK_FOR_CLARIFICATION]" in raw_reply:
            parts = raw_reply.split("[ASK_FOR_CLARIFICATION]", 1)
            reply = parts[0].strip()
            update_info = parts[1].strip()
            update_type = "question" # 这是一个问题
        elif "[SUGGEST_UPDATE]" in raw_reply:
            parts = raw_reply.split("[SUGGEST_UPDATE]", 1)
            reply = parts[0].strip()
            update_info = parts[1].strip()
            update_type = "suggestion" # 这是一个建议
        else:
            reply = raw_reply.strip()

        # 4. 保存对话历史
        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": reply})
        save_user_data(user_data)

        return {"reply": reply, "update_info": update_info, "update_type": update_type}

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
    """接收用户口语化信息，调用LLM提炼成结构化人设"""
    processing_prompt = """
你是一位专业的人设档案分析师。你的任务是将用户用口语提供的个人信息，提炼成一句简洁、客观、书面化的第三人称事实陈述。
- 不要进行任何对话或反问。
- 只输出提炼后的那一句核心事实。

例子:
用户输入: "嗯...我觉得我工作上可能还是更喜欢稳定一点的吧，不太想冒太大风险。"
你的输出: 在职业选择上，倾向于工作的稳定性而非高风险高回报的机会。

用户输入: "我周末就喜欢宅在家里看看电影打打游戏啥的，不太爱出去。"
你的输出: 业余时间偏好居家活动，如看电影和玩游戏，而非外出社交。
"""
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": processing_prompt},
                {"role": "user", "content": request.raw_info}
            ],
            temperature=0.3, # 使用较低的温度以获得更稳定、可预测的输出
        )
        processed_text = response.choices[0].message.content.strip()
        return {"processed_text": processed_text}
    except Exception as e:
        print(f"Error processing persona info: {e}")
        raise HTTPException(status_code=500, detail="处理人设信息时出错") 