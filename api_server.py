import os
import json
import time
import asyncio
from fastapi import FastAPI,HTTPException
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
#【新导入】StreamingResponse是FastAPI的“水龙头”，用来做流式输出
from fastapi.responses import StreamingResponse
import uvicorn
import json
import aiosqlite
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
#移入你刚刚调通的Graph
from app.graph_builder import build_graph
from app.observability import metrics
import re
#生命一个全局变量，用来存放编译好的图
graph = None
async def lifespan(app: FastAPI):
    """FastAPI生命周期:启动时连接异步SQLite"""
    global graph
    DB_PATH = "D:/agent_memory.sqlite"

    #建造异步数据库连接
    async with aiosqlite.connect(DB_PATH) as conn:
        #使用AsyncSqliteSaver
        checkpointer = AsyncSqliteSaver(conn)
        #调用刚才改造的构建函数
        graph = build_graph(checkpointer=checkpointer)
        print("✅️AsyncSqliteSaver初始化成功，多轮对话持久化开启！")
        yield
    #服务关闭时连接会回自动释放

#修改FastAPI实例化，传入lifespan
app = FastAPI(title="企业内部知识库Agent服务",lifespan=lifespan)

# ================= 【2. 新增：CORS 跨域配置】 =================
# 允许所有前端域名跨域访问你的接口
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源（生产环境建议改成具体的前端域名）
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有HTTP方法（包括 OPTIONS 和 POST）
    allow_headers=["*"],  # 允许所有请求头
)
# ==============================================================

#定义API接收的JSON格式
class ChatRequest(BaseModel):
    user_id:str
    session_id:str
    query:str


#============================1.普通非流式接口（便于快速测试）===============================================================
@app.post('/chat/sync')
async def chat_sync(req:ChatRequest):
    """同步接口:等所有步骤跑完，一次性返回。适合后台任务调用"""
    config = {"configurable":{"thread_id":req.session_id}}
    init_state = {
        "user_id":req.user_id,"session_id":req.session_id,"user_query":req.query,
        "tool_calls":[],"info":[],"round":0,"answer":"",
        "safety_triggered":False,"safety_reason":"","trace_data":{},
        "messages":[HumanMessage(content=req.query)],
        "long_term_memory":[]
    }
    try:
        #【核心修复】直接使用原生的异步方法ainvoke，不再使用run_in_executor
        #这样AsyncSqliteSaver就能在同一个FastAPI事件循环中安全运行
        #【修改】用async.wait_for限制最长执行时间
        task = asyncio.create_task(graph.ainvoke(init_state,config=config))
        result = await asyncio.wait_for(
            task,
            timeout=60.0    #超时60秒
        )

        # result = await loop.run_in_executor(None,lambda:graph.invoke(init_state,congfig=config))
        return {"code":200,"answer":result.get("answer","")}
    except asyncio.TimeoutError:
        return {"code":504,"msg":"推理超时(超过60秒),请重试或简化问题"}

    except Exception as e:
        return {"code":500,"msg":f"服务端报错:{str(e)}"}

#================2.流式输出接口(前端首选，解决本地慢痛点)==============================
@app.post("/chat/stream")
async def chat_stream(req:ChatRequest):
    """流式接口:边推理边返回进度，最后吐出完整答案"""
    config = {"configurable":{"thread_id":req.session_id}}
    init_state = {
        "user_id":req.user_id,"session_id":req.session_id,"user_query":req.query,
        "tool_calls":[],"info":[],"round":0,"answer":"",
        "safety_triggered":False,"safety_reason":"","trace_data":{},
        "research_notes":"",
        "messages":[HumanMessage(content=req.query)],
        "long_term_memory":[]
    }

#定一个“异步生成器”函数。使用yield往外吐数据
    async def event_generator():
        try:
            #先给前端发送一个“开始处理”的信号，让页面显示“正在思考...
            #json.dumps把字典转成字符串，ensure_ascii=False保证中文不乱码
            #"data:XXX\n\n"是SSE(Server-Sent Events)协议规定的固定格式
            yield f"data: {json.dumps({'state':'start','msg':'Agent开始思考...'},ensure_ascii=False)}\n\n"

        #【1.开始循环前记录起始时间】
            start_time = time.time()

            #【新增1】准备一个空篮子
            full_answer_text = ""

            #2.【监控摄像头开始】遍历Agent运行时抛出的所有事件
            #使用astream异步流式迭代
            #LangGraph会在每个节点执行完成后，突出最新的state
            #async for时异步循环，因为事件时随时产生的
            # async for chunk in graph.astream(init_state,config=config,stream_mode="values"):

            # 新增这一行，看看服务端到底有没有在推东西
            print("\n🚀 [Debug] 开始监听 LangGraph 事件...",flush=True)

            async for chunk in graph.astream_events(init_state,config=config,version="v2"):
                print(f"捕获事件:{chunk.get('event')}", flush=True)
                #【2.在循环最开始检查是否超时】
                if time.time() - start_time > 120:    #60秒超时阀值
                    yield f"data: {json.dumps({'status':'error','msg':'推理超时(超过120秒),请重试或简化问题'},ensure_ascii=False)}\n\n"
                    break #【3核心：强制跳出循环，停止监听】

