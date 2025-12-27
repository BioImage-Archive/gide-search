"""BioImage Archive API to unified schema transformer."""

from datetime import date

import httpx

from ..schema import (
    Author,
    BioSample,
    Funding,
    ImageAcquisition,
    ImagingMethod,
    Organisation,
    Organism,
    Publication,
    Source,
    Study,
)

BIA_API_URL = "https://alpha.bioimagearchive.org/search/search/fts"


class BIATransformer:
    """Transform BioImage Archive API data to unified Study schema."""

    def __init__(self, page_size: int = 50):
        self.page_size = page_size

    def _parse_date(self, date_str: str | None) -> date:
        """Parse date from string like 2025-11-27."""
        if not date_str:
            return date(2024, 1, 1)
        try:
            parts = date_str.split("-")
            return date(int(parts[0]), int(parts[1]), int(parts[2]))
        except (ValueError, IndexError):
            return date(2024, 1, 1)

    def _parse_authors(self, author_list: list[dict]) -> list[Author]:
        """Parse author list from API response."""
        authors = []
        for a in author_list:
            affiliations = []
            for aff in a.get("affiliation", []) or []:
                affiliations.append(
                    Organisation(
                        display_name=aff.get("display_name", "Unknown"),
                        rorid=aff.get("rorid"),
                        address=aff.get("address"),
                        website=aff.get("website"),
                    )
                )

            authors.append(
                Author(
                    name=a.get("display_name", "Unknown"),
                    orcid=a.get("orcid"),
                    email=a.get("contact_email"),
                    affiliations=affiliations,
                )
            )
        return authors

    def _parse_funding(self, grant_list: list[dict]) -> list[Funding]:
        """Parse grant/funding list from API response."""
        funding = []
        for g in grant_list:
            grant_id = g.get("id", "")
            funders = g.get("funder", []) or []
            funder_name = funders[0].get("display_name", "Unknown") if funders else "Unknown"
            if grant_id:
                funding.append(Funding(funder=funder_name, grant_id=grant_id))
        return funding

    def _parse_publications(self, pub_list: list[dict]) -> list[Publication]:
        """Parse related publications from API response."""
        publications = []
        for p in pub_list:
            pub = Publication(
                doi=p.get("doi"),
                pubmed_id=p.get("pubmed_id"),
                title=p.get("title"),
            )
            if pub.doi or pub.pubmed_id or pub.title:
                publications.append(pub)
        return publications

    def _extract_organisms(self, datasets: list[dict]) -> list[Organism]:
        """Extract organisms from dataset biological entities."""
        organisms = []
        seen = set()

        for ds in datasets:
            for be in ds.get("biological_entity", []) or []:
                for oc in be.get("organism_classification", []) or []:
                    name = oc.get("scientific_name") or oc.get("common_name") or "Unknown"
                    if name not in seen:
                        seen.add(name)
                        # BIA doesn't provide NCBI IDs in this response
                        organisms.append(Organism(name=name, ncbi_taxon_id=None))

        return organisms if organisms else [Organism(name="Unknown")]

    def _extract_imaging_methods(self, datasets: list[dict]) -> list[ImagingMethod]:
        """Extract imaging methods from dataset acquisition processes."""
        methods = []
        seen = set()

        for ds in datasets:
            for ap in ds.get("acquisition_process", []) or []:
                # Get method names
                method_names = ap.get("imaging_method_name", []) or []
                fbbi_ids = ap.get("fbbi_id", []) or []

                for i, name in enumerate(method_names):
                    if name and name not in seen:
                        seen.add(name)
                        fbbi_id = fbbi_ids[i] if i < len(fbbi_ids) else None
                        # Format FBbi ID if present
                        if fbbi_id and not fbbi_id.startswith("FBbi:"):
                            fbbi_id = f"FBbi:{fbbi_id}"
                        methods.append(ImagingMethod(name=name, fbbi_id=fbbi_id))

        return methods if methods else [ImagingMethod(name="Unknown")]

    def _extract_sample_type(self, datasets: list[dict]) -> str:
        """Extract sample type from dataset biological entities."""
        for ds in datasets:
            for be in ds.get("biological_entity", []) or []:
                desc = be.get("biological_entity_description", "")
                title = be.get("title", "")
                # Try to infer sample type from description
                text = (desc + " " + title).lower()
                if "tissue" in text:
                    return "tissue"
                if "cell" in text:
                    return "cell"
                if "organism" in text:
                    return "organism"
        return "unknown"

    def _extract_file_stats(self, datasets: list[dict]) -> tuple[int | None, int | None]:
        """Extract file count and total size from datasets."""
        total_files = 0
        total_size = 0

        for ds in datasets:
            total_files += ds.get("file_reference_count", 0) or 0
            total_size += ds.get("file_reference_size_bytes", 0) or 0

        return (total_files or None, total_size or None)

    def transform_hit(self, hit: dict) -> Study | None:
        """Transform a single BIA API hit to a Study object."""
        source = hit.get("_source", {})

        accession_id = source.get("accession_id", "")
        if not accession_id:
            return None

        title = source.get("title", accession_id)
        description = source.get("description", title)
        licence = source.get("licence", "Unknown")
        release_date = self._parse_date(source.get("release_date"))

        # Parse nested data
        authors = self._parse_authors(source.get("author", []) or [])
        funding = self._parse_funding(source.get("grant", []) or [])
        publications = self._parse_publications(source.get("related_publication", []) or [])
        keywords = source.get("keyword", []) or []

        # Extract from datasets
        datasets = source.get("dataset", []) or []
        organisms = self._extract_organisms(datasets)
        imaging_methods = self._extract_imaging_methods(datasets)
        sample_type = self._extract_sample_type(datasets)
        file_count, total_size = self._extract_file_stats(datasets)

        # Get DOI
        data_doi = source.get("doi")

        return Study(
            id=f"bia:{accession_id}",
            source=Source.BIA,
            source_url=f"https://www.ebi.ac.uk/biostudies/bioimages/studies/{accession_id}",
            title=title,
            description=description,
            license=licence,
            release_date=release_date,
            biosample=BioSample(
                organism=organisms,
                sample_type=sample_type,
            ),
            image_acquisition=ImageAcquisition(
                methods=imaging_methods,
            ),
            authors=authors,
            publications=publications,
            funding=funding,
            keywords=keywords,
            data_doi=data_doi,
            file_count=file_count,
            total_size_bytes=total_size,
        )

    def fetch_studies(self, query: str = "", page_size: int | None = None) -> list[dict]:
        """Fetch studies from BIA API."""
        size = page_size or self.page_size
        params = {
            "query": query,
            "pagination.page_size": size,
        }

        response = httpx.get(BIA_API_URL, params=params, timeout=30.0)
        response.raise_for_status()

        data = response.json()
        return data.get("hits", {}).get("hits", [])

    def transform_all(self, query: str = "", page_size: int | None = None) -> list[Study]:
        """Fetch and transform studies from BIA API."""
        hits = self.fetch_studies(query, page_size)
        studies = []

        for hit in hits:
            study = self.transform_hit(hit)
            if study:
                studies.append(study)

        return studies
