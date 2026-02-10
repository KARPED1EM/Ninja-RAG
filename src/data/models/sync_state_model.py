"""同步状态数据模型"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, String, Text

from .base import Base


class SyncStateModel(Base):
    """同步状态表模型"""

    __tablename__ = "sync_states"

    document_id = Column(
        String(255), primary_key=True, comment="文档唯一标识 (category/name)"
    )
    file_path = Column(String(1000), nullable=False, comment="文件路径")
    file_hash = Column(String(32), nullable=True, comment="文件 MD5 哈希值")
    file_mtime = Column(DateTime, nullable=False, comment="文件修改时间")
    last_synced_at = Column(DateTime, nullable=False, comment="最后同步时间")
    sync_status = Column(
        Enum("success", "failed", name="sync_status_enum"),
        nullable=False,
        comment="同步状态",
    )
    error_message = Column(Text, nullable=True, comment="错误信息")

    def __repr__(self) -> str:
        return f"<SyncStateModel(document_id={self.document_id}, status={self.sync_status})>"
