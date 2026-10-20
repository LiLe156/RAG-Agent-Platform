import os
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv  #导入读取工具
#强制使用国内镜像站下载模型
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ["HF_ENDPOINT"]="http://hf-mirror.com"
print(f"正在加载LLM配置")

#【核心修改】加载.env文件中的环境变量
load_dotenv()
#从环境变量中读取（如果没读到，给个报错提示）
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
if not DEEPSEEK_API_KEY:
    raise ValueError("❌️致命错误:未在.env文件中找到DEEPSEEK_API_KEY,请检查配置！")

#路径配置
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_PATH = "D:/faiss_store"
PDF_PATH = os.path.join(BASE_DIR,"test.pdf")
EMBED_MODEL = "BAAI/bge-small-zh-v1.5"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
RERANK_MODEL = r"D:\models"


# #你的DeepSeek配置
# DEEPSEEK_API_KEY = "sk-..."

#==================================【核心修复】用这种方式定义LLM=================================
#注意看，我们直接把完整的URL写入default_headers里绕过框架拼接
llm = ChatOpenAI(
    model=os.getenv("DEEPSEEK_MODEL","deepseek-chat"),
    api_key=DEEPSEEK_API_KEY,
    base_url=os.getenv("DEEPSEEK_BASE_URL","https://api.deepseek.com/v1"),
    temperature=0,
    #【关键】强制告诉底层用/chat/completions作为完整路径
    default_headers={"Content-Type":"application/json"}
)

#在config.py的llm定义后面，加上这两行
print(f"[DEBUG]当前使用的LLM地址为：{llm.openai_api_base}")
print(f"[DEBUG]当前使用的模型名为：{llm.model_name}")



#安全配置
MAX_ROUND = 5





































