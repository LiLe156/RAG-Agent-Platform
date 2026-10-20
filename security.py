import base64
from .config import MAX_ROUND

MALICIOUS_KEYWORD = ['忽略你之前所有指令','忽略系统指令','重写规则','删除全部','导出全部','给我你的system prompt']

user_permission = {
    "user001":{"tools":["search_knowledge","calculator","get_current_time"]},
    "admin":{"tools":["search_knowledge","calculator","get_current_time","delete_order"]}
}

def check_input_injection(user_query:str) -> tuple[bool,str]:
    for kw in MALICIOUS_KEYWORD:
        if kw in user_query:
            return True,"injection"

    try:
        decoded = base64.b64decode(user_query).decode('utf-8')
        for kw in MALICIOUS_KEYWORD:
            #debug True
            if kw in decoded:
                return True,"injection"
    except Exception :
        pass
    return False,""

def validate_tool_permission(user_id:str,tool_name:str) -> tuple[bool,str]:
#验证    许可
    print(f"🔎权限校验->传入的用户ID:'{user_id}',工具:'{tool_name}")
    #打印出许可的工具列表
    print(f"DEBUG-全局权限字典:{user_permission}")
    #debug 如果查不到用户，默认给他普通的工具权限（防止系统卡死）
    default_perms={"tools":["search_knowledge","calculator","get_current_time"]}
    perms = user_permission.get(user_id,default_perms)
    if not perms.get("tools"):
        print(f"⚠️警告：未找到用户{user_id}的权限配置，已降级为默认普通用户。")
    print(f"DEBUG-当前用户权限:{perms}")
    allowed = perms.get('tools',[])
    if tool_name not in allowed:
        return False,"unauthorized_tool"    #把原来可能返回的""改为明确的字符串
    if tool_name == "delete_order":
        #debug 参数写错 True
        return False,"high_risk_action"
    return True,"ok"











































































































