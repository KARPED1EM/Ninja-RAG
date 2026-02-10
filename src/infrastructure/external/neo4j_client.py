"""Neo4j 图数据库客户端"""

from typing import Any

from neo4j import AsyncGraphDatabase, AsyncSession

from src.infrastructure.config.settings import Settings


class Neo4jClient:
    """Neo4j 客户端"""

    def __init__(self, settings: Settings):
        self._settings = settings
        self._driver = None

    def get_driver(self):
        """获取驱动"""
        if self._driver is None:
            self._driver = AsyncGraphDatabase.driver(
                self._settings.neo4j_uri,
                auth=(self._settings.neo4j_user, self._settings.neo4j_password),
            )
        return self._driver

    async def close(self) -> None:
        """关闭连接"""
        if self._driver is not None:
            await self._driver.close()

    async def get_session(self) -> AsyncSession:
        """获取会话"""
        driver = self.get_driver()
        return driver.session(database=self._settings.neo4j_database)

    async def execute_query(
        self, query: str, parameters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """执行 Cypher 查询"""
        async with await self.get_session() as session:
            result = await session.run(query, parameters or {})
            records = await result.data()
            return records

    async def create_constraints(self) -> None:
        """创建约束和索引"""
        constraints = [
            # 实体唯一性约束
            "CREATE CONSTRAINT entity_name_unique IF NOT EXISTS FOR (e:Entity) REQUIRE e.name IS UNIQUE",
            # 人物唯一性约束
            "CREATE CONSTRAINT character_name_unique IF NOT EXISTS FOR (c:Character) REQUIRE c.name IS UNIQUE",
            # 概念唯一性约束
            "CREATE CONSTRAINT concept_name_unique IF NOT EXISTS FOR (c:Concept) REQUIRE c.name IS UNIQUE",
            # 作品唯一性约束
            "CREATE CONSTRAINT work_name_unique IF NOT EXISTS FOR (w:Work) REQUIRE w.name IS UNIQUE",
            # 组织唯一性约束
            "CREATE CONSTRAINT organization_name_unique IF NOT EXISTS FOR (o:Organization) REQUIRE o.name IS UNIQUE",
            # 元信息唯一性约束
            "CREATE CONSTRAINT meta_name_unique IF NOT EXISTS FOR (m:Meta) REQUIRE m.name IS UNIQUE",
            # 索引
            "CREATE INDEX entity_type_index IF NOT EXISTS FOR (e:Entity) ON (e.type)",
            "CREATE INDEX entity_wikibase_index IF NOT EXISTS FOR (e:Entity) ON (e.wikibase_item)",
        ]

        for constraint in constraints:
            try:
                await self.execute_query(constraint)
            except Exception as e:
                # 约束已存在，忽略错误
                if "already exists" not in str(e).lower():
                    raise

    async def clear_database(self) -> None:
        """清空数据库"""
        await self.execute_query("MATCH (n) DETACH DELETE n")

    async def create_node(
        self, labels: list[str], properties: dict[str, Any]
    ) -> dict[str, Any]:
        """创建节点"""
        label_str = ":".join(labels)
        query = f"CREATE (n:{label_str} $properties) RETURN n"
        result = await self.execute_query(query, {"properties": properties})
        return result[0]["n"] if result else {}

    async def create_relationship(
        self,
        from_node: dict[str, Any],
        to_node: dict[str, Any],
        rel_type: str,
        properties: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """创建关系"""
        query = f"""
        MATCH (a) WHERE id(a) = $from_id
        MATCH (b) WHERE id(b) = $to_id
        CREATE (a)-[r:{rel_type} $properties]->(b)
        RETURN r
        """
        result = await self.execute_query(
            query,
            {
                "from_id": from_node["id"],
                "to_id": to_node["id"],
                "properties": properties or {},
            },
        )
        return result[0]["r"] if result else {}

    async def find_node(
        self, labels: list[str] | None = None, properties: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """查找节点"""
        label_str = ":".join(labels) if labels else ""
        where_clauses = []
        params = {}

        if properties:
            for key, value in properties.items():
                where_clauses.append(f"n.{key} = ${key}")
                params[key] = value

        where_str = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        query = f"MATCH (n{':' + label_str if label_str else ''}) {where_str} RETURN n"
        result = await self.execute_query(query, params)
        return [record["n"] for record in result]

    async def find_paths(
        self, start_name: str, end_name: str, max_depth: int = 3
    ) -> list[dict[str, Any]]:
        """查找路径"""
        query = f"""
        MATCH path = (start:Entity {{name: $start_name}})-[*1..{max_depth}]-(end:Entity {{name: $end_name}})
        RETURN path
        LIMIT 10
        """
        result = await self.execute_query(
            query, {"start_name": start_name, "end_name": end_name}
        )
        return result

    async def find_related_entities(
        self, entity_name: str, rel_type: str | None = None, max_depth: int = 2
    ) -> list[dict[str, Any]]:
        """查找相关实体"""
        rel_pattern = f"[:{rel_type}*1..{max_depth}]" if rel_type else f"[*1..{max_depth}]"
        query = f"""
        MATCH (start:Entity {{name: $entity_name}})-{rel_pattern}-(related:Entity)
        RETURN DISTINCT related
        LIMIT 50
        """
        result = await self.execute_query(query, {"entity_name": entity_name})
        return [record["related"] for record in result]
