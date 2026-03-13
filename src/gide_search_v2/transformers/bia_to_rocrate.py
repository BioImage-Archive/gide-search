import re

from pydantic import AnyUrl, ValidationError
from pyld import jsonld

from gide_search_v2.transformers.to_rocrate import ROCrateTransformer
from gide_search_v2.utils.ontology_term_finder import OntologyTermFinder


class BIAROCrateTransformer(ROCrateTransformer):
    generated_ids: set[str]
    TYPE_ORDER: dict[str, int] = {
        "CreativeWork": 0,
        "Dataset": 1,
        "Person": 2,
        "Organization": 3,
        "Grant": 4,
        "ScholarlyArticle": 5,
        "Taxon": 6,
        "BioSample": 7,
        "LabProtocol": 8,
        "DefinedTerm": 9,
        "QuantitiveValue": 10,
    }

    def __init__(self, ontology_term_finder: OntologyTermFinder):
        self.generated_ids = set()
        self.ontology_term_finder = ontology_term_finder
        super().__init__()

    def type_rank(self, d):
        return min(self.TYPE_ORDER.get(t, float("inf")) for t in d.get("@type", []))

    def _get_root_dataset(self, bia_search_hit: dict):

        accession_id = bia_search_hit["accession_id"]
        return {
            "@id": f"https://www.ebi.ac.uk/biostudies/bioimages/studies/{accession_id}",
            "@type": ["Dataset"],
            "identifier": accession_id,
            "name": bia_search_hit["title"],
            "description": bia_search_hit["description"],
            "datePublished": str(bia_search_hit["release_date"]),
            "license": bia_search_hit["licence"],
            "keywords": bia_search_hit["keyword"],
            "publisher": self._get_publisher(),
            "author": self._get_authors(bia_search_hit["author"]),
            "funder": self._get_funder(bia_search_hit["grant"]),
            "citation": self._get_citation(bia_search_hit["related_publication"]),
            "about": self._get_bio_samples(bia_search_hit),
            "measurementMethod": self._get_imaging_protocols(bia_search_hit),
            "size": self._get_size(bia_search_hit),
            "thumbnailUrl": self._get_image(bia_search_hit),
        }

    def _get_funder(self, bia_grants: list[dict]):
        funders = []
        for bia_grant in bia_grants:
            if bia_grant.get("id") and len(bia_grant.get("funder", ())) > 1:
                try:
                    grant_id_url = str(AnyUrl(bia_grant["id"]))
                except ValidationError:
                    grant_id_url = self._generate_ref_id(bia_grant["id"])

                # Use funder name:

                funders.append(
                    {
                        "@id": grant_id_url,
                        "@type": ["Grant"],
                        "name": bia_grant.get("funder", [{}])[0].get("display_name"),
                        # TODO: use name from grant funder?
                        "identifier": bia_grant["id"],
                    }
                )
        return funders

    def _get_citation(self, bia_publications: list[dict]):
        publications = []
        for bia_publication in bia_publications:
            publications.append(
                {
                    "@id": bia_publication["doi"]
                    or bia_publication["pubmed_id"]
                    or self._generate_ref_id(bia_publication["title"]),
                    "@type": ["ScholarlyArticle"],
                    "name": bia_publication["title"],
                    "datePublished": str(bia_publication["publication_year"]),
                }
            )
        return publications

    def _get_bio_samples(self, bia_search_hit: dict):
        bio_samples = []
        taxons_ids = set()
        for dataset in bia_search_hit["dataset"]:
            for bia_bio_sample in dataset["biological_entity"]:
                taxons = self._get_taxons_from_ontology(bia_bio_sample)
                [taxons_ids.add(taxon["@id"]) for taxon in taxons]

                bio_samples.append(
                    {
                        "@id": f"#{bia_bio_sample["uuid"]}",
                        "@type": ["BioSample"],
                        "name": bia_bio_sample["title"],
                        "description": bia_bio_sample["biological_entity_description"],
                        "taxonomicRange": taxons,
                    }
                )

        bio_samples += [{"@id": taxon_id} for taxon_id in taxons_ids]

        return bio_samples

    def _get_taxons_from_ontology(self, bia_bio_sample):
        taxons = []
        for bia_taxon in bia_bio_sample["organism_classification"]:
            if bia_taxon["ncbi_id"]:
                # Fetch labels from ontology to make sure we use canonical values.
                ncbi_id: str = bia_taxon["ncbi_id"]
                if not ncbi_id.startswith("http"):
                    match = re.search(r"(\d+)$", ncbi_id)
                    if match:
                        ncbi_id = f"http://purl.obolibrary.org/obo/NCBITaxon_{int(match.group(1))}"
                    else:
                        continue

                term_with_labels = self.ontology_term_finder.fetch_labels_for_term(
                    "ncbitaxon", ncbi_id
                )
                if term_with_labels:
                    taxons.append(
                        {
                            "@type": ["Taxon"],
                            "vernacularName": (
                                term_with_labels.additional_label[0]
                                if term_with_labels.additional_label
                                else None
                            ),
                            "scientificName": term_with_labels.label[0],
                            "@id": term_with_labels.iri,
                        }
                    )

            else:
                search_term = bia_taxon["scientific_name"] or bia_taxon["common_name"]
                possible_terms = (
                    self.ontology_term_finder.find_iri_for_class_in_ontology(
                        "ncbitaxon", search_term
                    )
                )
                if len(possible_terms) > 0:
                    term_with_labels = possible_terms[0]
                    taxons.append(
                        {
                            "@type": ["Taxon"],
                            "vernacularName": next(
                                iter(term_with_labels.additional_label), None
                            ),
                            "scientificName": term_with_labels.label[0],
                            "@id": term_with_labels.iri,
                        }
                    )
        return taxons

    def _get_imaging_protocols(self, bia_search_hit: dict):
        imaging_protocol = []
        imaging_method_ids = set()
        for dataset in bia_search_hit["dataset"]:
            for bia_image_acquisition_protocol in dataset["acquisition_process"]:
                imaging_methods = self._get_imaging_method_from_ontology(
                    bia_image_acquisition_protocol
                )
                [
                    imaging_method_ids.add(imaging_method["@id"])
                    for imaging_method in imaging_methods
                ]

                imaging_protocol.append(
                    {
                        "@id": f"#{bia_image_acquisition_protocol["uuid"]}",
                        "@type": ["LabProtocol"],
                        "name": bia_image_acquisition_protocol["title"],
                        "description": bia_image_acquisition_protocol[
                            "protocol_description"
                        ],
                        "labEquipment": bia_image_acquisition_protocol[
                            "imaging_instrument_description"
                        ],
                        "measurementTechnique": imaging_methods,
                    }
                )
        imaging_protocol += [{"@id": imaging_id} for imaging_id in imaging_method_ids]
        return imaging_protocol

    def _get_imaging_method_from_ontology(self, bia_image_acquisition_protocol):
        imaging_methods = []

        if len(bia_image_acquisition_protocol["fbbi_id"]) == 0:
            for imaging_method_name in bia_image_acquisition_protocol[
                "imaging_method_name"
            ]:
                if len(imaging_method_name) > 120:
                    continue
                terms = self.ontology_term_finder.find_iri_for_class_in_ontology(
                    "fbbi",
                    imaging_method_name,
                    "http://purl.obolibrary.org/obo/FBbi_00000265",
                )
                if len(terms) > 0:
                    imaging_methods.append(
                        {
                            "@id": terms[0].iri,
                            "@type": ["DefinedTerm"],
                            "name": terms[0].label[0],
                        }
                    )
        else:
            for fbbi_id in bia_image_acquisition_protocol["fbbi_id"]:
                term_with_labels = self.ontology_term_finder.fetch_labels_for_term(
                    "fbbi", fbbi_id
                )
                if term_with_labels:
                    imaging_methods.append(
                        {
                            "@id": fbbi_id,
                            "@type": ["DefinedTerm"],
                            "name": next(iter(term_with_labels.label)),
                        }
                    )
        return imaging_methods

    def _get_size(self, bia_search_hit: dict):
        file_count = 0
        bytes_size = 0
        for dataset in bia_search_hit["dataset"]:
            file_count += dataset["file_reference_count"]
            bytes_size += dataset["file_reference_size_bytes"]

        return [
            {
                "@id": self._generate_ref_id("#total-file-size"),
                "@type": "QuantitiveValue",
                "value": bytes_size,
                "unitCode": "http://purl.obolibrary.org/obo/UO_0000233",
                "unitText": "bytes",
            },
            {
                "@id": self._generate_ref_id("#file-count"),
                "@type": "QuantitiveValue",
                "value": file_count,
                "unitCode": "http://purl.obolibrary.org/obo/UO_0000189",
                "unitText": "file count",
            },
        ]

    def _get_image(self, bia_search_hit: dict):
        image_links = []
        for dataset in bia_search_hit["dataset"]:
            image_links.append(dataset["example_image_uri"])
        return image_links

    def _get_publisher(self):
        return {
            "@id": "https://www.ebi.ac.uk/bioimage-archive/",
            "@type": ["Organization"],
            "name": "BioImage Archive",
        }

    def _get_authors(self, bia_authors: list[dict]):
        authors = []
        author_ids = set()
        for bia_author in bia_authors:
            if (
                bia_author.get("orcid")
                and (orcid := self._standardise_orcid(bia_author["orcid"]))
                not in author_ids
            ):
                author_id = orcid
            else:
                author_id = self._generate_ref_id(
                    bia_author["display_name"], force_unique=True
                )

            author = {
                "@id": author_id,
                "@type": ["Person"],
                "name": bia_author["display_name"],
                "email": bia_author.get("contact_email"),
                "affiliation": self._get_affiliation(bia_author["affiliation"]),
            }
            authors.append(author)
            author_ids.add(author_id)
        return authors

    @staticmethod
    def _standardise_orcid(orcid_id: str) -> str:
        orcid_base_url = "https://orcid.org/"
        if not orcid_id.startswith(orcid_base_url):
            return f"{orcid_base_url}{orcid_id}"
        else:
            return orcid_id

    def _get_affiliation(self, bia_affiliation_list: list[dict]):
        affiliations = []
        for bia_affiliation in bia_affiliation_list:
            affiliations.append(
                {
                    "@id": bia_affiliation["rorid"]
                    or self._generate_ref_id(bia_affiliation["display_name"]),
                    "@type": ["Organization"],
                    "name": bia_affiliation["display_name"],
                    "address": bia_affiliation["address"],
                    "url": bia_affiliation["website"],
                }
            )
        return affiliations

    def transform(self, single_object: dict) -> dict:
        accession_id = single_object["accession_id"]
        entry_uri = f"https://www.ebi.ac.uk/biostudies/bioimages/studies/{accession_id}"

        ro_crate_metadata = {
            "@context": self._get_ro_crate_context(),
            "@graph": [
                self._get_root_dataset(single_object),
            ],
        }

        flattened = jsonld.flatten(
            ro_crate_metadata, ctx=self._get_ro_crate_context_with_containers()
        )

        flattened["@context"] = self._get_ro_crate_context()
        sorted_graph_objects = sorted(
           flattened["@graph"],
            key=self.type_rank,
        )
        flattened["@graph"] = [self._get_ro_crate_ref(entry_uri)] + sorted_graph_objects
        return flattened
