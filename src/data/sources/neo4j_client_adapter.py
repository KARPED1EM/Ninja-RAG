"""Neo4j 客户端适配器"""

from typing import Any

from src.infrastructure.external.neo4j_client import Neo4jClient


class Neo4jClientAdapter:
    """Neo4j 客户端适配器（数据层）"""

    def __init__(self, neo4j_client: Neo4jClient):
        self._client = neo4j_client

    async def close(self) -> None:
        """关闭连接"""
        await self._client.close()

    async def execute_query(
        self, query: str, parameters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """执行查询"""
        return await self._client.execute_query(query, parameters)

    async def create_constraints(self) -> None:
        """创建约束"""
        await self._client.create_constraints()

    async def clear_database(self) -> None:
        """清空数据库"""
        await self._client.clear_database()

    async def create_node(
        self, labels: list[str], properties: dict[str, Any]
    ) -> dict[str, Any]:
        """创建节点"""
        return await self._client.create_node(labels, properties)

    async def create_relationship(
        self,
        from_node: dict[str, Any],
        to_node: dict[str, Any],
        rel_type: str,
        properties: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """创建关系"""
        return await self._client.create_relationship(
            from_node, to_node, rel_type, properties
        )

    async def find_node(
        self, labels: list[str] | None = None, properties: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """查找节点"""
        return await self._client.find_node(labels, properties)

    async def find_paths(
        self, start_name: str, end_name: str, max_depth: int = 3
    ) -> list[dict[str, Any]]:
        """查找路径"""
        return await self._client.find_paths(start_name, end_name, max_depth)

    async def find_related_entities(
        self, entity_name: str, rel_type: str | None = None, max_depth: int = 2
    ) -> list[dict[str, Any]]:
        """查找相关实体"""
        return await self._client.find_related_entities(entity_name, rel_type, max_depth)
