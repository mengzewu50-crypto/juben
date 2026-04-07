import json
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
from openai import AsyncOpenAI
import sqlite3
import hashlib
import secrets
from fastapi import Header
from fastapi.responses import JSONResponse

app = FastAPI()

def get_db():
    conn = sqlite3.connect("juben.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, user_id INTEGER)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS scripts (id TEXT PRIMARY KEY, user_id INTEGER, timestamp INTEGER, pinned INTEGER, tags TEXT, content TEXT)''')
        
        # 检查指定的默认账号是否存在，如果不存在则强制创建
        cur = conn.execute("SELECT * FROM users WHERE username='17681953047'")
        user = cur.fetchone()
        if not user:
            pwd_hash = hashlib.sha256("wmz164804992".encode()).hexdigest()
            conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", ("17681953047", pwd_hash))

init_db()
app.mount("/static", StaticFiles(directory="static"), name="static")

def get_system_prompt(mode: str) -> str:
    global_rules = """
【最高铁律：配音级纯净度与逻辑死锁（违者必重写）】
1. 绝对纯净叙事：全文只能由连贯的自然段组成！【绝对禁止】输出任何形式的“第一部分”、“阶段一”、小标题或序号！直接写正文！
2. 配音级字数统计：全文【除去标点符号的纯文字配音字数】必须严格控制在 1100字 至 1300字 之间。
3. 零对话原则：全篇禁止任何人物长篇对话。所有冲突必须通过“动作、环境、物理反馈、神态崩塌”来呈现。
4. 强制第二人称：全篇必须使用“你”作为视角。
5. 时代常识绝对锁定（防关公战秦琼）：所有行为、环境建筑和阶级互动必须【绝对严谨地符合】所设定的时代背景！现代社会绝不允许出现卖血等违背常识的桥段。
6. 智能动态补全原则：如果用户输入的【场景/转场】为空白，或者提示词中出现“请根据时代和身份自动推演”的字样，你必须根据已有的【时代背景】和【底层身份】自动推演并补全一个极其合理的写实场景。绝不允许跨时代乱编！（例如：1970年浙江的农民，场景必须自动设定为公社、田埂或破瓦房）。
"""

    if mode == "感官细节":
        mode_rules = """
【模式：感官细节（全感官ASMR级别体验）】
- 强制开场白（必须作为全文第一句话，直接开始，绝对不准加标题）：
  “在【具体时代背景】下，一个【底层的特定身份】偶然零距离体验到【被阶级垄断的顶级物品/享受】到底有多爽？你叫【名字】……”
- 无缝剧情指令（严禁分点作答，直接写成连贯的小说自然段）：
  开场后，先用约250字描写极其恶劣的劳作环境和肉体濒临极限的匮乏感；接着用约250字写初次接触该物品时不受大脑控制的生理本能；然后用约600字放慢动作十倍，极致放大该物品的材质、触感、气味或声音反馈，写出颅内高潮的纯粹生理爽感；最后用约100字留下不可思议的长叹，果断收尾。
"""
    elif mode == "脑洞爽文":
        mode_rules = """
【模式：脑洞爽文（降维打击）】
- 强制开场白（必须作为全文第一句话，直接开始，绝对不准加标题）：
  “在【具体时代背景】下，一个【底层的特定身份】掏出【现代廉价工业品】逆袭到底有多爽？你叫【名字】……”
- 无缝剧情指令（严禁分点作答，直接写成连贯的小说自然段）：
  开场后，先用约200字迅速把主角逼入绝境，反派极度傲慢；接着用约200字写主角掏出现代物品，反派用落后认知嘲笑；然后用约500字写物品爆发物理/化学效应，刻画反派恐惧磕头的丑态；最后用约300字写实质性的阶级逆袭，随机侧重描写权力互换或财富掠夺，果断收尾。
"""
    elif mode == "真实模拟":
        mode_rules = """
【模式：真实模拟（日常阶级壁垒与微观苦难）】
- 强制开场白（必须作为全文第一句话，直接开始，绝对不准加标题）：
  “在【具体时代背景】下，一个【底层的特定身份】想要【实现某个看似寻常的生活目标】到底有多难？你叫【名字】……”
- 无缝剧情指令（严禁分点作答，直接写成连贯的小说自然段）：
  开场后，先用约250字引出对“日常目标”的极度渴望；接着用约250字刻画遭遇的底层社会人情冷暖或阶级壁垒的无声刁难；然后用约600字聚焦为该目标付出的极限剥削与微观挣扎；最后用约100字写出获得残次品回报或希望破灭后的绝望妥协，闭眼长叹，果断收尾。
"""
    else:
        mode_rules = "【专属要求：真实模拟】"

    return f"你是一名配音导演。请【只用一次回答】输出没有任何标签的纯净短剧正文：\n{global_rules}\n{mode_rules}"

# 接入 DeepSeek 官方节点
client = AsyncOpenAI(
    api_key="sk-2ba9677d4b2f4cb08e220021f3c9f93d", 
    base_url="https://api.deepseek.com"
)

class ScriptRequest(BaseModel):
    era: str
    location: str
    identity: str
    reversal: str
    mode: str = "脑洞爽文"
    existing_content: Optional[str] = None

class AuthRequest(BaseModel):
    username: str
    password: str

class ScriptItem(BaseModel):
    id: str
    timestamp: int
    pinned: bool
    tags: str
    content: str
    
class SyncRequest(BaseModel):
    scripts: List[ScriptItem]

def get_user_id(token: str):
    if not token or not token.startswith("Bearer "): return None
    t = token.replace("Bearer ", "")
    with get_db() as conn:
        row = conn.execute("SELECT user_id FROM sessions WHERE token=?", (t,)).fetchone()
        return row["user_id"] if row else None

@app.post("/api/generate_script")
async def generate_script(req: ScriptRequest):
    async def event_generator():
        try:
            system_content = get_system_prompt(req.mode)
            
            # 拦截半空字段，强制大模型根据其他信息自动推演写实场景，且防止跨时代乱编
            era_val = req.era.strip() if req.era else ""
            location_val = req.location.strip() if req.location else ""
            identity_val = req.identity.strip() if req.identity else ""
            reversal_val = req.reversal.strip() if req.reversal else ""

            # 保留原有逻辑：如果全为空，则原样保留（前端传来的可能已经被随机库填充，如果在别的逻辑里被拦截则是空）
            all_empty = not era_val and not location_val and not identity_val and not reversal_val

            if not all_empty:
                if not era_val:
                    era_val = "【请根据场景和身份自动推演一个极其写实的时代，绝不允许跨时代乱编】"
                if not location_val:
                    location_val = "【请根据时代和身份自动推演一个极其写实的场景，绝不允许跨时代乱编】"
                if not identity_val:
                    identity_val = "【请根据时代和场景自动推演一个极其写实的底层身份，绝不允许跨时代乱编】"
                if not reversal_val:
                    reversal_val = "【请根据时代和身份自动推演一个极其写实的逆袭元素/生存考验，绝不允许跨时代乱编】"

            # 清理了多余的用户指令，让大模型专心听系统指令的规矩
            user_msg = f"时代背景：{era_val}，场景：{location_val}，底层身份：{identity_val}，逆袭元素/生存考验：{reversal_val}"
            
            msgs = [
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_msg}
            ]
            if req.existing_content:
                msgs.append({"role": "assistant", "content": req.existing_content})
                msgs.append({"role": "user", "content": "请无缝接着你刚才写到一半的内容，严格按照原定的结构、排版要求和1300纯汉字的篇幅继续往下续写情节。绝对不要重复上面已经写过的话，不要有任何客套，不要强行结尾，请自然地展开接下来的情节！"})
            
            # 物理掐断阀门：1500 tokens 兜底
            stream = await client.chat.completions.create(
                model="deepseek-chat", 
                messages=msgs,
                temperature=0.8,
                max_tokens=4000,
                stream=True
            )
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    yield f"data: {json.dumps({'content': content})}\n\n"
            
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/")
@app.head("/")
async def read_index():
    return FileResponse("static/index.html")

