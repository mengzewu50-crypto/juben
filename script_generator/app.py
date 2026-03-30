import json
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from openai import AsyncOpenAI

app = FastAPI()
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

@app.post("/api/generate_script")
async def generate_script(req: ScriptRequest):
    async def event_generator():
        try:
            stream = await client.chat.completions.create(
                model="deepseek-chat", 
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"时代：{req.era}，地点：{req.location}，身份：{req.identity}，逆袭元素：{req.reversal}"}
                ],
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