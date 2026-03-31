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
【铁律：字数锁死与短句化写作】
- 强制字数：全文总字数必须严格控制在 1100 到 1200 字之间，绝对禁止超过！一旦当前段落达到字数上限，必须立刻结尾并强行转入下一情节。
- 强制短句：严禁使用任何超过 25 字的长句！必须采用“动作驱动”而非“环境驱动”。多写“你做了什么”，绝不要写“云是什么样、风是什么味道”。删掉所有虚无缥缈的形容词！
- 段落字数锁死配置（绝对不可增删段落）：
  > 第 1 段（开场）：150 字。黄金反问句开头，代入本地化姓名，直接点明极惨的底层现状。
  > 第 2 段（受难）：200 字。残酷压迫降临或危机爆发，动作节奏要快。
  > 第 3 段（外挂觉醒）：250 字。注意【禁令】：绝对禁止详细描写寻找、打开外挂的过程（如怎么撕开包装、怎么撬锁），必须直接跳到外挂“使用后”的震撼效果！
  > 第 4 段（全场震惊打脸）：300 字（全篇高潮）。重点放在周围人、反派的强烈的反应上。
  > 第 5 段（结局反转）：200 字。命运彻底翻盘或落幕结尾。

【全模式通用限制】
- 地名泛指：严禁出现真实且具体的县/市级行政区划，必须使用类似“无名野村”、“罗马斗兽场”、“边关驿站”等泛指地名。
- 无外语化：正文中绝对不能出现任何英文字母或外语，所有物件与称呼必须用中文音译或符合时代感的表述。
"""

    if mode == "脑洞爽文":
        mode_rules = """
【专属导演风格：脑洞爽文】
- 删减要求：极度缩减主角的心理活动！
- 描写重心：大幅增加反派（看守、贵族、地主等压迫者）面对降维打击时被当场吓破胆、瑟瑟发抖、甚至跪地求饶的强烈肢体动作描写。
"""
    elif mode == "感官细节":
        mode_rules = """
【专属导演风格：感官细节】
- 描写重心：压缩次要剧情推进。字数全部拨给“外挂物品/食物带来的极致生理战栗”。如：油脂的香气、咀嚼的嘎嘣声、吞咽的快感、碳水多巴胺爆炸的极致满足。
"""
    elif mode == "真实模拟":
        mode_rules = """
【专属导演风格：真实模拟】
- 描写重心：彻底抹除个人英雄主义。字数全部拨给“普通人在历史车轮下面临的残酷生存压力”、“乱世中身不由己的无力感与血汗泥泞”。
"""
    else:
        # Default back to 脑洞爽文
        mode_rules = """
【专属导演风格：脑洞爽文】
- 删减要求：极度缩减主角的心理活动！
- 描写重心：大幅增加反派（看守、贵族、地主等压迫者）面对降维打击时被当场吓破胆、瑟瑟发抖、甚至跪地求饶的强烈肢体动作描写。
"""

    return f"你现在是一名顶级的暴风骤雨风格视听导演。请严格遵守以下硬核脱水指令：\n{global_rules}\n{mode_rules}"

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
            msgs = [
                {"role": "system", "content": system_content},
                {"role": "user", "content": f"时代背景：{req.era}，场景/核心舞台：{req.location}，底层身份：{req.identity}，核心元素：{req.reversal}"}
            ]
            if req.existing_content:
                msgs.append({"role": "assistant", "content": req.existing_content})
                msgs.append({"role": "user", "content": "请无缝接着你刚才写到一半的内容，直接继续往下续写情节，不要重复上面写过的话，也不要有任何客套。"})
            
            stream = await client.chat.completions.create(
                model="deepseek-chat", 
                messages=msgs,
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