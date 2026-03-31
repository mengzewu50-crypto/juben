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

SYSTEM_PROMPT = """你是一个专门制作“草根逆袭类”短视频的顶级文案策划。
请根据用户提供的【时代背景】、【具体地点】、【底层身份】和【逆袭元素】，创作一段极具感染力的长篇文案。

【字数严格限制】：
总字数必须严格控制在 1400字 到 1600字 之间！这是一项极其严格的要求！
为了达到字数要求，建议五章内容分配如下：
前四章每章大概200-250字，保持节奏紧凑；
第五章盛大结局和煽情可以达到400-500字左右。
写完后请务必自行检查，如果超出1600字或少于1400字，请精简或扩写细节。

【核心叙事结构】：
1. 黄金悬念开头：用“在XX时代，XX特质真的能当饭吃吗？”切入。
2. 第二人称代入：全程使用“你”来称呼主角。
3. 五章叙事：
   - 第一章：苦难深渊。描写环境恶劣、尊严被践踏。
   - 第二章：异能觉醒。描写特质显露后得到的第一份善意。
   - 第三章：生活小确幸。描写用特质换取基础生存资源的微小逆袭。
   - 第四章：阶层碰撞。描写你与顶级权贵的邂逅与张力。
   - 第五章：宿命终章。盛大的结局，极致的繁华对比，最后一段要煽情、热泪盈眶。

【语言风格】：
冷峻中带着体温，像讲故事的老人在你耳边算命。段落要短，画面感要强。绝对不要带“旁白：”、“第一章”等任何形式的标题或标注，要整篇连贯。"""

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
            msgs = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"时代：{req.era}，地点：{req.location}，身份：{req.identity}，逆袭元素：{req.reversal}"}
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