@app.post("/api/auth")
async def auth_user(req: AuthRequest):
    pwd_hash = hashlib.sha256(req.password.encode()).hexdigest()
    with get_db() as conn:
        user = conn.execute("SELECT * FROM users WHERE username=?", (req.username,)).fetchone()
        if user:
            if user["password"] != pwd_hash:
                return JSONResponse({"error": "密码错误"}, status_code=401)
            user_id = user["id"]
        else:
            return JSONResponse({"error": "账号不存在"}, status_code=404)
        
        token = secrets.token_hex(32)
        conn.execute("INSERT INTO sessions (token, user_id) VALUES (?, ?)", (token, user_id))
    return {"token": token, "username": req.username}

@app.get("/api/scripts")
async def get_scripts(authorization: Optional[str] = Header(None)):
    user_id = get_user_id(authorization)
    if not user_id: return JSONResponse({"error": "未登录"}, status_code=401)
    
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM scripts WHERE user_id=? ORDER BY timestamp DESC", (user_id,)).fetchall()
        return [{"id": r["id"], "timestamp": r["timestamp"], "pinned": bool(r["pinned"]), "tags": r["tags"], "content": r["content"]} for r in rows]

@app.post("/api/scripts/sync")
async def sync_scripts(req: SyncRequest, authorization: Optional[str] = Header(None)):
    user_id = get_user_id(authorization)
    if not user_id: return JSONResponse({"error": "未登录"}, status_code=401)
    
    with get_db() as conn:
        # 简单粗暴：删除所有的，再重新插入（同步）
        conn.execute("DELETE FROM scripts WHERE user_id=?", (user_id,))
        for s in req.scripts:
            conn.execute("INSERT INTO scripts (id, user_id, timestamp, pinned, tags, content) VALUES (?, ?, ?, ?, ?, ?)", 
                         (s.id, user_id, s.timestamp, int(s.pinned), s.tags, s.content))
    return {"success": True}