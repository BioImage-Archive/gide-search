import json
from pathlib import Path

from pyld import jsonld

from gide_search_v2.schema_search_object import Entry
from gide_search_v2.transformers.base_transformer import Transformer


class ROCrateIndexTransformer(Transformer):
    FRAME = {
        "@context": [
            "https://w3id.org/ro/crate/1.2/context",
            {
                "bia": "https://bioimage-archive.org/ro-crate/",
                "obo": "http://purl.obolibrary.org/obo/",
                "dwc": "http://rs.tdwg.org/dwc/terms/",
                "bao": "http://www.bioassayontology.org/bao#",
                "vernacularName": {"@id": "dwc:vernacularName"},
                "scientificName": {"@id": "dwc:scientificName"},
                "BioSample": {"@id": "http://schema.org/BioSample"},
                "LabProtocol": {"@id": "http://schema.org/LabProtocol"},
                "hasCellLine": {"@id": "bao:BAO_0002004", "@container": "@set"},
                "measurementMethod": {
                    "@id": "dwc:measurementMethod",
                    "@container": "@set",
                },
                "measurementTechnique": {
                    "@id": "http://schema.org/measurementTechnique",
                    "@container": "@set",
                },
                "about": {"@id": "http://schema.org/about", "@container": "@set"},
                "citation": {"@id": "http://schema.org/citation", "@container": "@set"},
                "author": {"@id": "http://schema.org/author", "@container": "@set"},
                "affiliation": {
                    "@id": "http://schema.org/affiliation",
                    "@container": "@set",
                },
                "funder": {"@id": "http://schema.org/funder", "@container": "@set"},
                "keywords": {"@id": "http://schema.org/keywords", "@container": "@set"},
                "size": {"@id": "http://schema.org/size", "@container": "@set"},
                "image": {"@id": "http://schema.org/image", "@container": "@set"},
                "type": {"@id": "@type", "@container": "@set"},
                "id": "@id",
            },
        ],
        "@type": "Dataset",
        "identifier": {},
        "name": {},
        "description": {},
        "datePublished": {},
        "license": {},
        "keywords": {},
        "publisher": {
            "name": {},
            "url": {},
        },
        "author": {
            "affiliation": {"name": {}, "url": {}, "address": {}},
            "name": {},
            "email": {},
        },
        "funder": {"name": {}, "identifier": {}},
        "citation": {"name": {}, "datePublished": {}},
        "about": {
            "name": {},
            "description": {},
            "taxonomicRange": {"vernacularName": {}, "scientificName": {}},
            "hasCellLine": {"name": {}},
        },
        "measurementMethod": {
            "name": {},
            "description": {},
            "measurementTechnique": {"name": {}},
            "labEquipment": {},
        },
        "image": {},
        "size": {"value": {}, "unitText": {}, "unitCode": {}},
    }

    def __init__(self):
        super().__init__()

    def transform(self, single_object: dict):

        framed_doc = jsonld.frame(single_object, self.FRAME, options={"explicit": True})

        if not isinstance(framed_doc, dict):
            raise TypeError()

        framed_doc.pop("@context")

        Entry.model_validate(framed_doc)

        return framed_doc

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
