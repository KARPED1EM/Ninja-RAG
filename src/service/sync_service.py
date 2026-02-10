"""同步服务 - 高并发自适应性能优化"""

import asyncio
import hashlib
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from src.data.mappers.wiki_document_mapper import WikiDocumentMapper
from src.data.repositories.document_repository import IDocumentRepository
from src.data.repositories.sync_state_repository import ISyncStateRepository
from src.data.repositories.vector_store_repository import IVectorStoreRepository
from src.domain.services.document_processor import DocumentProcessor
from src.domain.value_objects.document_id import DocumentId
from src.service.embedding_service import EmbeddingService
from src.service.knowledge_graph_service import KnowledgeGraphService

logger = logging.getLogger(__name__)


@dataclass
class SyncProgress:
    """同步进度"""

    phase: str  # "扫描" | "加载" | "解析" | "向量化" | "索引" | "完成"
    current: int
    total: int
    current_doc: str = ""
    message: str = ""


@dataclass
class SyncResult:
    """同步结果"""

    total: int
    success: int
    failed: int
    added: int = 0
    updated: int = 0
    deleted: int = 0
    errors: list[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class SyncService:
    """同步服务"""

    def __init__(
        self,
        data_dir: str,
        mapper: WikiDocumentMapper,
        doc_repo: IDocumentRepository,
        vector_repo: IVectorStoreRepository,
        kg_service: KnowledgeGraphService,
        sync_state_repo: ISyncStateRepository,
        embedding_service: EmbeddingService,
        document_processor: DocumentProcessor,
        chunk_max_length: int = 512,
    ):
        self._data_dir = Path(data_dir)
        self._mapper = mapper
        self._doc_repo = doc_repo
        self._vector_repo = vector_repo
        self._kg_service = kg_service
        self._sync_repo = sync_state_repo
        self._embedding = embedding_service
        self._processor = document_processor
        self._chunk_max_length = chunk_max_length
        self._progress_callback = None

        # 自适应并发度
        cpu_count = os.cpu_count() or 4
        self._io_concurrency = cpu_count * 8  # I/O 密集，高并发
        self._cpu_concurrency = cpu_count * 2  # CPU 密集
        self._db_concurrency = min(cpu_count * 3, 20)  # 数据库操作（限制最大值避免连接过载）
        self._embedding_batch_size = 64  # Embedding 批量大小
        self._max_embedding_batch = 1000  # 单批最大 chunks 数（避免显存溢出）

        # 信号量控制
        self._io_semaphore = asyncio.Semaphore(self._io_concurrency)
        self._cpu_semaphore = asyncio.Semaphore(self._cpu_concurrency)
        self._db_semaphore = asyncio.Semaphore(self._db_concurrency)

        logger.info(
            f"并发配置: I/O={self._io_concurrency}, "
            f"CPU={self._cpu_concurrency}, "
            f"DB={self._db_concurrency}, "
            f"Embedding批量={self._embedding_batch_size}, "
            f"单批最大chunks={self._max_embedding_batch}"
        )

    def set_progress_callback(self, callback):
        """设置进度回调函数"""
        self._progress_callback = callback

    async def _report_progress(self, progress: SyncProgress):
        """报告进度"""
        if self._progress_callback:
            await self._progress_callback(progress)

    def _calculate_file_hash(self, file_path: Path) -> str:
        """计算文件 MD5 hash（同步版本）"""
        md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                md5.update(chunk)
        return md5.hexdigest()

    async def _scan_files(self) -> dict[str, dict]:
        """
        并发扫描文件系统
        返回: {doc_id_str: {"path": str, "hash": str, "mtime": datetime}}
        """
        await self._report_progress(
            SyncProgress(phase="扫描", current=0, total=0, message="扫描文件系统...")
        )

        if not self._data_dir.exists():
            return {}

        # 收集所有待扫描的文件
        scan_tasks = []
        file_count = 0
        for category_dir in self._data_dir.iterdir():
            if not category_dir.is_dir():
                continue

            for doc_dir in category_dir.iterdir():
                if not doc_dir.is_dir():
                    continue

                parse_file = doc_dir / "parse.json"
                if not parse_file.exists():
                    continue

                doc_id = f"{category_dir.name}/{doc_dir.name}"
                scan_tasks.append(
                    self._scan_single_file(
                        doc_id, parse_file, category_dir.name, doc_dir.name
                    )
                )
                file_count += 1

        await self._report_progress(
            SyncProgress(
                phase="扫描",
                current=0,
                total=file_count,
                message=f"计算文件哈希 ({file_count} 个文件)",
            )
        )

        # 并发扫描
        results = await asyncio.gather(*scan_tasks)
        files = {doc_id: info for doc_id, info in results if info is not None}

        await self._report_progress(
            SyncProgress(
                phase="扫描",
                current=len(files),
                total=len(files),
                message=f"完成 ({len(files)} 个文件)",
            )
        )

        return files

    async def _scan_single_file(
        self, doc_id: str, parse_file: Path, category: str, name: str
    ) -> tuple[str, dict | None]:
        """扫描单个文件（在线程池中执行 hash 计算）"""
        async with self._io_semaphore:
            try:
                # 在线程池中计算 hash（避免阻塞事件循环）
                file_hash = await asyncio.to_thread(
                    self._calculate_file_hash, parse_file
                )
                file_mtime = datetime.fromtimestamp(parse_file.stat().st_mtime)

                return doc_id, {
                    "path": str(parse_file),
                    "hash": file_hash,
                    "mtime": file_mtime,
                    "category": category,
                    "name": name,
                }
            except Exception as e:
                logger.error(f"扫描文件失败 {doc_id}: {e}")
                return doc_id, None

    async def incremental_sync(self) -> SyncResult:
        """增量更新（超高并发版本）"""
        logger.info("开始增量更新（超高并发）...")
        result = SyncResult(total=0, success=0, failed=0)

        # 1. 并发扫描文件系统
        current_files = await self._scan_files()

        # 2. 获取数据库中的同步状态
        await self._report_progress(
            SyncProgress(
                phase="扫描",
                current=len(current_files),
                total=len(current_files),
                message="比对数据库状态...",
            )
        )

        db_states = await self._sync_repo.get_all_states()
        db_files = {state.document_id: state for state in db_states}

        # 3. 比对差异
        to_add = []
        to_update = []
        to_delete = []

        for doc_id, file_info in current_files.items():
            if doc_id not in db_files:
                to_add.append((doc_id, file_info))
            else:
                state = db_files[doc_id]
                if state.file_hash != file_info["hash"]:
                    to_update.append((doc_id, file_info))

        for doc_id in db_files:
            if doc_id not in current_files:
                to_delete.append(doc_id)

        total_tasks = len(to_add) + len(to_update) + len(to_delete)

        if total_tasks == 0:
            await self._report_progress(
                SyncProgress(
                    phase="完成", current=0, total=0, message="✓ 无需更新，数据已是最新"
                )
            )
            logger.info("无需更新")
            return result

        await self._report_progress(
            SyncProgress(
                phase="扫描",
                current=total_tasks,
                total=total_tasks,
                message=f"变更统计: +{len(to_add)} ~{len(to_update)} -{len(to_delete)}",
            )
        )

        logger.info(
            f"发现变更：新增 {len(to_add)}, 更新 {len(to_update)}, 删除 {len(to_delete)}"
        )

        # 4. 并发处理删除（快速清理）
        if to_delete:
            await self._report_progress(
                SyncProgress(
                    phase="删除",
                    current=0,
                    total=len(to_delete),
                    message=f"删除过期文档 ({len(to_delete)} 个)",
                )
            )
            delete_results = await asyncio.gather(
                *[self._process_delete(doc_id) for doc_id in to_delete],
                return_exceptions=True,
            )
            for doc_id, res in zip(to_delete, delete_results):
                if isinstance(res, Exception):
                    result.failed += 1
                    result.errors.append(f"删除失败 {doc_id}: {res}")
                    logger.error(f"✗ 删除失败 {doc_id}: {res}")
                else:
                    result.deleted += 1
                    result.success += 1

            await self._report_progress(
                SyncProgress(
                    phase="删除",
                    current=len(to_delete),
                    total=len(to_delete),
                    message=f"完成 (成功 {result.deleted})",
                )
            )

        # 5. 并发处理新增和更新（流水线式）
        all_tasks = [("add", doc_id, info) for doc_id, info in to_add] + [
            ("update", doc_id, info) for doc_id, info in to_update
        ]

        # 流水线处理
        pipeline_results = await self._pipeline_process(all_tasks, total_tasks)

        # 统计结果
        for action, doc_id, res in pipeline_results:
            if isinstance(res, Exception):
                result.failed += 1
                result.errors.append(f"{action} 失败 {doc_id}: {res}")
                logger.error(f"✗ {action} 失败 {doc_id}: {res}")
            else:
                result.success += 1
                if action == "add":
                    result.added += 1
                elif action == "update":
                    result.updated += 1

        result.total = total_tasks

        # 计算成功率
        success_rate = (
            (result.success / total_tasks * 100) if total_tasks > 0 else 100
        )

        await self._report_progress(
            SyncProgress(
                phase="完成",
                current=total_tasks,
                total=total_tasks,
                message=f"✓ 同步完成! +{result.added} ~{result.updated} -{result.deleted} ✗{result.failed} (成功率 {success_rate:.1f}%)",
            )
        )

        logger.info(
            f"增量更新完成: 新增 {result.added}, 更新 {result.updated}, "
            f"删除 {result.deleted}, 失败 {result.failed}, 成功率: {success_rate:.1f}%"
        )
        return result

    async def _pipeline_process(self, tasks, total_tasks):
        """流水线式处理（分阶段并发）"""
        # 阶段 1: 并发加载和解析
        await self._report_progress(
            SyncProgress(
                phase="加载",
                current=0,
                total=total_tasks,
                message=f"加载文档 ({total_tasks} 个)",
            )
        )

        loaded_docs = await asyncio.gather(
            *[self._load_and_parse(action, doc_id, info) for action, doc_id, info in tasks],
            return_exceptions=True,
        )

        # 过滤成功的文档
        valid_docs = []
        failed_docs = []
        for i, (action, doc_id, info) in enumerate(tasks):
            res = loaded_docs[i]
            if isinstance(res, Exception):
                failed_docs.append((action, doc_id, res))
                logger.error(f"加载失败 {doc_id}: {res}")
            else:
                valid_docs.append((action, doc_id, info, res))

        await self._report_progress(
            SyncProgress(
                phase="加载",
                current=len(valid_docs),
                total=total_tasks,
                message=f"完成 (成功 {len(valid_docs)}, 失败 {len(failed_docs)})",
            )
        )

        if not valid_docs:
            return [(action, doc_id, res) for action, doc_id, res in failed_docs]

        # 阶段 2: 批量分块
        await self._report_progress(
            SyncProgress(
                phase="分块",
                current=0,
                total=len(valid_docs),
                message=f"分割文档 ({len(valid_docs)} 个)",
            )
        )

        chunked_docs = await asyncio.gather(
            *[
                self._chunk_document(action, doc_id, info, doc)
                for action, doc_id, info, doc in valid_docs
            ],
            return_exceptions=True,
        )

        await self._report_progress(
            SyncProgress(
                phase="分块",
                current=len(valid_docs),
                total=len(valid_docs),
                message="完成",
            )
        )

        # 阶段 3: 批量 Embedding
        await self._report_progress(
            SyncProgress(
                phase="向量化",
                current=0,
                total=len(valid_docs),
                message="批量向量化...",
            )
        )

        embedded_docs = await self._batch_embedding_all(chunked_docs, valid_docs)

        await self._report_progress(
            SyncProgress(
                phase="向量化",
                current=len(valid_docs),
                total=len(valid_docs),
                message="完成",
            )
        )

        # 阶段 4: 并发索引
        await self._report_progress(
            SyncProgress(
                phase="索引",
                current=0,
                total=len(valid_docs),
                message=f"索引文档 ({len(valid_docs)} 个)",
            )
        )

        # 索引时实时报告进度（使用 as_completed 实现真实时输出）
        completed_count = 0
        total_docs = len(valid_docs)
        index_results = []

        # 创建所有索引任务
        index_tasks = {}
        for i, ((action, doc_id, info, doc), (chunks, embedded)) in enumerate(
            zip(valid_docs, embedded_docs)
        ):
            task = asyncio.create_task(
                self._index_document_concurrent(
                    action, doc_id, info, doc, chunks, embedded
                )
            )
            index_tasks[task] = (action, doc_id, info)

        # 按完成顺序处理结果（真实时报告进度）
        for task in asyncio.as_completed(index_tasks.keys()):
            try:
                result = await task
                action, doc_id, info = index_tasks[task]
                completed_count += 1

                # 每完成一个立即报告进度
                await self._report_progress(
                    SyncProgress(
                        phase="索引",
                        current=completed_count,
                        total=total_docs,
                        current_doc=doc_id,
                        message=doc_id,
                    )
                )

                index_results.append((action, doc_id, result))
            except Exception as e:
                action, doc_id, info = index_tasks[task]
                completed_count += 1
                index_results.append((action, doc_id, e))

        # 合并结果
        all_results = []
        for i, (action, doc_id, info, doc) in enumerate(valid_docs):
            all_results.append((action, doc_id, index_results[i]))
        for action, doc_id, res in failed_docs:
            all_results.append((action, doc_id, res))

        return all_results

    async def _load_and_parse(self, action: str, doc_id: str, file_info: dict):
        """加载并解析文档（I/O + CPU）"""
        from src.data.sources.wiki_json_loader import WikiJsonLoader

        async with self._io_semaphore:
            # 文件加载
            loader = WikiJsonLoader(str(self._data_dir))
            raw_data = await loader.load_document(
                file_info["category"], file_info["name"]
            )

            if not raw_data:
                raise ValueError(f"加载失败: {doc_id}")

        async with self._cpu_semaphore:
            # 在线程池中解析（CPU 密集）
            document = await asyncio.to_thread(self._mapper.map_to_document, raw_data)

        return (document, raw_data)

    async def _chunk_document(
        self, action: str, doc_id: str, file_info: dict, doc_and_raw
    ):
        """分割文档（CPU 密集）"""
        document, raw_data = doc_and_raw

        async with self._cpu_semaphore:
            chunks = await asyncio.to_thread(
                self._processor.split_into_chunks, document, self._chunk_max_length
            )

        return (document, raw_data, chunks)

    async def _batch_embedding_all(self, chunked_docs, valid_docs):
        """批量 Embedding 所有文档的 chunks（分批处理）"""
        # 收集所有 chunks
        all_chunks_flat = []
        chunk_counts = []

        for i, chunked_result in enumerate(chunked_docs):
            if isinstance(chunked_result, Exception):
                chunk_counts.append(0)
                continue

            document, raw_data, chunks = chunked_result
            all_chunks_flat.extend(chunks)
            chunk_counts.append(len(chunks))

        if not all_chunks_flat:
            return [([], []) for _ in chunked_docs]

        # 分批 Embedding（避免显存溢出）
        embedded_chunks = []

        total_chunks = len(all_chunks_flat)
        logger.info(f"批量向量化: {total_chunks} 个文本块")

        for i in range(0, total_chunks, self._max_embedding_batch):
            batch = all_chunks_flat[i : i + self._max_embedding_batch]
            batch_num = i // self._max_embedding_batch + 1
            total_batches = (
                total_chunks + self._max_embedding_batch - 1
            ) // self._max_embedding_batch

            logger.debug(f"向量化批次 {batch_num}/{total_batches}")

            # 先处理
            batch_embedded = await asyncio.to_thread(
                self._embedding.embed_chunks, batch
            )
            embedded_chunks.extend(batch_embedded)

            # 完成后报告进度
            await self._report_progress(
                SyncProgress(
                    phase="向量化",
                    current=i + len(batch),
                    total=total_chunks,
                    message=f"批次 {batch_num}/{total_batches} ({len(batch)} chunks)",
                )
            )

        logger.info(f"向量化完成: {len(embedded_chunks)} 个向量")

        # 按文档重新分组
        results = []
        offset = 0
        for i, chunked_result in enumerate(chunked_docs):
            if isinstance(chunked_result, Exception):
                results.append(([], []))
                continue

            document, raw_data, chunks = chunked_result
            count = chunk_counts[i]
            doc_embedded = embedded_chunks[offset : offset + count]
            results.append((chunks, doc_embedded))
            offset += count

        return results

    async def _index_document_concurrent(
        self,
        action: str,
        doc_id: str,
        file_info: dict,
        doc_and_raw,
        chunks,
        embedded_chunks,
    ):
        """并发索引文档（MySQL + Milvus + Neo4j）"""
        document, raw_data = doc_and_raw

        # 如果是更新，先删除旧向量
        if action == "update":
            logger.debug(f"[{doc_id}] 删除旧向量...")
            async with self._db_semaphore:
                await self._vector_repo.delete_by_document(document.id)
            logger.debug(f"[{doc_id}] 旧向量已删除")

        # 并发执行三个索引操作
        async with self._db_semaphore:
            logger.debug(f"[{doc_id}] 开始索引: MySQL + Milvus({len(embedded_chunks)} 向量) + Neo4j")

            # 使用 TaskGroup 确保所有任务完成
            async with asyncio.TaskGroup() as tg:
                # MySQL 保存
                tg.create_task(self._save_to_mysql(document, doc_id))

                # Milvus 向量索引
                if embedded_chunks:
                    tg.create_task(
                        self._save_to_milvus(document.id, embedded_chunks, doc_id)
                    )

                # Neo4j 知识图谱
                tg.create_task(self._save_to_neo4j(document, doc_id))

            logger.debug(f"[{doc_id}] 索引完成")

        # 保存同步状态
        file_hash = file_info["hash"]
        await self._sync_repo.save_state(
            document.id,
            file_info["path"],
            file_info["mtime"],
            status="success",
            file_hash=file_hash,
        )

        return "success"

    async def _save_to_mysql(self, document, doc_id: str):
        """保存到 MySQL"""
        logger.debug(f"[{doc_id}] → MySQL 保存中...")
        await self._doc_repo.save(document)
        logger.debug(f"[{doc_id}] ✓ MySQL 完成")

    async def _save_to_milvus(self, document_id, embedded_chunks, doc_id: str):
        """保存到 Milvus"""
        logger.debug(f"[{doc_id}] → Milvus 索引 {len(embedded_chunks)} 个向量...")
        await self._vector_repo.index_vectors(document_id, embedded_chunks)
        logger.debug(f"[{doc_id}] ✓ Milvus 完成")

    async def _save_to_neo4j(self, document, doc_id: str):
        """保存到 Neo4j"""
        logger.debug(f"[{doc_id}] → Neo4j 构建图谱...")
        stats = await self._kg_service.build_graph_from_document(document)
        logger.debug(f"[{doc_id}] ✓ Neo4j 完成 (节点:{stats.get('nodes', 0)}, 边:{stats.get('edges', 0)})")

    async def _process_delete(self, doc_id: str):
        """删除文档"""
        async with self._db_semaphore:
            doc_id_obj = DocumentId.from_str(doc_id)

            # 并发删除
            async with asyncio.TaskGroup() as tg:
                tg.create_task(self._doc_repo.delete(doc_id_obj))
                tg.create_task(self._vector_repo.delete_by_document(doc_id_obj))
                tg.create_task(self._sync_repo.delete_state(doc_id_obj))
