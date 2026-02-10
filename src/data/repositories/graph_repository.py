"""图数据库仓库实现"""

from typing import Any, Protocol

from src.data.sources.neo4j_client_adapter import Neo4jClientAdapter
from src.domain.entities.kg_entity import KGEntity
from src.domain.entities.kg_relation import KGRelation
from src.domain.entities.query_result import GraphPath


class IGraphRepository(Protocol):
    """图数据库仓库接口"""

    async def create_entity(self, entity: KGEntity) -> dict[str, Any]: ...

    async def create_relation(self, relation: KGRelation) -> dict[str, Any]: ...

    async def create_entities_batch(self, entities: list[KGEntity]) -> int: ...

    async def create_relations_batch(self, relations: list[KGRelation]) -> int: ...

    async def find_entity(self, name: str) -> dict[str, Any] | None: ...

    async def find_paths(
        self, entity_names: list[str], max_depth: int = 3
    ) -> list[GraphPath]: ...

    async def find_related_entities(
        self, entity_name: str, relation_type: str | None = None, max_depth: int = 2
    ) -> list[dict[str, Any]]: ...

    async def query_cypher(
        self, query: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]: ...


class Neo4jGraphRepository:
    """基于 Neo4j 的图数据库仓库实现"""

    def __init__(self, neo4j_adapter: Neo4jClientAdapter):
        self._neo4j = neo4j_adapter

    async def create_entity(self, entity: KGEntity) -> dict[str, Any]:
        """创建实体节点"""
        labels = ["Entity", entity.get_label()]
        properties = entity.to_neo4j_properties()

        # 使用 MERGE 避免重复
        query = f"""
        MERGE (n:{':'.join(labels)} {{name: $name}})
        ON CREATE SET n += $properties
        ON MATCH SET n += $properties
        RETURN n
        """

        result = await self._neo4j.execute_query(
            query, {"name": entity.name, "properties": properties}
        )
        return result[0]["n"] if result else {}

    async def create_relation(self, relation: KGRelation) -> dict[str, Any]:
        """创建关系"""
        rel_type = relation.get_cypher_type()
        properties = relation.to_neo4j_properties()

        query = f"""
        MATCH (a:Entity {{name: $from_entity}})
        MATCH (b:Entity {{name: $to_entity}})
        MERGE (a)-[r:{rel_type}]->(b)
        ON CREATE SET r += $properties
        ON MATCH SET r += $properties
        RETURN r
        """

        result = await self._neo4j.execute_query(
            query,
            {
                "from_entity": relation.from_entity,
                "to_entity": relation.to_entity,
                "properties": properties,
            },
        )
        return result[0]["r"] if result else {}

    async def create_entities_batch(self, entities: list[KGEntity]) -> int:
        """批量创建实体（单个查询）"""
        if not entities:
            return 0

        # 准备批量数据
        entity_data = []
        for entity in entities:
            labels = ["Entity", entity.get_label()]
            entity_data.append(
                {
                    "name": entity.name,
                    "labels": labels,
                    "properties": entity.to_neo4j_properties(),
                }
            )

        # UNWIND 批量创建
        query = """
        UNWIND $entities AS entity
        CALL {
            WITH entity
            MERGE (n:Entity {name: entity.name})
            SET n += entity.properties
            WITH n, entity
            CALL apoc.create.addLabels(n, [label IN entity.labels WHERE label <> 'Entity']) YIELD node
            RETURN node
        }
        RETURN count(*) AS created
        """

        try:
            result = await self._neo4j.execute_query(query, {"entities": entity_data})
            return result[0]["created"] if result else 0
        except Exception:
            # 如果 APOC 不可用，降级为简单版本
            query_simple = """
            UNWIND $entities AS entity
            MERGE (n:Entity {name: entity.name})
            SET n += entity.properties
            RETURN count(*) AS created
            """
            result = await self._neo4j.execute_query(
                query_simple, {"entities": entity_data}
            )
            return result[0]["created"] if result else 0

    async def create_relations_batch(self, relations: list[KGRelation]) -> int:
        """批量创建关系（单个查询）"""
        if not relations:
            return 0

        # 准备批量数据
        relation_data = []
        for relation in relations:
            relation_data.append(
                {
                    "from_entity": relation.from_entity,
                    "to_entity": relation.to_entity,
                    "type": relation.get_cypher_type(),
                    "properties": relation.to_neo4j_properties(),
                }
            )

        # UNWIND 批量创建
        query = """
        UNWIND $relations AS rel
        MATCH (a:Entity {name: rel.from_entity})
        MATCH (b:Entity {name: rel.to_entity})
        CALL apoc.merge.relationship(a, rel.type, {}, rel.properties, b, {}) YIELD rel AS r
        RETURN count(*) AS created
        """

        try:
            result = await self._neo4j.execute_query(
                query, {"relations": relation_data}
            )
            return result[0]["created"] if result else 0
        except Exception:
            # 如果 APOC 不可用，使用多查询方式
            created = 0
            for rel_data in relation_data:
                rel_type = rel_data["type"]
                query_single = f"""
                MATCH (a:Entity {{name: $from_entity}})
                MATCH (b:Entity {{name: $to_entity}})
                MERGE (a)-[r:{rel_type}]->(b)
                ON CREATE SET r += $properties
                ON MATCH SET r += $properties
                RETURN r
                """
                result = await self._neo4j.execute_query(
                    query_single,
                    {
                        "from_entity": rel_data["from_entity"],
                        "to_entity": rel_data["to_entity"],
                        "properties": rel_data["properties"],
                    },
                )
                if result:
                    created += 1
            return created

    async def find_entity(self, name: str) -> dict[str, Any] | None:
        """查找实体"""
        nodes = await self._neo4j.find_node(labels=["Entity"], properties={"name": name})
        return nodes[0] if nodes else None

    async def find_paths(
        self, entity_names: list[str], max_depth: int = 3
    ) -> list[GraphPath]:
        """查找路径"""
        if len(entity_names) < 2:
            return []

        paths = []
        start_name = entity_names[0]

        for end_name in entity_names[1:]:
            result = await self._neo4j.find_paths(start_name, end_name, max_depth)

            for record in result:
                path_data = record.get("path", {})
                # 简化路径信息
                paths.append(
                    GraphPath(
                        start_entity=start_name,
                        end_entity=end_name,
                        path_length=max_depth,  # 简化实现
                        relationships=[],
                        path_description=f"{start_name} -> {end_name}",
                    )
                )

        return paths

    async def find_related_entities(
        self, entity_name: str, relation_type: str | None = None, max_depth: int = 2
    ) -> list[dict[str, Any]]:
        """查找相关实体"""
        return await self._neo4j.find_related_entities(
            entity_name, relation_type, max_depth
        )

    async def query_cypher(
        self, query: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """执行 Cypher 查询"""
        return await self._neo4j.execute_query(query, params)

    async def clear(self) -> None:
        """清空数据库"""
        await self._neo4j.clear_database()

    async def count_nodes(self) -> int:
        """统计节点总数"""
        result = await self._neo4j.execute_query("MATCH (n) RETURN count(n) as count")
        return result[0]["count"] if result else 0
