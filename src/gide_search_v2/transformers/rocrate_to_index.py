import logging

from pydantic import ValidationError
from pyld import jsonld

from gide_search_v2.search.schema_search_object import IndexableDataset
from gide_search_v2.transformers.frame_transformer import FrameTransformer

logger = logging.getLogger("__main__." + __name__)


class ROCrateIndexTransformer(FrameTransformer):

    FRAME_BASE = {
        "@type": "Dataset",
        "@embed": "@always",
    }
    frame: dict

    def __init__(self):
        self.frame = self.FRAME_BASE | { "@context": self._get_ro_crate_context_with_containers()}
        super().__init__()

    def transform(self, single_object: dict):

        # FIXME: currently replacing context with defined one while we all update our ro-crates.
        single_object["@context"] = "https://www.gide-project.org/ro-crate/search/1.0/context"

        framed_doc = jsonld.frame(single_object, self.frame)

        if not isinstance(framed_doc, dict):
            raise TypeError()

        framed_doc.pop("@context")

        try:
            dataset = IndexableDataset.model_validate(framed_doc)
        except ValidationError as e:
            logger.error(
                f"Validation failed for: {framed_doc.get("@id", "Unknown object")}"
            )
            raise e

        return dataset.model_dump(by_alias=False)
