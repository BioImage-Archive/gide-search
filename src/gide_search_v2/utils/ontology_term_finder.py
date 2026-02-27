import json
import logging
from dataclasses import dataclass
from functools import cache

from ols_client import EBIClient
from requests.exceptions import HTTPError

logger = logging.getLogger("__main__." + __name__)


@dataclass
class TermWithLabels:
    iri: str
    label: list[str]
    additional_label: list[str]
    short_id: list[str]


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

    @staticmethod
    def _collect_short_ids(short_id: str | list[str], short_ids: list):
        if short_id:
            if isinstance(short_id, str):
                short_ids.append(short_id)
            else:
                short_ids += short_id

    @cache
    def fetch_labels_for_term(self, ontology: str, term_iri: str):
        if ontology not in self.avaliable_ontology_ids:
            raise KeyError(f"{ontology} is not in ols")

        term_iri = term_iri.removeprefix("obo:")

        try:
            response = self.ebi_client.get_term(ontology, term_iri)
        except HTTPError as e:
            logger.warning(e)
            logger.warning(f"{term_iri} not found.")
            return

        term_info = response["_embedded"]["terms"][0]

        return self._create_term_with_labels(term_info)

    @cache
    def _get_iri_for_class_in_ontology(
        self, ontology: str, search_terms: str, required_superclass: str | None = None
    ) -> list[TermWithLabels]:
        api_response = self._find_class_in_ontology(ontology, search_terms)

        iris_and_labels: list[TermWithLabels] = []
        for ontology_term in api_response["elements"]:
            if required_superclass:
                for ancestor in ontology_term["hierarchicalAncestor"]:
                    if ancestor["iri"] == required_superclass:
                        iris_and_labels.append(
                            self._create_term_with_labels(ontology_term)
                        )
                        break
            else:
                iris_and_labels.append(self._create_term_with_labels(ontology_term))

        return iris_and_labels

    def _create_term_with_labels(self, ontology_term) -> TermWithLabels:
        short_ids = []
        self._collect_short_ids(ontology_term.get("obo_id"), short_ids)
        self._collect_short_ids(ontology_term.get("curie"), short_ids)
        self._collect_short_ids(ontology_term.get("short_form"), short_ids)

        label = (
            ontology_term["label"]
            if isinstance(ontology_term["label"], list)
            else [ontology_term["label"]]
        )

        return TermWithLabels(
            **{
                "iri": ontology_term["iri"],
                "label": label,
                "additional_label": ontology_term.get("synonyms", []),
                "short_id": short_ids,
            }
        )

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
