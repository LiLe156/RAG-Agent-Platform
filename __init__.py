from .rag import search_knowledge
from .calculator import calculator
from .datetime_tool import get_current_time


TOOL_REGISTRY = {
    "search_knowledge":search_knowledge,
    "calculator":calculator,
    "get_current_time":get_current_time
}

























