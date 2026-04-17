import logging

from pydantic import ValidationError
from pyld import jsonld

from gide_search.search.schema_search_object import IndexableDataset
from gide_search.transformers.frame_transformer import FrameTransformer
from gide_search.utils.ontology_term_finder import OntologyTermFinder

logger = logging.getLogger("__main__." + __name__)


class ROCrateIndexTransformer(FrameTransformer):

    FRAME_BASE = {
        "@type": "Dataset",
        "@embed": "@always",
    }
    frame: dict

    def __init__(self):
        self.frame = self.FRAME_BASE | {
            "@context": self._get_ro_crate_context_with_containers()
        }
        self.ontology_lookup = OntologyTermFinder()
        super().__init__()

    def transform(self, single_object: dict):

        base_iri = self._find_root_object(single_object).get("about", {}).get("@id")

        # FIXME: currently replacing context with defined one while we all update our ro-crates. The base IRI still needs to be present.
        single_object["@context"] = [
            "https://www.gide-project.org/ro-crate/search/1.0/context",
            {"@base": base_iri},
        ]

        framed_doc = jsonld.frame(
            single_object,
            self.frame,
        )

        if not isinstance(framed_doc, dict):
            raise TypeError()

        framed_doc.pop("@context")

        try:
            dataset = IndexableDataset.model_validate(framed_doc)
            dataset.fetch_labels(self.ontology_lookup)
        except ValidationError as e:
            logger.error(
                f"Validation failed for: {framed_doc.get('@id', 'Unknown object')}"
            )
            raise e

        return dataset.model_dump(by_alias=False)

    @staticmethod
    def _find_root_object(ro_crate_metadata: dict) -> dict:
        for entity in ro_crate_metadata.get("@graph"):
            if entity.get("@id") == "ro-crate-metadata.json":
                return entity

        # Waiting on update to example ro-crate to correct mistake we made about the ID of the root object.
        for entity in ro_crate_metadata.get("@graph"):
            if entity.get("@type") == "CreativeWork" and all(
                (x in entity for x in ("about", "conformsTo"))
            ):
                return entity

        raise ValueError("Cannot find root entity in ro-crate document")
