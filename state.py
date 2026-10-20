from typing import TypedDict,List,Dict,Annotated
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    user_id:str
    session_id:str
    user_query:str
    #【新增】使用Annotated和add_messages自动管理对话历史
    messages:Annotated[list[BaseMessage],add_messages]
    tool_calls:List[Dict]
    info:List[str]
    round:int
    answer:str
    safety_triggered:bool
    safety_reason:str
    trace_data:Dict

    #【新增】常记忆检索结果
    long_term_memory:List[str]

    #【新增】记录检索专家收集到的原始资料
    research_notes: str

    #【新增】审核重试次数
    critic_retry_count:int

    research_notes:str
























































