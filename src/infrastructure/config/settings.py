"""配置管理模块"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # 应用配置
    app_name: str = Field(default="Ninja-RAG", alias="APP_NAME")
    debug: bool = Field(default=False, alias="DEBUG")

    # 数据路径
    data_dir: str = Field(default="data/raw/wiki", alias="DATA_DIR")

    # MySQL 配置
    mysql_host: str = Field(default="localhost", alias="MYSQL_HOST")
    mysql_port: int = Field(default=3306, alias="MYSQL_PORT")
    mysql_user: str = Field(default="root", alias="MYSQL_USER")
    mysql_password: str = Field(default="", alias="MYSQL_PASSWORD")
    mysql_database: str = Field(default="ninja_rag", alias="MYSQL_DATABASE")

    # Milvus 配置
    milvus_host: str = Field(default="localhost", alias="MILVUS_HOST")
    milvus_port: int = Field(default=19530, alias="MILVUS_PORT")
    milvus_collection: str = Field(default="naruto_wiki", alias="MILVUS_COLLECTION")

    # Neo4j 配置
    neo4j_uri: str = Field(default="bolt://localhost:7687", alias="NEO4J_URI")
    neo4j_user: str = Field(default="neo4j", alias="NEO4J_USER")
    neo4j_password: str = Field(default="", alias="NEO4J_PASSWORD")
    neo4j_database: str = Field(default="naruto", alias="NEO4J_DATABASE")

    # 嵌入模型配置
    embedding_model: str = Field(default="BAAI/bge-m3", alias="EMBEDDING_MODEL")
    embedding_dim: int = Field(default=1024, alias="EMBEDDING_DIM")
    embedding_device: str = Field(default="cuda", alias="EMBEDDING_DEVICE")
    embedding_batch_size: int = Field(default=32, alias="EMBEDDING_BATCH_SIZE")

    # 千问 API 配置
    dashscope_api_key: str = Field(default="", alias="DASHSCOPE_API_KEY")
    qwen_model: str = Field(default="qwen-max", alias="QWEN_MODEL")
    qwen_temperature: float = Field(default=0.7, alias="QWEN_TEMPERATURE")

    # RAG 配置
    default_top_k: int = Field(default=5, alias="DEFAULT_TOP_K")
    chunk_max_length: int = Field(default=512, alias="CHUNK_MAX_LENGTH")

    # 混合检索配置
    dense_weight: float = Field(default=0.5, alias="DENSE_WEIGHT")
    sparse_weight: float = Field(default=0.5, alias="SPARSE_WEIGHT")
    use_hyde: bool = Field(default=False, alias="USE_HYDE")

    # 知识图谱配置
    enable_kg: bool = Field(default=True, alias="ENABLE_KG")
    kg_weight: float = Field(default=0.4, alias="KG_WEIGHT")
    llm_extract_entities: bool = Field(default=True, alias="LLM_EXTRACT_ENTITIES")

    # 同步配置
    auto_sync_on_startup: bool = Field(default=True, alias="AUTO_SYNC_ON_STARTUP")

    @property
    def mysql_url(self) -> str:
        """MySQL 连接 URL"""
        return f"mysql+aiomysql://{self.mysql_user}:{self.mysql_password}@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
