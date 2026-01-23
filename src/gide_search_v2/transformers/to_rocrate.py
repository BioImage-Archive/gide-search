import hashlib
from uuid import UUID

import httpx
from rdflib import Graph, URIRef
from rdflib.namespace import RDFS

from gide_search_v2.transformers.base_transformer import Transformer


class ROCrateTransformer(Transformer):
    generated_ids: set[str]
    fbbi_label_cache: dict

    def __init__(self):
        self.generated_ids = set()
        self.fbbi_label_cache = {}
        super().__init__()

    def _get_ro_crate_context(self) -> str | dict | list[dict | str]:
        return [
            "https://w3id.org/ro/crate/1.1/context",
            {
                "bia": "https://bioimage-archive.org/ro-crate/",
                "obo": "http://purl.obolibrary.org/obo/",
                "dwc": "http://rs.tdwg.org/dwc/terms/",
                "bao": "http://www.bioassayontology.org/bao#",
                "vernacularName": {"@id": "dwc:vernacularName"},
                "scientificName": {"@id": "dwc:scientificName"},
                "hasCellLine": {"@id": "bao:BAO_0002004"},
                "measurementMethod": {"@id": "dwc:measurementMethod"},
                "BioSample": {"@id": "http://schema.org/BioSample"},
                "LabProtocol": {"@id": "http://schema.org/LabProtocol"},
                "DefinedTerm": {"@id": "http://schema.org/DefinedTerm"},
            },
        ]

    def _get_ro_crate_ref(self, entry_id: str) -> dict:
        return {
            "@id": "ro-crate-metadata.json",
            "@type": "CreativeWork",
            "conformsTo": {"@id": "https://w3id.org/ro/crate/1.1"},
            "about": {"@id": entry_id},
        }

    def _generate_ref_id(self, key: str, force_unique: bool = False) -> str:
        hexdigest = hashlib.md5(key.encode("utf-8")).hexdigest()
        relative_ref = f"#{UUID(version=4, hex=hexdigest)}"
        if force_unique and relative_ref in self.generated_ids:
            relative_ref = self._generate_ref_id(relative_ref, force_unique=True)
        self.generated_ids.add(relative_ref)
        return relative_ref

    def _get_fbbi_label_from_ontology(self, fbbi_term: str) -> str | None:
        """Fetch and cache the label for an FBBI ontology term from the OWL document."""
        # Check cache first
        if fbbi_term in self.fbbi_label_cache:
            return self.fbbi_label_cache[fbbi_term]

        graph = Graph()
        try:
            response = httpx.get(fbbi_term, timeout=10, follow_redirects=True)
            response.raise_for_status()
            graph.parse(data=response.text, format="xml")
        except Exception as e:
            self.fbbi_label_cache[fbbi_term] = None
            return None

        term_uri = URIRef(fbbi_term)
        labels = list(graph.objects(term_uri, RDFS.label))
        if labels:
            label = str(labels[0])
            self.fbbi_label_cache[fbbi_term] = label
            return label
        else:
            self.fbbi_label_cache[fbbi_term] = None
            return None
