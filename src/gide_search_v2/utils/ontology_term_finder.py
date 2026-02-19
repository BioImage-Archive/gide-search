import json
from functools import cache

from ols_client import EBIClient


class OntologyTermFinder:
    ebi_client: EBIClient
    avaliable_ontology_ids: list[str]

    def __init__(
        self,
    ) -> None:
        self.ebi_client = EBIClient()
        ontologies = self.ebi_client.get_ontologies()
        self.avaliable_ontology_ids = []
        for ontology in ontologies:
            self.avaliable_ontology_ids.append(ontology["ontologyId"])

    @staticmethod
    def _simplify_search_term(search_terms: str):
        # To make it more likely to hit a cache, perform a small ammount of cleanup on the strings before searching
        search_terms = search_terms.strip().lower()

        return search_terms

    def find_iri_for_class_in_ontology(
        self, ontology: str, search_terms: str, required_superclass: str | None = None
    ):
        if ontology not in self.avaliable_ontology_ids:
            raise KeyError(f"{ontology} is not in ols")

        search_terms = self._simplify_search_term(search_terms)

        return self._get_iri_for_class_in_ontology(
            ontology, search_terms, required_superclass
        )

    @cache
    def _get_iri_for_class_in_ontology(
        self, ontology: str, search_terms: str, required_superclass: str | None = None
    ):
        api_response = self._find_class_in_ontology(ontology, search_terms)

        iris_and_labels: list[tuple[str, list[str]]] = []
        for ontology_term in api_response["elements"]:
            if required_superclass:
                for ancestor in ontology_term["hierarchicalAncestor"]:
                    if ancestor["iri"] == required_superclass:
                        iris_and_labels.append(
                            (ontology_term["iri"], ontology_term["label"])
                        )
                        break
            else:
                iris_and_labels.append((ontology_term["iri"], ontology_term["label"]))

        return iris_and_labels

    def _find_class_in_ontology(self, ontology: str, search_terms: str):
        response = self.ebi_client.get_response(
            path=f"v2/ontologies/{ontology}/classes",
            params={
                "search": search_terms,
                "page": 0,
                "size": 20,
                "searchFields": "label^100 synonym^5 description",
                "definedBy": ontology,
                "resolveReferences": True,
                "manchesterSyntax": True,
                "lang": "en",
            },
        )

        parsed_response = json.loads(response.content)

        return parsed_response
