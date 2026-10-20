import re
import json
import time
import uuid
from typing import Any

def mask_sensitive_data(text:str) -> str:
    if not isinstance(text,str):
        return str(text)
    text = re.sub(r'(?<!\d)1[3-9]\d{9}(?!\d)', '138****8888', text)
    text = re.sub(r'(?<!\d)\d{17}[\dXx](?!\d)', '3401**********1234', text)
    text = re.sub(r'(sk-[a-zA-Z0-9]{20,})', 'sk-****', text)
    return text

class AgentTracer:
    def __init__(self,user_id:str,session_id:str):
        self.trace_id = f"trace_{uuid.uuid4().hex[:8]}"
        self.user_id = user_id
        self.session_id = session_id
        self.spans = []

    def add_span(self,span_name:str,start_time:float,input_data:Any,output_data:Any,error:str = None):
        def truncate(data):
            #有AIMessage是个Python对象，不能直接转成JSON，导致程序崩溃
            #【核心修复】加上default=str，让json.dumps遇到对象时自动转成字符串
            s = json.dumps(data,ensure_ascii=False,default=str) if not isinstance(data,str) else data
            s = mask_sensitive_data(s)
            return s[:200] + "...(截断)" if len(s) > 200 else s
        self.spans.append({
            "trace_id":self.trace_id,
            "span_name":span_name,
            "cost_ms":round((time.time()-start_time)*1000,2),
            "input":truncate(input_data),
            "output":truncate(output_data),
            "error":str(error) if error else None
        })

    def export_log(self):
        return {
            "trace_id":self.trace_id,
            "user_id":self.user_id,
            "session_id":self.session_id,
            "total_cost_ms":sum(s['cost_ms'] for s in self.spans),
            "spans":self.spans
        }

class MetricsCollector:
    def __init__(self):
        self.requests = 0
        self.total_spans = 0
        self.total_cost_ms = 0
        self.error_count = 0
        self.injection_intercepts = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    def record_trace(self,trace_data:dict):
        self.requests += 1
        self.total_spans += len(trace_data.get("spans",[]))
        self.total_cost_ms += trace_data.get("total_cost_ms",0)
        for span in trace_data.get("spans",[]):
            if span.get("error"):
                self.error_count += 1

    def record_injection(self):
        self.injection_intercepts += 1

        # 新增记录方法
    def record_tokens(self, input_tokens: int, output_tokens: int):
         self.total_input_tokens += input_tokens
         self.total_output_tokens += output_tokens

    def report(self):
        avg_cost = self.total_cost_ms / self.requests if self.requests > 0 else 0
        avg_spans = self.total_spans / self.requests if self.requests > 0 else 0
        # return f"\n====全局监控报表====\n总请求数:{self.requests}\n平均耗时:{avg_cost:.2f} ms\n平均执行步骤数:{avg_spans:.2f}\n注入拦截次数:{self:{self.injection_intercepts}}"
        #{self:{self.injection_intercepts}} 这是 f-string 的格式说明符语法，会被解释为 self 用 {self.injection_intercepts} 作为格式说明符，这是非法的，运行时可能报错。
        return f"""
        ====全局监控报表====
        总请求数:{self.requests}
        平均耗时:{avg_cost:.2f} ms
        平均执行步骤数:{avg_spans:.2f}
        异常次数:{self.error_count}
        注入拦截次数:{self.injection_intercepts}
        -------Token消耗(粗略估算)---------
        总输入Token:{self.total_input_tokens}
        总输出Token:{self.total_output_tokens}
        总计耗时Token:{self.total_input_tokens + self.total_output_tokens}
"""

metrics = MetricsCollector()

































































































