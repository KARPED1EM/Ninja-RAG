"""Milvus 向量数据库客户端"""

import logging
from typing import Any

from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, connections

from src.infrastructure.config.settings import Settings

logger = logging.getLogger(__name__)


class MilvusClient:
    """Milvus 客户端"""

    def __init__(self, settings: Settings):
        self._settings = settings
        self._alias = "default"
        self._connected = False

    def connect(self) -> None:
        """连接 Milvus"""
        if not self._connected:
            connections.connect(
                alias=self._alias,
                host=self._settings.milvus_host,
                port=str(self._settings.milvus_port),
            )
            self._connected = True

    def disconnect(self) -> None:
        """断开连接"""
        if self._connected:
            connections.disconnect(alias=self._alias)
            self._connected = False

    def collection_exists(self, collection_name: str) -> bool:
        """检查集合是否存在"""
        from pymilvus import utility

        self.connect()
        return utility.has_collection(collection_name, using=self._alias)

    def create_collection(
        self, collection_name: str, dimension: int, description: str = ""
    ) -> Collection:
        """创建集合"""
        self.connect()

        # 定义字段
        fields = [
            FieldSchema(
                name="id",
                dtype=DataType.VARCHAR,
                is_primary=True,
                max_length=500,
                description="文档片段唯一标识",
            ),
            FieldSchema(
                name="document_id",
                dtype=DataType.VARCHAR,
                max_length=255,
                description="文档 ID",
            ),
            FieldSchema(
                name="section_title",
                dtype=DataType.VARCHAR,
                max_length=500,
                description="章节标题",
            ),
            FieldSchema(
                name="content",
                dtype=DataType.VARCHAR,
                max_length=10000,
                description="文本内容",
            ),
            FieldSchema(
                name="embedding",
                dtype=DataType.FLOAT_VECTOR,
                dim=dimension,
                description="向量嵌入",
            ),
        ]

        # 创建 schema
        schema = CollectionSchema(fields=fields, description=description)

        # 创建集合
        collection = Collection(
            name=collection_name, schema=schema, using=self._alias
        )

        # 创建索引
        index_params = {
            "index_type": "IVF_FLAT",
            "metric_type": "IP",  # 内积（余弦相似度）
            "params": {"nlist": 128},
        }
        collection.create_index(field_name="embedding", index_params=index_params)

        return collection

    def get_collection(self, collection_name: str) -> Collection:
        """获取集合"""
        self.connect()
        return Collection(name=collection_name, using=self._alias)

    def drop_collection(self, collection_name: str) -> None:
        """删除集合"""
        from pymilvus import utility

        self.connect()
        if utility.has_collection(collection_name, using=self._alias):
            utility.drop_collection(collection_name, using=self._alias)

    def insert(
        self, collection_name: str, data: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """插入数据（使用行式格式，大数据量时分批插入）"""
        collection = self.get_collection(collection_name)
        collection.load()

        # Milvus 建议单次插入不超过 10000 条（避免内存压力）
        max_batch_size = 10000
        total_count = 0
        all_primary_keys = []

        if len(data) <= max_batch_size:
            # 小批量，直接插入
            result = collection.insert(data)
            collection.flush()
            return {"insert_count": len(data), "primary_keys": result.primary_keys}

        # 大批量，分批插入
        logger.info(f"大批量插入 {len(data)} 条数据，分批处理（每批 {max_batch_size}）...")
        for i in range(0, len(data), max_batch_size):
            batch = data[i : i + max_batch_size]
            result = collection.insert(batch)
            total_count += len(batch)
            all_primary_keys.extend(result.primary_keys)
            logger.debug(
                f"Milvus 插入批次 {i // max_batch_size + 1}/{(len(data) + max_batch_size - 1) // max_batch_size} "
                f"({len(batch)} 条)"
            )

        collection.flush()
        logger.info(f"Milvus 批量插入完成：{total_count} 条")
        return {"insert_count": total_count, "primary_keys": all_primary_keys}

    def search(
        self,
        collection_name: str,
        query_vectors: list[list[float]],
        top_k: int = 5,
        output_fields: list[str] | None = None,
    ) -> list[list[dict[str, Any]]]:
        """向量检索"""
        collection = self.get_collection(collection_name)
        collection.load()

        search_params = {"metric_type": "IP", "params": {"nprobe": 10}}

        if output_fields is None:
            output_fields = ["document_id", "section_title", "content"]

        results = collection.search(
            data=query_vectors,
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            output_fields=output_fields,
        )

        # 格式化结果
        formatted_results = []
        for hits in results:
            formatted_hits = []
            for hit in hits:
                formatted_hits.append(
                    {
                        "id": hit.id,
                        "score": hit.score,
                        "entity": hit.entity.to_dict(),
                    }
                )
            formatted_results.append(formatted_hits)

        return formatted_results

    def delete(
        self, collection_name: str, expr: str
    ) -> dict[str, Any]:
        """删除数据"""
        collection = self.get_collection(collection_name)
        collection.load()
        result = collection.delete(expr)
        collection.flush()
        return {"delete_count": result.delete_count}