#-------------------------下面是原有的流式处理逻辑--------------------------
                #检查是否有中间进度
                #提取事件类型和名字
                kind = chunk.get("event")
                #比如:"on_chat_model_stream"
                name = chunk.get("name","")
                #比如:"agent_think"或"search_knowledge"
                print(f"捕获事件：{kind}|名称：{name}")   #【监控打印】


                #判断是否进入节点
                #如果进入了一个节点（比如开始查资料了）
                if kind == "on_chain_start" and name in ["agent_think","safety_refusal","output"]:
                    yield f"data: {json.dumps({'status':'node','msg':f'进入节点:{name}'},ensure_ascii=False)}\n\n"

                #判断是否需要调用工具
                #如果开始调用工具（比如去查test.pdf）
                if kind == "on_tool_start":
                    yield f"data: {json.dumps({'status': 'tool', 'msg': f'正在调用工具{name}'},ensure_ascii=False)}\n\n"

                #此处实时退出大模型输出文字（流式生成）
                if kind == "on_chat_model_stream":
                    content = chunk["data"]["chunk"].content

                    # 优先从 metadata 获取图节点名，如果获取不到，就退回用原来的 name
                    metadata = chunk.get("metadata", {})
                    node_name = chunk.get("name", "")
                    actual_node = metadata.get("langgraph_node", node_name)

                    # 【严格限制】只允许 writer 节点过安检
                    if content and actual_node == "writer":

                        # 1. 只要看到 content 或 action，直接一刀切
                        if 'content' in content:
                            content = content.split('content')[-1]
                        elif 'action' in content:
                            content = content.split('answer')[-1] if 'answer' in content else content.split('action')[
                                -1]

                        # 2. 去掉首尾可能残留的标点符号和花括号
                        content = content.lstrip(': "{}').rstrip('"{}')

                        # 3. 物理超度所有审核词
                        if "FAIL" in content or "PASS" in content or "不合格" in content:
                            continue

                        # 4. 过滤废话兜底
                        if "知识没有找到相关内容" in content:
                            content = content.split("知识没有找到相关内容")[0]

                        # 5. 推送干净的内容
                        if content.strip():
                            # 【新增2】把清洗干净的字连接起来
                            full_answer_text += content
                            yield f"data: {json.dumps({'status': 'stream', 'token': content}, ensure_ascii=False)}\n\n"
                    else:
                        # 所有其他节点（agent_think, critic, 甚至底层包装）全部拦截
                        if content:
                            print(f"🤫 [后台思考] [{actual_node}] 输出被拦截，不发给前端。")


            # #3.全部处理完毕
            # yield f"data: {json.dumps({'status':'done','msg':'处理完毕'},ensure_ascii=False)}\n\n"

        #【核心修复】把最终的完整答案一并塞在done消息里
            # final_full_answer = state.get("answer","")#或者从graph最后的chunk里拿到
            yield f"data:{json.dumps({'status':'done','msg':'处理完毕','answer':full_answer_text},ensure_ascii=False)}\n\n"
        except Exception as e:
            #如果出错，推给前端一个错误
            yield f"data: {json.dumps({'status':'error','msg':f'服务端报错:{str(e)}'},ensure_ascii=False)}\n\n"
    #把上面这个生成器塞进“水龙头”，告诉浏览器这个接口返回的是事件流(text/event-stream)
    return StreamingResponse(event_generator(),media_type="text/event-stream")

if __name__ == "__main__":
    print("🚀API服务重启:http://127.0.0.1:8000/docs")
    uvicorn.run(app,host="127.0.0.1",port=8001,workers=1,loop="asyncio")


#运行操作如下:
"""
🛠️ 第二步：本地运行与测试
启动服务：在 PyCharm 里直接右键运行 api_server.py。

看到终端打印 Uvicorn running on http://127.0.0.1:8000 就成功了。

用浏览器测试（推荐）：
打开浏览器，访问 http://127.0.0.1:8000/docs。你会看到一个 Swagger 网页。
展开 /chat/stream，点击 Try it out，输入：
    {
  "user_id": "user001",
  "session_id": "session_web_001",
  "query": "Function Call原理是什么？"
}
点击 Execute，你会立刻在下方看到 "Agent 开始思考..." 的进度，并且等工具调用完后，最终回答会一次性推送到网页上。


+++++++++=============================================笔记======================================================+++++++++++++++++++++++++++++++
💡 核心设计解析：
run_in_executor：因为 graph.invoke 是同步阻塞的，如果直接在 FastAPI 的异步函数里跑，会卡死整个服务器。我把同步调用包装进线程池里，防止服务崩溃。

astream(stream_mode="values")：这是 LangGraph 特有的流式方法，它每次节点执行完，会把最新状态送出来。我们在 event_generator 里判断：如果有 answer，就把 answer 推给前端，让前端不再无限等待。

StreamingResponse：这是 SSE 协议的标准写法。注意 data: {...}\n\n 的格式，这是 SSE 规范，前端（Vue/React）只需监听 onmessage 就能接收到。


"""



























































































































