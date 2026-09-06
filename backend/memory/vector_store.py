"""向量检索层 —— ChromaDB 封装（对应 PRD4 6.1 / 6.3）

提供：
- add_chunks(book_id, chunks)：把书籍分块写入向量库（含文本与元数据）
- search(query, book_id, top_k, min_score)：语义检索 Top-K，带相似度阈值过滤

设计要点：
- Embedder 可插拔：默认 HashingEmbedder（本地离线、零下载），
  生产可替换为真实 embedding API（如 DeepSeek / OpenAI）——只需实现
  `embed(texts: List[str]) -> List[List[float]]`。
- 单 collection，按 book_id 元数据过滤，避免每本书建一个 collection。
"""

import hashlib
import logging
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Protocol, Sequence

import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)

# collection 中距离度量：余弦距离（score = 1 - distance）
_COLLECTION_NAME = "book_chunks"

# 默认检索 top_k
DEFAULT_TOP_K = 3
# 默认相似度阈值（PRD4 3.2: > 0.75）
DEFAULT_MIN_SCORE = 0.75


# ============================================================
# Embedder 协议
# ============================================================


class Embedder(Protocol):
    """Embedding 生成协议（可插拔）"""

    def embed(self, texts: List[str]) -> List[List[float]]:
        """把一批文本转成向量列表"""
        ...


EmbedderFunc = Callable[[List[str]], List[List[float]]]


class HashingEmbedder:
    """离线确定性 Embedder —— 基于字符 n-gram 哈希

    说明：真实场景应替换为 API Embedder（如 DeepSeek embedding）。
    此实现用于本地开发与单测，保证零下载、可复现。
    """

    _DIM = 256
    _NGRAM = 3

    def _text_vec(self, text: str) -> List[float]:
        vec = [0.0] * self._DIM
        norm_text = text.lower()
        if not norm_text.strip():
            return vec
        for i in range(len(norm_text) - self._NGRAM + 1):
            gram = norm_text[i:i + self._NGRAM]
            h = int(hashlib.md5(gram.encode("utf-8")).hexdigest()[:8], 16)
            idx = h % self._DIM
            # 加权：词边界出现频率低，用 1 恒定累加即可
            vec[idx] += 1.0
        # L2 归一化
        norm = sum(v * v for v in vec) ** 0.5
        if norm == 0:
            return vec
        return [v / norm for v in vec]

    def embed(self, texts: List[str]) -> List[List[float]]:
        return [self._text_vec(t) for t in texts]


def get_default_embedder() -> Embedder:
    """获取默认 embedder（离线确定性）"""
    return HashingEmbedder()


# ============================================================
# 检索结果
# ============================================================


@dataclass
class RetrievedChunk:
    """一次检索命中的分块"""

    text: str = ""
    chapter: Optional[str] = None
    chunk_index: int = 0
    score: float = 0.0

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "chapter": self.chapter,
            "chunk_index": self.chunk_index,
            "score": round(self.score, 4),
        }


@dataclass
class BookChunk:
    """待写入的分块（元数据即原文所在位置）"""

    chunk_index: int
    text: str
    chapter: Optional[str] = None
    metadata: dict = field(default_factory=dict)


# ============================================================
# 向量存储
# ============================================================


class VectorStoreError(Exception):
    """向量库操作异常"""


class VectorStore:
    """ChromaDB 向量库封装

    用法：
        >>> store = VectorStore()
        >>> store.add_chunks("book-1", [BookChunk(chunk_index=0, text="...", chapter="c1")])
        >>> hits = store.search("某问题", book_id="book-1", top_k=3, min_score=0.0)
    """

    def __init__(
        self,
        embedder: Optional[Embedder] = None,
        collection_name: str = _COLLECTION_NAME,
    ) -> None:
        self._embedder = embedder or get_default_embedder()
        # chromadb ephemeral client 在同一进程内共享后端，
        # collection 名用于逻辑隔离（测试应传独立名）
        self._client = chromadb.Client(Settings(anonymized_telemetry=False))
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    # ============================================================
    # 写入
    # ============================================================

    def add_chunks(self, book_id: str, chunks: Sequence[BookChunk]) -> int:
        """把一本书的分块写入向量库

        Args:
            book_id: 书籍标识
            chunks: 分块列表

        Returns:
            写入数量

        Raises:
            VectorStoreError: 写入失败（含文本为空）
        """
        valid = [c for c in chunks if c.text.strip()]
        if not valid:
            raise VectorStoreError("No valid chunks to add (all texts empty)")

        ids: List[str] = []
        docs: List[str] = []
        metas: List[dict] = []
        for c in valid:
            cid = f"{book_id}#chunk-{c.chunk_index}"
            ids.append(cid)
            docs.append(c.text)
            # chromadb 不接受 None 值，丢弃空元数据
            meta: dict = {"book_id": book_id, "chunk_index": c.chunk_index}
            if c.chapter:
                meta["chapter"] = c.chapter
            for k, v in (c.metadata or {}).items():
                if v is not None:
                    meta[k] = v
            metas.append(meta)

        embeddings = self._embedder.embed(docs)
        self._collection.add(
            ids=ids,
            documents=docs,
            embeddings=embeddings,
            metadatas=metas,
        )
        logger.info("vector store: added %d chunks for book %s", len(valid), book_id)
        return len(valid)

    # ============================================================
    # 检索
    # ============================================================

    def count(self) -> int:
        """当前库内分块总数"""
        return self._collection.count()

    def search(
        self,
        query: str,
        book_id: str,
        top_k: int = DEFAULT_TOP_K,
        min_score: float = DEFAULT_MIN_SCORE,
    ) -> List[RetrievedChunk]:
        """语义检索

        Args:
            query: 查询文本（玩家问题）
            book_id: 限定书籍
            top_k: 返回候选数（过滤前）
            min_score: 相似度阈值（余弦），低于此值的结果被丢弃

        Returns:
            按分数降序的 RetrievedChunk 列表
        """
        if not query.strip():
            return []

        total = self._collection.count()
        if total == 0:
            return []

        query_vec = self._embedder.embed([query])
        # n_results 不超过库中条目数，避免 chromadb 报错
        k = min(top_k, total)
        try:
            raw = self._collection.query(
                query_embeddings=query_vec,
                n_results=k,
                where={"book_id": book_id},
                include=["documents", "metadatas", "distances"],
            )
        except Exception as e:
            raise VectorStoreError(f"Vector search failed: {e}") from e

        return self._parse_query_result(raw, min_score)

    def _parse_query_result(
        self, raw: dict, min_score: float,
    ) -> List[RetrievedChunk]:
        """解析 chromadb query 结果，做阈值过滤 + 分数降序"""
        results: List[RetrievedChunk] = []

        # chromadb 返回嵌套 list：[[...]]
        docs_lists = raw.get("documents") or []
        metas_lists = raw.get("metadatas") or []
        dists_lists = raw.get("distances") or []

        for docs, metas, dists in zip(docs_lists, metas_lists, dists_lists):
            for doc, meta, dist in zip(docs, metas, dists):
                # cosine distance → 相似度（越小越相似）
                score = 1.0 - float(dist)
                if score < min_score:
                    continue
                chunk = RetrievedChunk(
                    text=doc or "",
                    chapter=meta.get("chapter") if meta else None,
                    chunk_index=int(meta.get("chunk_index", 0)) if meta else 0,
                    score=score,
                )
                results.append(chunk)

        # 分数降序
        results.sort(key=lambda r: r.score, reverse=True)
        return results
