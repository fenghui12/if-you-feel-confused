# AI 助理：一个能与你共同成长的智能伙伴

本项目是一个基于 FastAPI 和原生前端（HTML/CSS/JS）构建的、高度可定制的、拥有动态学习能力的 AI 助理。它不仅仅是一个聊天机器人，更是一个能够通过对话深入了解你，并持续完善自身认知的智能伙伴。

## ✨ 核心功能

- **🧠 智能人设洞察系统 (核心)**：AI 能够"无感地"从你的对话中捕捉新的个人信息点。它会主动提出建议，让你一键确认，从而不断丰富和完善它对你的"认知档案"，实现真正的个性化交流。
- **🎭 多专家模式**: 内置多种专家角色（如情感大师、金融大师），每个角色拥有独立的聊天上下文和专业知识。你可以随时切换角色以获得针对性的建议，而不会互相干扰。
- **🔧 动态配置平台**: 提供一个直观的"设置"界面，让你能够：
    -   自由编辑和丰富你的核心人设。
    -   创建、编辑、删除任何专家角色，定制他们的名称和核心指令。
- **💾 持久化记忆**: 所有的用户人设、专家配置和聊天记录都会被保存在本地的 JSON 文件中，确保你的数据不会丢失，AI 的"记忆"得以延续。
- **🗑️ 安全的记录管理**: 提供一键清空当前专家聊天记录的功能，并配有二次确认弹窗，防止误操作。

## 🤖 工作机制探秘：AI 如何学习？

本项目的灵魂在于其独特的"人设补全"机制。我们摒弃了生硬的、盘问式的交互，代之以更智能、更人性化的学习流程：

1.  **洞察建议 (Suggest Update)**：这是AI学习的主要方式。当你在对话中无意间透露了一个新的信息点（例如，"我周末要去学编程"），AI 会在正常回答的结尾，自然地提出一个建议："根据您提到的信息，我建议将'技能：正在学习Python'加入您的人设档案，可以吗？"。你只需点击确认，AI 的知识库就完成了更新。
2.  **必要提问 (Ask for Clarification)**：仅当 AI 认为缺少某个**关键信息**就**无法给出有意义的回答**时，它才会谨慎地向你提问。例如，在进行理财规划时，它可能会问："为了更好地规划您的理财，我需要了解您能接受的风险等级是高、中、还是低？"

这一套机制确保了用户体验的流畅，让 AI 在潜移默化中加深对你的了解。

## 🛠️ 技术栈

- **后端**: Python, FastAPI
- **LLM API**: DeepSeek API
- **前端**: HTML, CSS, JavaScript (无框架)
- **数据持久化**: 本地 JSON 文件 (`data/user_profile.json`)

## 🚀 快速开始

1.  **克隆仓库**
    ```bash
    git clone <your-repository-url>
    cd <repository-directory>
    ```

2.  **创建并激活虚拟环境** (推荐)
    ```bash
    # Windows
    python -m venv venv
    .\venv\Scripts\activate

    # macOS / Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **安装依赖**
    ```bash
    pip install -r requirements.txt
    ```

4.  **配置 API Key**
    -   将 `.env.example` 文件复制并重命名为 `.env`。
    -   在 `.env` 文件中填入你的 DeepSeek API Key:
        ```env
        DEEPSEEK_API_KEY="sk-xxxxxxxxxxxxxxxx"
        ```

5.  **运行应用**
    ```bash
    uvicorn main:app --reload
    ```

6.  在浏览器中打开 `http://127.0.0.1:8000` 即可开始使用。

## 📁 项目结构

```
.
├── data/
│   └── user_profile.json  # 存储用户人设、专家配置和聊天记录
├── static/
│   ├── script.js          # 前端核心交互逻辑
│   ├── style.css          # 应用样式
│   └── favicon.svg        # 网站图标
├── templates/
│   └── index.html         # 主页面 HTML 结构
├── .env                   # (本地配置) 你的 API Key
├── .env.example           # API Key 配置示例
├── .gitignore             # Git 忽略文件配置
├── main.py                # FastAPI 后端主程序
├── README.md              # 就是你正在看的这个文件
└── requirements.txt       # Python 依赖列表
```
