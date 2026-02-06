from pydantic import AnyUrl, ValidationError
from pyld import jsonld

from gide_search_v2.schema_search_object import Entry
from gide_search_v2.transformers.to_rocrate import ROCrateTransformer


class BIAROCrateTransformer(ROCrateTransformer):
    generated_ids: set[str]

    def __init__(self):
        self.generated_ids = set()
        super().__init__()

    def _get_root_dataset(self, bia_search_hit: dict):

        accession_id = bia_search_hit["accession_id"]
        return {
            "@id": f"https://www.ebi.ac.uk/biostudies/bioimages/studies/{accession_id}",
            "@type": ["Dataset"],
            "identifier": accession_id,
            "name": bia_search_hit["title"],
            "description": bia_search_hit["description"],
            "datePublished": str(bia_search_hit["release_date"]),
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
            try:
                grant_id_url = str(AnyUrl(bia_grant["id"]))
            except ValidationError:
                grant_id_url = self._generate_ref_id(bia_grant["id"])

            funders.append(
                {
                    "@id": grant_id_url,
                    "@type": ["Grant"],
                    "name": None,
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
                taxons = []
                for bia_taxon in bia_bio_sample["organism_classification"]:
                    if bia_taxon["ncbi_id"]:
                        taxons.append(
                            {
                                "@type": ["Taxon"],
                                "vernacularName": bia_taxon["common_name"],
                                "scientificName": bia_taxon["scientific_name"],
                                "@id": bia_taxon["ncbi_id"]
                                or self._generate_ref_id(bia_taxon["common_name"]),
                            }
                        )
                        taxons_ids.add(str(bia_taxon["ncbi_id"]))

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

    def _get_imaging_protocols(self, bia_search_hit: dict):
        imaging_protocol = []
        imaginge_method_ids = set()
        for dataset in bia_search_hit["dataset"]:
            for bia_image_acquisition_protocol in dataset["acquisition_process"]:
                imaging_methods = []

                for fbbi_id in bia_image_acquisition_protocol["fbbi_id"]:
                    if fbbi_id:
                        imaging_methods.append(
                            {
                                "@id": fbbi_id,
                                "@type": ["DefinedTerm"],
                                "name": self._get_fbbi_label_from_ontology(fbbi_id),
                            }
                        )
                        imaginge_method_ids.add(str(fbbi_id))

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
        imaging_protocol += [{"@id": imaging_id} for imaging_id in imaginge_method_ids]
        return imaging_protocol

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
        for bia_author in bia_authors:
            authors.append(
                {
                    "@id": (
                        self._standardise_orcid(bia_author["orcid"])
                        if bia_author["orcid"]
                        else self._generate_ref_id(
                            bia_author["display_name"], force_unique=True
                        )
                    ),
                    "@type": ["Person"],
                    "name": bia_author["display_name"],
                    "email": bia_author.get("contact_email"),
                    "affiliation": self._get_affiliation(bia_author["affiliation"]),
                }
            )
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
                    "@type": ["Organisation"],
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
                self._get_ro_crate_ref(entry_uri, accession_id),
                self._get_root_dataset(single_object),
            ],
        }
        return jsonld.flatten(ro_crate_metadata, ctx=self._get_ro_crate_context())
