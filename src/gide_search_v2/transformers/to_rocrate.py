import hashlib
from uuid import UUID

from gide_search_v2.transformers.frame_transformer import FrameTransformer


class ROCrateTransformer(FrameTransformer):
    generated_ids: set[str]

    def __init__(self):
        self.generated_ids = set()
        super().__init__()

    def _get_ro_crate_ref(self, entry_url: str) -> dict:
        return {
            "@id": "ro-crate-metadata.json",
            "@type": "CreativeWork",
            "conformsTo": {
                "@id": "https://www.gide-project.org/ro-crate/search/1.0/profile"
            },
            "about": {"@id": entry_url},
        }

    def _generate_ref_id(self, key: str, force_unique: bool = False) -> str:
        hexdigest = hashlib.md5(key.encode("utf-8")).hexdigest()
        relative_ref = f"#{UUID(version=4, hex=hexdigest)}"
        if force_unique and relative_ref in self.generated_ids:
            relative_ref = self._generate_ref_id(relative_ref, force_unique=True)
        self.generated_ids.add(relative_ref)
        return relative_ref
