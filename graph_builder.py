from langgraph.graph import StateGraph,END
from langgraph.checkpoint.sqlite import SqliteSaver
from .state import AgentState
#新导入记忆节点
from .graph_nodes import agent_think_node,safety_refusal_node,output_node,retriever_memory_node,save_memory_node,writer_node,critic_node
import os



builder = StateGraph(AgentState)
builder.add_node("retriever_memory",retriever_memory_node)#新增
builder.add_node("agent_think",agent_think_node)
builder.add_node("safety_refusal",safety_refusal_node)
builder.add_node("output",output_node)
builder.add_node("save_memory",save_memory_node)  #新增
builder.add_node("writer",writer_node)   #新增
builder.add_node("critic",critic_node)


# builder.set_entry_point("agent_think")    再加入记忆节点之前开始节点时=是agent_ndoe
#【修改入口】从现在检索记忆开始
builder.set_entry_point("retriever_memory")

#路由逻辑:如果agent_think没给出答案，就交给writer去写
def route_after_think(state):
    #如果触发安全拦截，直接走拒绝节点
    if state.get("safety_triggered"):
        return "safety_refusal"
    #如果已经有了答案，去输出节点结束流程
    # 如果已经产生答案（比如报错退出、达到轮次上限），直接去输出
    # if state.get("answer"):
    #     return "writer"
    #既然没拦截，也没答案（说明刚调用完工具），继续回去思考
    # 否则（说明资料收集完毕，进入撰写阶段），去 writer 节点
    return "writer"
builder.add_conditional_edges(
    "agent_think",
    route_after_think,
    {"safety_refusal":"safety_refusal","writer":"writer"}
)
#writer写完，交给critic审核
builder.add_edge("writer","critic")
#===========================【核心】critic的回路路由=================================================
def route_after_critic(state):
    retry_count = state.get("critic_retry_count",0)
    answer = state.get("answer","")

    #条件1：如果审核通过（answer有值 且 重试次数被清0）
    if answer and retry_count == 0:
        return "output"

    #条件2：如果审核不通过，且重试次数超过2次，打回给writer
    if retry_count < 2:
        return 'writer'

    #条件3：重试次数超过2次，强制放行（防止死循环）
    print("🔴【系统】审核重试超过2次，强制输出当前结果")
    return "output"

builder.add_conditional_edges(
    "critic",
    route_after_critic,
    {"output":'output','writer':"writer"}

)


#writer写完答案后，去output输出
# builder.add_edge("writer","output")

#路由：检索完及以后，去think
builder.add_edge("retriever_memory","agent_think")

#debug True 如果黑客攻击连接一次，方便后台记录，保证系统闭环
builder.add_edge("safety_refusal","output")

#原有的条件路由（think之后的分支）保持不变，但要在output之后加上save_memory
#...原有的add_conditional_edges代码...
builder.add_edge("output","save_memory")
#这里是需要添加node的·记忆节点·
builder.add_edge("save_memory",END)


DB_PATH="D:/agent_memory.sqlite"

parent_dir=os.path.dirname(DB_PATH)
if parent_dir and not os.path.exists(parent_dir):
    os.makedirs(parent_dir)
    print(f"📃已自动创建目录:{parent_dir}")
#注意:asyncSqliteSaver需要再FastAPI生命周期或者异步上下文中使用。
#为了简化API端的调用，我们暂时不在这里实例化，而是导出一个构建函数。


#直接使用sqlite3建立连接(check_same_thread=False防止多线程报错)
# conn = sqlite3.connect("D:/agent_memory.sqlite",check_same_thread=False)
# checkpointer = SqliteSaver(conn)
# checkpointer = SqliteSaver.from_conn_string("D:/agent_memory.sqlite")
# graph = builder.compile(checkpointer=checkpointer)

# checkpointer = MemorySaver()
# graph = builder.compile(checkpointer=checkpointer)
# print("✅️Agent图构建完成，已接入Sqlite会话持久")
# print("✅️已切换为MemorySaver（内存会话），流式输出解锁！")

#============================【修改点】导出构建函数，交由FastAPI异步初始化==================================================================
#删除写死的MemorySaver和graph，改为函数导出
def build_graph(checkpointer):
    """由API端传入checkpointer(AsyncSqliteSaver)来构建并编译图"""
    return builder.compile(checkpointer=checkpointer)

print("✅️graph_builder初始化完成，等待API端注入持久化Checkpointer...")






























































































































































































