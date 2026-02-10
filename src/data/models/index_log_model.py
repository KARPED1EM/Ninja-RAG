"""索引日志数据模型"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from .base import Base


class IndexLogModel(Base):
    """索引日志表模型"""

    __tablename__ = "index_logs"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="日志 ID")
    document_id = Column(String(255), nullable=False, index=True, comment="文档 ID")
    operation = Column(
        String(50), nullable=False, comment="操作类型 (index, reindex, delete)"
    )
    vector_count = Column(Integer, default=0, comment="索引向量数")
    graph_nodes = Column(Integer, default=0, comment="图谱节点数")
    graph_edges = Column(Integer, default=0, comment="图谱边数")
    status = Column(String(50), nullable=False, comment="操作状态")
    error_message = Column(Text, nullable=True, comment="错误信息")
    created_at = Column(DateTime, default=datetime.now, nullable=False, comment="创建时间")

    def __repr__(self) -> str:
        return f"<IndexLogModel(id={self.id}, document_id={self.document_id}, operation={self.operation})>"
