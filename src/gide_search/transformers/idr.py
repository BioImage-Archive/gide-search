"""IDR metadata to unified schema transformer."""

import csv
import re
from datetime import date
from pathlib import Path

from ..schema import (
    Author,
    BioSample,
    ImageAcquisitionProtocol,
    ImagingMethod,
    Organism,
    Publication,
    Source,
    Study,
)


class IDRTransformer:
    """Transform IDR study metadata files to unified Study schema."""

    def __init__(self, idr_repo_path: Path | str):
        self.repo_path = Path(idr_repo_path)

    def _parse_study_file(self, study_file: Path) -> dict[str, str | list[str]]:
        """Parse an IDR study.txt file into a dictionary."""
        data: dict[str, str | list[str]] = {}

        with open(study_file, encoding="utf-8") as f:
            reader = csv.reader(f, delimiter="\t")
            for row in reader:
                if not row or row[0].startswith("#") or row[0].startswith('"#'):
                    continue

                key = row[0].strip()
                if not key:
                    continue

                # Get non-empty values
                values = [v.strip() for v in row[1:] if v.strip()]

                if not values:
                    continue

                # Some fields can have multiple values (e.g., Study PubMed ID)
                if key in data:
                    existing = data[key]
                    if isinstance(existing, list):
                        existing.extend(values)
                    else:
                        data[key] = [existing] + values
                else:
                    data[key] = values[0] if len(values) == 1 else values

        return data

    def _extract_ncbi_taxon_id(self, accession: str) -> int | None:
        """Extract NCBI Taxon ID from accession like NCBITaxon_4896."""
        if not accession:
            return None
        match = re.search(r"NCBITaxon_(\d+)", accession)
        if match:
            return int(match.group(1))
        return None

    def _extract_fbbi_id(self, accession: str) -> str | None:
        """Extract FBbi ID from accession like FBbi_00000253."""
        if not accession:
            return None
        match = re.search(r"FBbi_(\d+)", accession)
        if match:
            return f"FBbi:{match.group(1)}"
        return None

    def _parse_date(self, date_str: str) -> date:
        """Parse date from string like 2016-04-27."""
        if not date_str:
            return date(2016, 1, 1)  # Default fallback
        try:
            parts = date_str.split("-")
            return date(int(parts[0]), int(parts[1]), int(parts[2]))
        except (ValueError, IndexError):
            return date(2016, 1, 1)

    def _parse_authors(self, author_list: str | list[str]) -> list[Author]:
        """Parse author list string into Author objects."""
        if not author_list:
            return []

        # Take first author list if multiple
        if isinstance(author_list, list):
            author_list = author_list[0]

        authors = []
        for name in author_list.split(","):
            name = name.strip()
            if name:
                authors.append(Author(name=name))
        return authors

    def _parse_publications(self, data: dict) -> list[Publication]:
        """Parse publication information from study data."""
        publications = []

        pmids = data.get("Study PubMed ID", [])
        dois = data.get("Study DOI", [])
        titles = data.get("Study Publication Title", [])

        # Normalize to lists
        if isinstance(pmids, str):
            pmids = [pmids]
        if isinstance(dois, str):
            dois = [dois]
        if isinstance(titles, str):
            titles = [titles]

        # Create publications from available data
        max_len = max(len(pmids), len(dois), len(titles), 1)
        for i in range(max_len):
            pub = Publication(
                pubmed_id=pmids[i] if i < len(pmids) else None,
                doi=dois[i] if i < len(dois) else None,
                title=titles[i] if i < len(titles) else None,
            )
            if pub.pubmed_id or pub.doi or pub.title:
                publications.append(pub)

        return publications

    def transform_study(self, study_file: Path) -> Study | None:
        """Transform a single IDR study file to a Study object."""
        data = self._parse_study_file(study_file)

        if not data:
            return None

        # Extract study ID
        study_id = data.get("Comment[IDR Study Accession]", "")
        if isinstance(study_id, list):
            study_id = study_id[0]
        if not study_id:
            # Try to extract from filename
            match = re.search(r"(idr\d+)", study_file.name)
            study_id = match.group(1) if match else study_file.stem

        # Extract organism info
        organism_name = data.get("Study Organism", "Unknown")
        if isinstance(organism_name, list):
            organism_name = organism_name[0]
        organism_accession = data.get("Study Organism Term Accession", "")
        if isinstance(organism_accession, list):
            organism_accession = organism_accession[0]
        ncbi_taxon_id = self._extract_ncbi_taxon_id(organism_accession)

        # Extract imaging method (from Screen section)
        imaging_method = data.get("Screen Imaging Method", "Unknown")
        if isinstance(imaging_method, list):
            imaging_method = imaging_method[0]
        imaging_accession = data.get("Screen Imaging Method Term Accession", "")
        if isinstance(imaging_accession, list):
            imaging_accession = imaging_accession[0]
        fbbi_id = self._extract_fbbi_id(imaging_accession)

        # Extract sample type
        sample_type = data.get("Screen Sample Type", "unknown")
        if isinstance(sample_type, list):
            sample_type = sample_type[0]

        # Extract title and description
        title = data.get("Study Title", study_id)
        if isinstance(title, list):
            title = title[0]
        description = data.get("Study Description", title)
        if isinstance(description, list):
            description = description[0]

        # Extract license
        license_str = data.get("Study License", "Unknown")
        if isinstance(license_str, list):
            license_str = license_str[0]

        # Extract release date
        release_date_str = data.get("Study Public Release Date", "")
        if isinstance(release_date_str, list):
            release_date_str = release_date_str[0]
        release_date = self._parse_date(release_date_str)

        # Extract authors
        author_list = data.get("Study Author List", "")
        authors = self._parse_authors(author_list)

        # Extract publications
        publications = self._parse_publications(data)

        return Study(
            id=f"idr:{study_id}",
            source=Source.IDR,
            source_url=f"https://idr.openmicroscopy.org/search/?query=Name:{study_id}",
            title=title,
            description=description,
            license=license_str,
            release_date=release_date,
            biosamples=[BioSample(
                organism=[Organism(scientific_name=organism_name, ncbi_taxon_id=ncbi_taxon_id)],
                sample_type=sample_type,
            )],
            image_acquisition_protocols=[ImageAcquisitionProtocol(
                methods=[ImagingMethod(name=imaging_method, fbbi_id=fbbi_id)],
            )],
            authors=authors,
            publications=publications,
        )

    def find_study_files(self) -> list[Path]:
        """Find all study.txt files in the IDR repo."""
        return list(self.repo_path.glob("idr*/*-study.txt"))

    def transform_all(self) -> list[Study]:
        """Transform all IDR studies to Study objects."""
        studies = []
        for study_file in self.find_study_files():
            study = self.transform_study(study_file)
            if study:
                studies.append(study)
        return studies
