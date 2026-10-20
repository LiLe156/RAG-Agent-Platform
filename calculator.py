#calculator.py
def calculator(expression:str) -> str:
    #expression表达
    """执行简单的数学计算，如'1+1'或'23*45"""
    allowed = set("0123456789+-*/().")
    if not all(c in allowed for c in expression):
        return "错误:表达式包含非法字符"
    try:
        result = eval(expression,{"__builtins__":{}},{})
        return f"计算结果:{expression}={result}"
    except Exception as e:
        return f"计算错误:{str(e)}"



































































































