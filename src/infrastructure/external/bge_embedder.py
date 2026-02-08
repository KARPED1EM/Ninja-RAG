"""BGE 嵌入模型客户端"""

import logging

import torch
from sentence_transformers import SentenceTransformer

from src.infrastructure.config.settings import Settings

logger = logging.getLogger(__name__)


class BgeEmbedder:
    """BGE 中文嵌入模型（支持 GPU 加速）"""

    def __init__(self, settings: Settings):
        self._settings = settings
        self._model: SentenceTransformer | None = None
        self._device = self._get_device()

    def _get_device(self) -> str:
        """智能选择设备（优先 GPU）"""
        requested_device = self._settings.embedding_device.lower()

        # 如果请求 CUDA，检查是否可用
        if requested_device.startswith("cuda"):
            if torch.cuda.is_available():
                # 如果指定了具体设备号，验证其有效性
                if ":" in requested_device:
                    device_id = int(requested_device.split(":")[1])
                    if device_id < torch.cuda.device_count():
                        logger.info(
                            f"使用 GPU: {torch.cuda.get_device_name(device_id)} "
                            f"(显存: {torch.cuda.get_device_properties(device_id).total_memory / 1024**3:.1f} GB)"
                        )
                        return requested_device
                    else:
                        logger.warning(
                            f"请求的 GPU 设备 {requested_device} 不存在，"
                            f"当前可用 GPU 数量: {torch.cuda.device_count()}，降级到 CPU"
                        )
                        return "cpu"
                else:
                    # 使用默认 GPU
                    logger.info(
                        f"使用 GPU: {torch.cuda.get_device_name(0)} "
                        f"(显存: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB)"
                    )
                    return "cuda"
            else:
                logger.warning(
                    f"请求 GPU ({requested_device}) 但 CUDA 不可用，降级到 CPU。"
                    f"如需 GPU 加速，请安装 CUDA 版本的 PyTorch: "
                    f"pip install torch --index-url https://download.pytorch.org/whl/cu121"
                )
                return "cpu"
        else:
            logger.info("使用 CPU 运行嵌入模型")
            return "cpu"

    def get_model(self) -> SentenceTransformer:
        """获取模型（懒加载）"""
        if self._model is None:
            logger.info(
                f"加载嵌入模型: {self._settings.embedding_model} (设备: {self._device})"
            )
            self._model = SentenceTransformer(
                self._settings.embedding_model,
                device=self._device,
            )
        return self._model

    def embed_text(self, text: str) -> list[float]:
        """嵌入单个文本"""
        model = self.get_model()
        embedding = model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def embed_texts(
        self, texts: list[str], batch_size: int | None = None
    ) -> list[list[float]]:
        """批量嵌入文本"""
        model = self.get_model()
        if batch_size is None:
            batch_size = self._settings.embedding_batch_size

        embeddings = model.encode(
            texts,
            normalize_embeddings=True,
            batch_size=batch_size,
            show_progress_bar=True,
        )
        return [emb.tolist() for emb in embeddings]

    @property
    def dimension(self) -> int:
        """向量维度"""
        return self._settings.embedding_dim
