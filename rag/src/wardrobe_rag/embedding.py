"""Real neural encoders. Models are lazy-loaded and never silently mocked."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Sequence

import numpy as np
from PIL import Image

MODEL_SPECS = {
    "text": "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
    "image": "sentence-transformers/clip-ViT-B-32",
    "visual_text": "sentence-transformers/clip-ViT-B-32-multilingual-v1",
}
MODEL_REVISIONS = {
    "text": "4328cf26390c98c5e3c738b4460a05b95f4911f5",
    "image": "327ab6726d33c0e22f920c83f2ff9e4bd38ca37f",
    "visual_text": "58edf8cada9e398793dca955574a48cbb7f18be2",
}


class SentenceTransformerEmbedder:
    def __init__(self, *, cache_dir: Path | None = None, device: str = "cpu",
                 offline: bool = False, batch_size: int = 16,
                 model_paths: dict[str, str] | None = None,
                 model_revisions: dict[str, str] | None = None):
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.device = device
        self.offline = offline
        self.batch_size = batch_size
        self.model_paths = model_paths or dict(MODEL_SPECS)
        self.model_revisions = model_revisions or dict(MODEL_REVISIONS)
        if set(self.model_paths) != set(MODEL_SPECS) or set(self.model_revisions) != set(MODEL_SPECS):
            raise ValueError("Specify text, image and visual_text model paths and immutable revisions")
        if model_paths is not None and model_revisions is None:
            raise ValueError("Custom model paths require explicit immutable model_revisions")
        self._models: dict[str, object] = {}
        self._revisions: dict[str, str] = {}

    def _model(self, channel: str):
        if channel not in self._models:
            from sentence_transformers import SentenceTransformer
            self._models[channel] = SentenceTransformer(
                self.model_paths[channel], device=self.device,
                revision=self.model_revisions[channel],
                cache_folder=str(self.cache_dir) if self.cache_dir else None,
                local_files_only=self.offline, trust_remote_code=False,
            )
            model = self._models[channel]
            # Commit hash is supplied by transformers for downloaded configs.
            first = model[0]
            config = getattr(getattr(first, "auto_model", None), "config", None)
            if config is None:
                config = getattr(getattr(first, "model", None), "config", None)
            self._revisions[channel] = getattr(config, "_commit_hash", None) or self.model_revisions[channel]
        return self._models[channel]

    def prepare(self) -> dict:
        for channel in MODEL_SPECS:
            self._model(channel)
        return self.provenance

    @property
    def provenance(self) -> dict:
        return {"models": self.model_paths, "revisions": self._revisions,
                "device": self.device, "offline": self.offline}

    @property
    def fingerprint(self) -> str:
        # Resolve all model revisions before persisting an index signature.
        self.prepare()
        payload = {"models": self.model_paths, "revisions": self._revisions, "template": 1}
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    def _encode(self, channel: str, values: Sequence) -> np.ndarray:
        if not values:
            return np.empty((0, 0), dtype=np.float32)
        return np.asarray(self._model(channel).encode(
            list(values), batch_size=self.batch_size, convert_to_numpy=True,
            normalize_embeddings=True, show_progress_bar=False,
        ), dtype=np.float32)

    def encode_text(self, texts: Sequence[str]) -> np.ndarray:
        return self._encode("text", texts)

    def encode_visual_text(self, texts: Sequence[str]) -> np.ndarray:
        return self._encode("visual_text", texts)

    def encode_images(self, images: Sequence[Image.Image]) -> np.ndarray:
        return self._encode("image", images)
