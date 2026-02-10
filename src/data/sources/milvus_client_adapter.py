"""Milvus 客户端适配器"""

from typing import Any

from src.infrastructure.external.milvus_client import MilvusClient


class MilvusClientAdapter:
    """Milvus 客户端适配器（数据层）"""

    def __init__(self, milvus_client: MilvusClient):
        self._client = milvus_client

    def connect(self) -> None:
        """连接"""
        self._client.connect()

    def disconnect(self) -> None:
        """断开连接"""
        self._client.disconnect()

    def collection_exists(self, collection_name: str) -> bool:
        """集合是否存在"""
        return self._client.collection_exists(collection_name)

    def create_collection(
        self, collection_name: str, dimension: int, description: str = ""
    ) -> None:
        """创建集合"""
        self._client.create_collection(collection_name, dimension, description)

    def drop_collection(self, collection_name: str) -> None:
        """删除集合"""
        self._client.drop_collection(collection_name)

    def insert(
        self, collection_name: str, data: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """插入数据"""
        return self._client.insert(collection_name, data)

    def search(
        self,
        collection_name: str,
        query_vectors: list[list[float]],
        top_k: int = 5,
        output_fields: list[str] | None = None,
    ) -> list[list[dict[str, Any]]]:
        """检索"""
        return self._client.search(collection_name, query_vectors, top_k, output_fields)

    def delete(self, collection_name: str, expr: str) -> dict[str, Any]:
        """删除数据"""
        return self._client.delete(collection_name, expr)
