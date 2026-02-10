"""系统启动初始化"""

import asyncio
import logging

from src.infrastructure.config.settings import Settings
from src.infrastructure.database import Database
from src.infrastructure.external.milvus_client import MilvusClient
from src.infrastructure.external.neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)


class StartupService:
    """启动初始化服务"""

    def __init__(
        self,
        settings: Settings,
        database: Database,
        milvus_client: MilvusClient,
        neo4j_client: Neo4jClient,
    ):
        self._settings = settings
        self._database = database
        self._milvus = milvus_client
        self._neo4j = neo4j_client

    async def initialize_system(self) -> None:
        """初始化系统"""
        logger.info("系统启动中...")

        # 1. 初始化数据库结构
        await self._initialize_databases()

        # 2. 检测数据完整性
        if await self._is_first_run() or await self._is_data_missing():
            logger.warning("检测到首次启动或数据丢失")
            if self._settings.auto_sync_on_startup:
                logger.info("auto_sync_on_startup=True，需要触发全量更新")
                logger.info("请访问管理界面或调用 POST /api/sync/full 进行全量更新")
            else:
                logger.info("auto_sync_on_startup=False，跳过自动同步")

        logger.info("系统就绪")

    async def _initialize_databases(self) -> None:
        """初始化所有数据库结构"""
        logger.info("初始化数据库结构...")

        # MySQL 建表
        try:
            await self._database.create_all_tables()
            logger.info("✓ MySQL 表初始化完成")
        except Exception as e:
            logger.error(f"✗ MySQL 表初始化失败: {e}")
            raise

        # Milvus 创建集合
        try:
            self._milvus.connect()
            if not self._milvus.collection_exists(self._settings.milvus_collection):
                self._milvus.create_collection(
                    self._settings.milvus_collection,
                    self._settings.embedding_dim,
                    "火影忍者维基向量存储",
                )
                logger.info("✓ Milvus 集合创建完成")
            else:
                logger.info("✓ Milvus 集合已存在")
        except Exception as e:
            logger.error(f"✗ Milvus 集合初始化失败: {e}")
            raise

        # Neo4j 创建约束（带重试）
        max_retries = 5
        retry_delay = 2
        for attempt in range(max_retries):
            try:
                await self._neo4j.create_constraints()
                logger.info("✓ Neo4j 约束和索引创建完成")
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Neo4j 连接失败 (尝试 {attempt + 1}/{max_retries})，{retry_delay}秒后重试: {e}"
                    )
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 1.5  # 指数退避
                else:
                    logger.error(f"✗ Neo4j 约束初始化失败（已重试 {max_retries} 次）: {e}")
                    raise

    async def _is_first_run(self) -> bool:
        """是否首次运行"""
        try:
            async with self._database.get_session() as session:
                from sqlalchemy import select

                from src.data.models import DocumentModel

                result = await session.execute(select(DocumentModel).limit(1))
                return result.first() is None
        except Exception:
            return True

    async def _is_data_missing(self) -> bool:
        """是否数据丢失"""
        try:
            # 检查 MySQL
            async with self._database.get_session() as session:
                from sqlalchemy import func, select

                from src.data.models import DocumentModel

                result = await session.execute(
                    select(func.count(DocumentModel.id))
                )
                mysql_count = result.scalar() or 0

            # 检查 Milvus
            try:
                collection = self._milvus.get_collection(
                    self._settings.milvus_collection
                )
                milvus_count = collection.num_entities
            except Exception:
                milvus_count = 0

            # 如果 MySQL 有数据但 Milvus 没有，说明数据丢失
            if mysql_count > 0 and milvus_count == 0:
                logger.warning(
                    f"数据不一致: MySQL={mysql_count} 文档, Milvus={milvus_count} 向量"
                )
                return True

            return False
        except Exception as e:
            logger.error(f"检测数据完整性失败: {e}")
            return False

    async def shutdown(self) -> None:
        """关闭系统"""
        logger.info("系统关闭中...")
        await self._database.close()
        self._milvus.disconnect()
        await self._neo4j.close()
        logger.info("系统已关闭")
