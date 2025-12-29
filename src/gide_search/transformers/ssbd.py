"""SSBD ontology to unified schema transformer."""

from datetime import date
from pathlib import Path

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDF, RDFS

from ..schema import (
    BioSample,
    ImageAcquisitionProtocol,
    ImagingMethod,
    Organism,
    Publication,
    Source,
    Study,
)

# SSBD namespaces
ONTOLOGY = Namespace("http://ssbd.riken.jp/ontology/")
OBO = Namespace("http://purl.obolibrary.org/obo/")


class SSBDTransformer:
    """Transform SSBD ontology data to unified Study schema."""

    def __init__(self, ttl_path: Path | str):
        self.graph = Graph()
        self.graph.parse(ttl_path, format="turtle")
        self._build_project_mappings()

    def _build_project_mappings(self) -> None:
        """Build mappings from datasets to projects and projects to publications."""
        # Map dataset URI -> project URI
        self._dataset_to_project: dict[str, URIRef] = {}
        # Map project URI -> list of publication URIs
        self._project_publications: dict[str, list[URIRef]] = {}
        # Map project URI -> project metadata
        self._project_metadata: dict[str, dict] = {}

        # Find all SSBD_Project instances
        for project_uri in self.graph.subjects(RDF.type, ONTOLOGY.SSBD_Project):
            project_key = str(project_uri)

            # Get datasets for this project
            for dataset_uri in self.graph.objects(project_uri, ONTOLOGY.has_dataset_output):
                self._dataset_to_project[str(dataset_uri)] = project_uri

            # Get publications for this project
            pubs = []
            for pub_uri in self.graph.objects(project_uri, ONTOLOGY.has_project_publications):
                pubs.append(pub_uri)
            self._project_publications[project_key] = pubs

            # Get project metadata
            self._project_metadata[project_key] = {
                "url": self._get_literal(project_uri, ONTOLOGY.has_project_url),
                "description": self._get_literal(project_uri, ONTOLOGY.has_description),
                "license": self._get_literal(project_uri, ONTOLOGY.has_license),
                "submission_date": self._get_literal(project_uri, ONTOLOGY.has_submission_date),
            }

    def _get_publications_for_dataset(self, dataset_uri: URIRef) -> list[Publication]:
        """Get publications associated with a dataset via its project."""
        project_uri = self._dataset_to_project.get(str(dataset_uri))
        if not project_uri:
            return []

        pub_uris = self._project_publications.get(str(project_uri), [])
        return [self._parse_paper(pub_uri) for pub_uri in pub_uris]

    def _get_project_metadata(self, dataset_uri: URIRef) -> dict:
        """Get project metadata for a dataset."""
        project_uri = self._dataset_to_project.get(str(dataset_uri))
        if not project_uri:
            return {}
        return self._project_metadata.get(str(project_uri), {})

    def _extract_ncbi_taxon_id(self, uri: URIRef) -> int | None:
        """Extract NCBI Taxon ID from URI like obo:NCBITaxon_10090."""
        uri_str = str(uri)
        if "NCBITaxon_" in uri_str:
            try:
                return int(uri_str.split("NCBITaxon_")[-1])
            except ValueError:
                return None
        return None

    def _extract_fbbi_id(self, uri: URIRef) -> str | None:
        """Extract FBbi ID from URI like obo:FBbi_00050000."""
        uri_str = str(uri)
        if "FBbi_" in uri_str:
            # Return in standard format: FBbi:00050000
            fbbi_num = uri_str.split("FBbi_")[-1]
            return f"FBbi:{fbbi_num}"
        return None

    def _get_literal(self, subject: URIRef, predicate: URIRef) -> str | None:
        """Get a literal value for a subject-predicate pair."""
        for obj in self.graph.objects(subject, predicate):
            return str(obj)
        return None

    def _get_object(self, subject: URIRef, predicate: URIRef) -> URIRef | None:
        """Get an object URI for a subject-predicate pair."""
        for obj in self.graph.objects(subject, predicate):
            if isinstance(obj, URIRef):
                return obj
        return None

    def _parse_biosample(self, biosample_uri: URIRef) -> BioSample:
        """Parse SSBD_biosample_information to BioSample."""
        organisms = []

        # Get organism (NCBI Taxon)
        org_uri = self._get_object(biosample_uri, ONTOLOGY.is_about_organism)
        if org_uri:
            ncbi_id = self._extract_ncbi_taxon_id(org_uri)
            # Try to get organism name from label, fallback to URI parsing
            org_name = self._get_literal(org_uri, RDFS.label)
            if not org_name and ncbi_id:
                org_name = f"NCBITaxon:{ncbi_id}"
            organisms.append(Organism(scientific_name=org_name or "Unknown", ncbi_taxon_id=ncbi_id))

        # Get strain
        strain_uri = self._get_object(biosample_uri, ONTOLOGY.is_about_strain)
        strain = str(strain_uri) if strain_uri else None

        return BioSample(
            organism=organisms if organisms else [Organism(scientific_name="Unknown")],
            sample_type="unknown",  # SSBD doesn't seem to have this directly
            strain=strain,
        )

    def _parse_imaging_method(self, imaging_uri: URIRef) -> ImageAcquisitionProtocol:
        """Parse SSBD_imaging_method_information to ImageAcquisitionProtocol."""
        methods = []

        # Get imaging method type (FBbi ontology)
        method_uri = self._get_object(imaging_uri, ONTOLOGY.has_imaging_method_recorded_type)
        if method_uri:
            fbbi_id = self._extract_fbbi_id(method_uri)
            method_name = self._get_literal(method_uri, RDFS.label)
            if not method_name and fbbi_id:
                method_name = fbbi_id
            methods.append(ImagingMethod(name=method_name or "Unknown", fbbi_id=fbbi_id))

        # Get instrument description (has_body contains instrument model)
        imaging_instrument_description = self._get_literal(imaging_uri, ONTOLOGY.has_body)

        return ImageAcquisitionProtocol(
            methods=methods if methods else [ImagingMethod(name="Unknown")],
            imaging_instrument_description=imaging_instrument_description,
        )

    def _parse_paper(self, paper_uri: URIRef) -> Publication:
        """Parse SSBD_paper_information to Publication."""
        doi = self._get_literal(paper_uri, ONTOLOGY.has_doi)
        pmid = self._get_literal(paper_uri, ONTOLOGY.has_PMID)
        paper_info = self._get_literal(paper_uri, ONTOLOGY.has_paper_information)

        # Extract authors and title from citation string
        # Format: "Author1, Author2 (Year) Title, Journal, ..."
        authors_name = None
        title = paper_info
        year = None

        if paper_info:
            import re

            # Match pattern: "Authors (Year) Rest..."
            match = re.match(r"^(.+?)\s*\((\d{4})\)\s*(.+)$", paper_info, re.DOTALL)
            if match:
                authors_name = match.group(1).strip()
                try:
                    year = int(match.group(2))
                except ValueError:
                    pass
                # Use the rest as title (first part before comma is typically the title)
                rest = match.group(3).strip()
                # Try to extract just the title (before journal info)
                parts = rest.split(",")
                if parts:
                    title = parts[0].strip()

        return Publication(
            doi=doi,
            pubmed_id=pmid,
            title=title,
            authors_name=authors_name,
            year=year,
        )

    def _get_dataset_id(self, dataset_uri: URIRef) -> str:
        """Extract dataset ID from URI."""
        # URI like: http://ssbd.riken.jp/ontology/ssbd-dataset-141-Fig1a_FIB-SEM_somatosensory
        uri_str = str(dataset_uri)
        if "ssbd-dataset-" in uri_str:
            return uri_str.split("/")[-1]
        return uri_str

    def transform_all(self) -> list[Study]:
        """Transform all SSBD datasets to Study objects."""
        studies = []

        # Find all SSBD_dataset instances
        for dataset_uri in self.graph.subjects(RDF.type, ONTOLOGY.SSBD_dataset):
            study = self.transform_dataset(dataset_uri)
            if study:
                studies.append(study)

        return studies

    def transform_dataset(self, dataset_uri: URIRef) -> Study | None:
        """Transform a single SSBD dataset to a Study."""
        dataset_id = self._get_dataset_id(dataset_uri)

        # Get title
        title = self._get_literal(dataset_uri, ONTOLOGY.has_dataset_title)
        if not title:
            title = self._get_literal(dataset_uri, RDFS.label) or dataset_id

        # Get biosample info
        biosample_uri = self._get_object(dataset_uri, ONTOLOGY.has_biosample_information)
        biosample = self._parse_biosample(biosample_uri) if biosample_uri else BioSample(
            organism=[Organism(scientific_name="Unknown")],
            sample_type="unknown",
        )

        # Get imaging method info
        imaging_uri = self._get_object(dataset_uri, ONTOLOGY.has_imaging_method_total_info)
        image_acquisition_protocol = self._parse_imaging_method(imaging_uri) if imaging_uri else ImageAcquisitionProtocol(
            methods=[ImagingMethod(name="Unknown")],
        )

        # Get publications via project
        publications = self._get_publications_for_dataset(dataset_uri)

        # Get project metadata for better source URL and description
        project_meta = self._get_project_metadata(dataset_uri)
        source_url = project_meta.get("url") or f"https://ssbd.riken.jp/repository/{dataset_id}/"
        description = project_meta.get("description") or title

        # Parse submission date if available
        release_date = date(2025, 5, 12)  # Default from ontology version
        if project_meta.get("submission_date"):
            try:
                parts = project_meta["submission_date"].split("-")
                release_date = date(int(parts[0]), int(parts[1]), int(parts[2]))
            except (ValueError, IndexError):
                pass

        return Study(
            id=f"ssbd:{dataset_id}",
            source=Source.SSBD,
            source_url=source_url,
            title=title,
            description=description,
            license="CC BY 4.0",  # SSBD default license
            release_date=release_date,
            biosamples=[biosample],
            image_acquisition_protocols=[image_acquisition_protocol],
            publications=publications,
        )
