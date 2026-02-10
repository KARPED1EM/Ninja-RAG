"""依赖注入容器"""

from dependency_injector import containers, providers

from src.data.mappers.document_db_mapper import DocumentDBMapper
from src.data.mappers.wiki_document_mapper import WikiDocumentMapper
from src.data.mappers.wiki_graph_mapper import WikiGraphMapper
from src.data.repositories.document_repository import MySQLDocumentRepository
from src.data.repositories.graph_repository import Neo4jGraphRepository
from src.data.repositories.sync_state_repository import MySQLSyncStateRepository
from src.data.repositories.vector_store_repository import MilvusVectorStoreRepository
from src.data.sources.milvus_client_adapter import MilvusClientAdapter
from src.data.sources.mysql_client_adapter import MySQLClientAdapter
from src.data.sources.neo4j_client_adapter import Neo4jClientAdapter
from src.data.sources.wiki_json_loader import WikiJsonLoader
from src.domain.services.document_processor import DocumentProcessor
from src.domain.services.entity_extractor import EntityExtractor
from src.infrastructure.config.settings import Settings
from src.infrastructure.database import Database
from src.infrastructure.external.bge_embedder import BgeEmbedder
from src.infrastructure.external.milvus_client import MilvusClient
from src.infrastructure.external.neo4j_client import Neo4jClient
from src.infrastructure.external.qwen_client import QwenClient
from src.infrastructure.startup import StartupService
from src.service.bm25_service import BM25Service
from src.service.document_service import DocumentService
from src.service.embedding_service import EmbeddingService
from src.service.hybrid_search_service import HybridSearchService
from src.service.hyde_service import HydeService
from src.service.knowledge_graph_service import KnowledgeGraphService
from src.service.llm_service import LLMService
from src.service.rag_service import RAGService
from src.service.sync_service import SyncService
from src.service.text_normalizer import TextNormalizer


class Container(containers.DeclarativeContainer):
    """IoC 容器"""

    # 配置
    config = providers.Singleton(Settings)

    # 数据库
    database = providers.Singleton(Database, settings=config)

    # 外部服务客户端（单例）
    milvus_client = providers.Singleton(MilvusClient, settings=config)
    neo4j_client = providers.Singleton(Neo4jClient, settings=config)
    bge_embedder = providers.Singleton(BgeEmbedder, settings=config)
    qwen_client = providers.Singleton(QwenClient, settings=config)

    # 数据源适配器
    mysql_adapter = providers.Singleton(MySQLClientAdapter, database=database)
    milvus_adapter = providers.Singleton(
        MilvusClientAdapter, milvus_client=milvus_client
    )
    neo4j_adapter = providers.Singleton(Neo4jClientAdapter, neo4j_client=neo4j_client)

    # 数据源
    wiki_json_loader = providers.Singleton(
        WikiJsonLoader,
        data_dir=config.provided.data_dir,
    )

    # 文本规范化服务（需要在 mapper 之前定义）
    text_normalizer = providers.Singleton(TextNormalizer)

    # 映射器
    wiki_document_mapper = providers.Singleton(
        WikiDocumentMapper, text_normalizer=text_normalizer
    )
    document_db_mapper = providers.Singleton(DocumentDBMapper)
    wiki_graph_mapper = providers.Singleton(WikiGraphMapper)

    # 仓库
    document_repository = providers.Singleton(
        MySQLDocumentRepository,
        database=database,
        mapper=document_db_mapper,
    )

    vector_store_repository = providers.Singleton(
        MilvusVectorStoreRepository,
        milvus_adapter=milvus_adapter,
        collection_name=config.provided.milvus_collection,
    )

    graph_repository = providers.Singleton(
        Neo4jGraphRepository,
        neo4j_adapter=neo4j_adapter,
    )

    sync_state_repository = providers.Singleton(
        MySQLSyncStateRepository,
        database=database,
    )

    # 领域服务
    document_processor = providers.Singleton(DocumentProcessor)
    entity_extractor = providers.Singleton(EntityExtractor)

    # 应用服务
    embedding_service = providers.Singleton(EmbeddingService, bge_embedder=bge_embedder)

    llm_service = providers.Singleton(LLMService, qwen_client=qwen_client)

    bm25_service = providers.Singleton(BM25Service, cache_dir=".cache/bm25")

    hyde_service = providers.Singleton(
        HydeService, llm_service=llm_service, embedding_service=embedding_service
    )

    hybrid_search_service = providers.Singleton(
        HybridSearchService,
        embedding_service=embedding_service,
        vector_store=vector_store_repository,
        bm25_service=bm25_service,
        hyde_service=hyde_service,
        dense_weight=config.provided.dense_weight,
        sparse_weight=config.provided.sparse_weight,
        use_hyde=config.provided.use_hyde,
    )

    document_service = providers.Singleton(
        DocumentService, document_repository=document_repository
    )

    knowledge_graph_service = providers.Singleton(
        KnowledgeGraphService,
        graph_repository=graph_repository,
        wiki_graph_mapper=wiki_graph_mapper,
        entity_extractor=entity_extractor,
        llm_service=llm_service,
        enable_llm_extract=config.provided.llm_extract_entities,
    )

    sync_service = providers.Singleton(
        SyncService,
        data_dir=config.provided.data_dir,
        mapper=wiki_document_mapper,
        doc_repo=document_repository,
        vector_repo=vector_store_repository,
        kg_service=knowledge_graph_service,
        sync_state_repo=sync_state_repository,
        embedding_service=embedding_service,
        document_processor=document_processor,
        chunk_max_length=config.provided.chunk_max_length,
    )

    rag_service = providers.Singleton(
        RAGService,
        hybrid_search=hybrid_search_service,
        kg_service=knowledge_graph_service,
        llm_service=llm_service,
        text_normalizer=text_normalizer,
        default_top_k=config.provided.default_top_k,
        enable_kg=config.provided.enable_kg,
        kg_weight=config.provided.kg_weight,
    )

    # 启动服务
    startup_service = providers.Singleton(
        StartupService,
        settings=config,
        database=database,
        milvus_client=milvus_client,
        neo4j_client=neo4j_client,
    )
