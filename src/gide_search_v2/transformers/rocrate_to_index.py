import json
from pathlib import Path

from pyld import jsonld

from gide_search_v2.search.schema_search_object import Dataset, IndexableDataset
from gide_search_v2.transformers.base_transformer import Transformer


class ROCrateIndexTransformer(Transformer):

    FRAME = {
        "@context": [
            "https://w3id.org/ro/crate/1.2/context",
            {
                "bia": "https://bioimage-archive.org/ro-crate/",
                "dwc": "http://rs.tdwg.org/dwc/terms/",
                "bao": "http://www.bioassayontology.org/bao#",
                "dwciri": "http://rs.tdwg.org/dwc/iri/",
                "vernacularName": {"@id": "dwc:vernacularName"},
                "scientificName": {"@id": "dwc:scientificName"},
                "BioSample": {"@id": "http://schema.org/BioSample"},
                "LabProtocol": {"@id": "http://schema.org/LabProtocol"},
                "labEquipment": {"@id": "http://schema.org/labEquipment"},
                "hasCellLine": {"@id": "bao:BAO_0002004", "@container": "@set"},
                "measurementMethod": {
                    "@id": "dwciri:measurementMethod",
                    "@container": "@set",
                },
                "taxonomicRange": {
                    "@id": "http://schema.org/taxonomicRange",
                    "@container": "@set",
                },
                "seeAlso": {"@id": "rdf:seeAlso", "@container": "@set"},
                "measurementTechnique": {
                    "@id": "http://schema.org/measurementTechnique",
                    "@container": "@set",
                },
                "about": {"@id": "http://schema.org/about", "@container": "@set"},
                "citation": {"@id": "http://schema.org/citation", "@container": "@set"},
                "author": {
                    "@id": "http://schema.org/author",
                    "@container": "@set",
                },
                "affiliation": {
                    "@id": "http://schema.org/affiliation",
                    "@container": "@set",
                },
                "funder": {"@id": "http://schema.org/funder", "@container": "@set"},
                "keywords": {"@id": "http://schema.org/keywords", "@container": "@set"},
                "size": {"@id": "http://schema.org/size", "@container": "@set"},
                "thumbnailUrl": {
                    "@id": "http://schema.org/thumbnailUrl",
                    "@container": "@set",
                },
                "@type": {"@container": "@set"},
                # "id": "@id",
            },
        ],
        "@type": "Dataset",
        "@embed": "@always",
    }

    def __init__(self):
        super().__init__()

    def transform(self, single_object: dict):

        framed_doc = jsonld.frame(single_object, self.FRAME)

        if not isinstance(framed_doc, dict):
            raise TypeError()

        framed_doc.pop("@context")

        dataset = IndexableDataset.model_validate(framed_doc)

        return dataset.model_dump(by_alias=False)

    def collect_objects(self, path: str | Path):
        path = Path(path)

        if path.is_dir():
            path = path / "ro-crate-metadata.json"

        if not (path.is_file and path.name == "ro-crate-metadata.json" and path.exists):
            if not path.is_file:
                print(path.is_file)
            raise ValueError(f"Needs {path} to exist to process ro-crate-metadata.json")

        with open(path) as f:
            document = json.load(f)

        return document
