import hashlib
from uuid import UUID

import httpx
from rdflib import Graph, URIRef
from rdflib.namespace import RDFS

from gide_search_v2.transformers.base_transformer import Transformer


class ROCrateTransformer(Transformer):
    generated_ids: set[str]

    def __init__(self):
        self.generated_ids = set()
        super().__init__()

    def _get_ro_crate_context(self) -> str | dict | list[dict | str]:
        return [
            "https://w3id.org/ro/crate/1.2/context",
            {
                "bia": "https://bioimage-archive.org/ro-crate/",
                "obo": "http://purl.obolibrary.org/obo/",
                "dwc": "http://rs.tdwg.org/dwc/terms/",
                "dwciri": "http://rs.tdwg.org/dwc/iri/",
                "bao": "http://www.bioassayontology.org/bao#",
                "xsd": "http://www.w3.org/2001/XMLSchema#",
                "vernacularName": {"@id": "dwc:vernacularName"},
                "scientificName": {"@id": "dwc:scientificName"},
                "hasCellLine": {"@id": "bao:BAO_0002004"},
                "measurementMethod": {"@id": "dwciri:measurementMethod"},
                "seeAlso": {"@id": "rdf:seeAlso"},
                "BioSample": {"@id": "http://schema.org/BioSample"},
                "LabProtocol": {"@id": "http://schema.org/LabProtocol"},
                "labEquipment": {"@id": "http://schema.org/labEquipment"},
                "datePublished": {
                    "@id": "http://schema.org/datePublished",
                    "@type": "xsd:date",
                },
            },
        ]

    def _get_ro_crate_context_with_containers(self) -> list | str:
        return [
            "https://w3id.org/ro/crate/1.2/context",
            {
                "bia": "https://bioimage-archive.org/ro-crate/",
                "obo": "http://purl.obolibrary.org/obo/",
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
                "measurementTechnique": {
                    "@id": "http://schema.org/measurementTechnique",
                    "@container": "@set",
                },
                "seeAlso": {"@id": "rdf:seeAlso", "@container": "@set"},
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
                "thumbnailUrl": {
                    "@id": "http://schema.org/thumbnailUrl",
                    "@container": "@set",
                },
                "@type": {"@container": "@set"},
            },
        ]

    def _get_ro_crate_ref(self, entry_url: str, database_id: str) -> dict:
        return {
            "@id": f"{database_id}-ro-crate-metadata.json",
            "@type": "CreativeWork",
            "conformsTo": {"@id": "https://w3id.org/ro/crate/1.2"},
            "about": {"@id": entry_url},
        }

    def _generate_ref_id(self, key: str, force_unique: bool = False) -> str:
        hexdigest = hashlib.md5(key.encode("utf-8")).hexdigest()
        relative_ref = f"#{UUID(version=4, hex=hexdigest)}"
        if force_unique and relative_ref in self.generated_ids:
            relative_ref = self._generate_ref_id(relative_ref, force_unique=True)
        self.generated_ids.add(relative_ref)
        return relative_ref
