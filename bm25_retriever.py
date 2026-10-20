"""BM25 关键词检索：补向量检索对专有名词、英文术语、精确短句不敏感的问题。"""
import jieba
from langchain_core.documents import Document
from langchain_community.retrievers.bm25 import BM25Retriever


def chinese_tokenize(text: str) -> list[str]:
    """中文用搜索引擎切词；英文术语（如 Function Call）也能整词留下。"""
    return [token.strip() for token in jieba.cut_for_search(text) if token.strip()]


def build_bm25_retriever(documents: list[Document], k: int = 4) -> BM25Retriever:
    if not documents:
        raise ValueError("没有可用于 BM25 的文档")
    retriever = BM25Retriever.from_documents(
        documents,
        preprocess_func=chinese_tokenize,
    )
    retriever.k = k
    return retriever
