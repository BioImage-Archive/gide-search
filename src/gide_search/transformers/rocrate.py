"""RO-Crate metadata to unified schema transformer."""

import json
import re
from datetime import date
from pathlib import Path

from ..schema import (
    Author,
    BioSample,
    Funding,
    ImageAcquisitionProtocol,
    ImagingDatasetSummary,
    ImagingMethod,
    Organisation,
    Organism,
    Publication,
    Source,
)


class ROCrateTransformer:
    """Transform RO-Crate metadata files to unified ImagingDatasetSummary schema.

    Supports both standard Schema.org vocabulary and BIA profile extensions.
    """

    # Known publisher patterns for source identification
    SOURCE_PATTERNS = {
        Source.IDR: ["idr", "image data resource", "openmicroscopy"],
        Source.SSBD: ["ssbd", "riken"],
        Source.BIA: ["bia", "bioimage archive", "empiar", "ebi"],
    }

    def __init__(self, path: Path | str):
        """Initialize with path to ro-crate-metadata.json or directory."""
        self.path = Path(path)

    def transform_all(self) -> list[ImagingDatasetSummary]:
        """Transform all RO-Crate files found at the path."""
        if self.path.is_file():
            return [self.transform_crate(self.path)]
        else:
            crates = list(self.path.rglob("ro-crate-metadata.json"))
            return [self.transform_crate(p) for p in crates]

    def transform_crate(self, path: Path) -> ImagingDatasetSummary:
        """Transform a single RO-Crate file to ImagingDatasetSummary."""
        with open(path) as f:
            data = json.load(f)

        graph = data.get("@graph", [])
        entity_map = self._build_entity_map(graph)
        root = self._find_root_dataset(graph)

        if not root:
            raise ValueError(f"No root Dataset found in {path}")

        # Determine source from publisher or accession ID
        source = self._extract_source(root, entity_map)

        # Extract ID (accession ID or dataset identifier)
        accession_id = self._extract_id(root)
        study_id = f"{source.value.lower()}:{accession_id}"

        # Extract URL
        source_url = self._extract_source_url(root, source, accession_id)

        # Core metadata
        title = root.get("title") or root.get("name") or accession_id
        description = root.get("description") or title
        license_val = root.get("licence") or root.get("license") or "Unknown"
        release_date = self._parse_date(root.get("datePublished"))

        # Extract structured data
        authors = self._extract_authors(root, entity_map)
        organisms, sample_type, bio_desc = self._extract_biosample_info(root, entity_map)
        imaging_methods, protocol_desc, instrument_desc = self._extract_imaging_info(root, entity_map)
        publications = self._extract_publications(root, entity_map)
        funding = self._extract_funding(root, entity_map)
        keywords = self._extract_keywords(root)

        # Data DOI
        data_doi = root.get("identifier") if root.get("identifier", "").startswith("10.") else None

        return ImagingDatasetSummary(
            id=study_id,
            source=source,
            source_url=source_url,
            title=title,
            description=description,
            license=license_val,
            release_date=release_date,
            biosamples=[
                BioSample(
                    organism=organisms,
                    sample_type=sample_type,
                    biological_entity_description=bio_desc,
                )
            ],
            image_acquisition_protocols=[
                ImageAcquisitionProtocol(
                    methods=imaging_methods,
                    protocol_description=protocol_desc,
                    imaging_instrument_description=instrument_desc,
                )
            ],
            authors=authors,
            publications=publications,
            funding=funding,
            keywords=keywords,
            data_doi=data_doi,
        )

    def _build_entity_map(self, graph: list[dict]) -> dict[str, dict]:
        """Build a map of @id -> entity for quick lookups."""
        return {entity.get("@id"): entity for entity in graph if "@id" in entity}

    def _find_root_dataset(self, graph: list[dict]) -> dict | None:
        """Find the root Dataset entity in the graph."""
        for entity in graph:
            entity_id = entity.get("@id", "")
            entity_types = entity.get("@type", [])
            if isinstance(entity_types, str):
                entity_types = [entity_types]

            # Root dataset is "./" or the one referenced by ro-crate-metadata.json
            if entity_id == "./" and ("Dataset" in entity_types or "bia:Study" in entity_types):
                return entity

        # Fallback: find the dataset referenced by the metadata descriptor
        for entity in graph:
            if entity.get("@id") == "ro-crate-metadata.json":
                about = entity.get("about", {})
                about_id = about.get("@id") if isinstance(about, dict) else about
                for e in graph:
                    if e.get("@id") == about_id:
                        return e
        return None

    def _resolve_entity(self, ref: dict | str | None, entity_map: dict[str, dict]) -> dict | None:
        """Resolve an @id reference to its entity."""
        if ref is None:
            return None
        ref_id = ref.get("@id") if isinstance(ref, dict) else ref
        return entity_map.get(ref_id)

    def _resolve_entities(self, refs: list | None, entity_map: dict[str, dict]) -> list[dict]:
        """Resolve a list of @id references to entities."""
        if not refs:
            return []
        entities = []
        for ref in refs:
            entity = self._resolve_entity(ref, entity_map)
            if entity:
                entities.append(entity)
        return entities

    def _extract_source(self, root: dict, entity_map: dict[str, dict]) -> Source:
        """Determine the data source from publisher or accession ID."""
        # Check publisher
        publisher_ref = root.get("publisher")
        if publisher_ref:
            publisher = self._resolve_entity(publisher_ref, entity_map)
            if publisher:
                publisher_name = (publisher.get("name") or publisher.get("@id") or "").lower()
                publisher_url = (publisher.get("url") or publisher.get("@id") or "").lower()
                text = publisher_name + " " + publisher_url

                for source, patterns in self.SOURCE_PATTERNS.items():
                    if any(p in text for p in patterns):
                        return source

        # Check accession ID patterns
        accession_id = self._extract_id(root).upper()
        if accession_id.startswith("IDR"):
            return Source.IDR
        if accession_id.startswith("SSBD"):
            return Source.SSBD
        if accession_id.startswith(("S-BIAD", "EMPIAR")):
            return Source.BIA

        return Source.EXTERNAL

    def _extract_id(self, root: dict) -> str:
        """Extract identifier from root dataset."""
        # Try accessionId (BIA style), then identifier, then @id
        accession = root.get("accessionId") or root.get("identifier")
        if accession:
            return str(accession)

        # Fall back to URL-based extraction
        url = root.get("url", "")
        if url:
            parts = url.rstrip("/").split("/")
            return parts[-1] if parts else "unknown"

        return "unknown"

    def _extract_source_url(self, root: dict, source: Source, accession_id: str) -> str:
        """Extract or construct the source URL."""
        if root.get("url"):
            return root["url"]

        # Construct URL based on source and accession ID
        if source == Source.IDR:
            return f"https://idr.openmicroscopy.org/study/{accession_id}/"
        elif source == Source.SSBD:
            return f"https://ssbd.riken.jp/repository/{accession_id}/"
        elif source == Source.BIA:
            if accession_id.startswith("EMPIAR"):
                return f"https://www.ebi.ac.uk/empiar/{accession_id}/"
            return f"https://www.ebi.ac.uk/biostudies/bioimages/studies/{accession_id}"
        else:
            return f"https://example.org/study/{accession_id}"

    def _parse_date(self, date_str: str | None) -> date:
        """Parse ISO date string to date object."""
        if not date_str:
            return date(2024, 1, 1)
        try:
            parts = date_str.split("-")
            return date(int(parts[0]), int(parts[1]), int(parts[2]))
        except (ValueError, IndexError):
            return date(2024, 1, 1)

    def _extract_authors(self, root: dict, entity_map: dict[str, dict]) -> list[Author]:
        """Extract authors from contributor/author references."""
        authors = []
        # Try 'contributor' (BIA style) then 'author' (Schema.org style)
        author_refs = root.get("contributor") or root.get("author") or []

        for ref in author_refs:
            person = self._resolve_entity(ref, entity_map)
            if not person:
                continue

            name = person.get("displayName") or person.get("name") or "Unknown"
            orcid = self._extract_orcid(person)
            email = person.get("contactEmail") or person.get("email")
            affiliations = self._extract_affiliations(person, entity_map)

            authors.append(
                Author(
                    name=name,
                    orcid=orcid,
                    email=email,
                    affiliations=affiliations,
                )
            )

        return authors

    def _extract_orcid(self, person: dict) -> str | None:
        """Extract ORCID from person entity."""
        # Check @id for ORCID URL
        person_id = person.get("@id", "")
        if "orcid.org" in person_id:
            return person_id

        # Check identifier field
        identifier = person.get("identifier")
        if identifier and "orcid" in str(identifier).lower():
            return identifier

        return None

    def _extract_affiliations(self, person: dict, entity_map: dict[str, dict]) -> list[Organisation]:
        """Extract affiliations from person entity."""
        affiliations = []
        aff_refs = person.get("affiliation") or person.get("memberOf") or []

        if isinstance(aff_refs, dict):
            aff_refs = [aff_refs]

        for ref in aff_refs:
            org = self._resolve_entity(ref, entity_map)
            if not org:
                continue

            affiliations.append(
                Organisation(
                    display_name=org.get("name") or org.get("displayName") or "Unknown",
                    rorid=org.get("identifier") if "ror.org" in str(org.get("identifier", "")) else None,
                    address=org.get("address"),
                    website=org.get("url") or org.get("website"),
                )
            )

        return affiliations

    def _extract_biosample_info(
        self, root: dict, entity_map: dict[str, dict]
    ) -> tuple[list[Organism], str, str | None]:
        """Extract organisms, sample type, and biological entity description."""
        organisms = []
        bio_desc = None
        seen_organisms = set()

        # Find BioSamples - look in hasPart for nested datasets, then their associations
        parts = root.get("hasPart") or []
        for part_ref in parts:
            part = self._resolve_entity(part_ref, entity_map)
            if not part:
                continue

            # Check for associatedBiologicalEntity in nested datasets
            bio_entity_refs = part.get("associatedBiologicalEntity") or []
            for be_ref in bio_entity_refs:
                be = self._resolve_entity(be_ref, entity_map)
                if be:
                    self._extract_organisms_from_biosample(be, entity_map, organisms, seen_organisms)
                    if not bio_desc:
                        bio_desc = be.get("biologicalEntityDescription")

        # Also check direct 'about' or 'subject' for BioSamples
        about_refs = root.get("about") or []
        if isinstance(about_refs, dict):
            about_refs = [about_refs]
        for ref in about_refs:
            entity = self._resolve_entity(ref, entity_map)
            if entity and self._is_biosample(entity):
                self._extract_organisms_from_biosample(entity, entity_map, organisms, seen_organisms)
                if not bio_desc:
                    bio_desc = entity.get("biologicalEntityDescription")

        # Infer sample type from description
        sample_type = self._infer_sample_type(bio_desc)

        if not organisms:
            organisms = [Organism(scientific_name="Unknown")]

        return organisms, sample_type, bio_desc

    def _is_biosample(self, entity: dict) -> bool:
        """Check if entity is a BioSample type."""
        entity_types = entity.get("@type", [])
        if isinstance(entity_types, str):
            entity_types = [entity_types]
        return any("BioSample" in t for t in entity_types)

    def _extract_organisms_from_biosample(
        self,
        biosample: dict,
        entity_map: dict[str, dict],
        organisms: list[Organism],
        seen: set,
    ) -> None:
        """Extract organisms from a BioSample entity."""
        # Get organism classification references
        org_refs = biosample.get("organismClassification") or []
        if isinstance(org_refs, dict):
            org_refs = [org_refs]

        for ref in org_refs:
            taxon = self._resolve_entity(ref, entity_map)
            if not taxon:
                # Try extracting from reference ID directly
                ref_id = ref.get("@id") if isinstance(ref, dict) else ref
                ncbi_id = self._extract_ncbi_taxon_id(ref_id)
                if ncbi_id and ref_id not in seen:
                    seen.add(ref_id)
                    organisms.append(
                        Organism(
                            scientific_name=ref_id.split(":")[-1] if ":" in ref_id else ref_id,
                            ncbi_taxon_id=ncbi_id,
                        )
                    )
                continue

            scientific_name = taxon.get("scientificName") or taxon.get("name") or "Unknown"
            common_name = taxon.get("commonName")

            if scientific_name in seen:
                continue
            seen.add(scientific_name)

            # Extract NCBI Taxon ID from @id
            ncbi_id = self._extract_ncbi_taxon_id(taxon.get("@id"))

            organisms.append(
                Organism(
                    scientific_name=scientific_name,
                    common_name=common_name,
                    ncbi_taxon_id=ncbi_id,
                )
            )

    def _extract_ncbi_taxon_id(self, url_or_id: str | None) -> int | None:
        """Extract NCBI Taxonomy ID from URL or identifier."""
        if not url_or_id:
            return None

        # Match patterns like:
        # - http://purl.obolibrary.org/obo/NCBITaxon_9606
        # - NCBI:txid3055
        # - NCBITaxon:9606
        patterns = [
            r"NCBITaxon[_:](\d+)",
            r"NCBI:txid(\d+)",
            r"ncbitaxon/(\d+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, url_or_id, re.IGNORECASE)
            if match:
                return int(match.group(1))

        return None

    def _infer_sample_type(self, description: str | None) -> str:
        """Infer sample type from description."""
        if not description:
            return "unknown"

        text = description.lower()
        if "tissue" in text:
            return "tissue"
        if "cell line" in text or "cell culture" in text:
            return "cell"
        if "organism" in text or "whole" in text:
            return "organism"
        if "cell" in text:
            return "cell"
        return "unknown"

    def _extract_imaging_info(
        self, root: dict, entity_map: dict[str, dict]
    ) -> tuple[list[ImagingMethod], str | None, str | None]:
        """Extract imaging methods, protocol description, and instrument description."""
        methods = []
        protocol_desc = None
        instrument_desc = None
        seen_methods = set()

        # Look for ImageAcquisitionProtocol in nested datasets
        parts = root.get("hasPart") or []
        for part_ref in parts:
            part = self._resolve_entity(part_ref, entity_map)
            if not part:
                continue

            protocol_refs = part.get("associatedImageAcquisitionProtocol") or []
            for proto_ref in protocol_refs:
                proto = self._resolve_entity(proto_ref, entity_map)
                if not proto:
                    continue

                self._extract_methods_from_protocol(proto, methods, seen_methods)
                if not protocol_desc:
                    protocol_desc = proto.get("protocolDescription")
                if not instrument_desc:
                    instrument_desc = proto.get("imagingInstrumentDescription")

        # Also check measurementTechnique (Schema.org style)
        technique_refs = root.get("measurementTechnique") or []
        if isinstance(technique_refs, dict):
            technique_refs = [technique_refs]
        for ref in technique_refs:
            entity = self._resolve_entity(ref, entity_map)
            if entity:
                # Check for BIA-style properties first
                if entity.get("imagingMethodName") or entity.get("fbbiId"):
                    self._extract_methods_from_protocol(entity, methods, seen_methods)
                    if not protocol_desc:
                        protocol_desc = entity.get("protocolDescription") or entity.get("description")
                    if not instrument_desc:
                        instrument_desc = entity.get("imagingInstrumentDescription")
                else:
                    # Fall back to Schema.org style
                    name = entity.get("name")
                    url = entity.get("url") or entity.get("@id")
                    if name and name not in seen_methods:
                        seen_methods.add(name)
                        fbbi_id = self._extract_fbbi_id(url)
                        methods.append(ImagingMethod(name=name, fbbi_id=fbbi_id))

        if not methods:
            methods = [ImagingMethod(name="Unknown")]

        return methods, protocol_desc, instrument_desc

    def _extract_methods_from_protocol(
        self, protocol: dict, methods: list[ImagingMethod], seen: set
    ) -> None:
        """Extract imaging methods from an ImageAcquisitionProtocol entity."""
        method_names = protocol.get("imagingMethodName") or []
        fbbi_ids = protocol.get("fbbiId") or []

        if isinstance(method_names, str):
            method_names = [method_names]
        if isinstance(fbbi_ids, str):
            fbbi_ids = [fbbi_ids]

        for i, name in enumerate(method_names):
            if not name or name in seen:
                continue
            seen.add(name)

            fbbi_id = fbbi_ids[i] if i < len(fbbi_ids) else None
            fbbi_id = self._extract_fbbi_id(fbbi_id)

            methods.append(ImagingMethod(name=name, fbbi_id=fbbi_id))

    def _extract_fbbi_id(self, url_or_id: str | None) -> str | None:
        """Extract FBbi ontology ID from URL or identifier."""
        if not url_or_id:
            return None

        # Match patterns like:
        # - http://purl.obolibrary.org/obo/FBbi_00000246
        # - obo:FBbi_00000256
        # - FBbi_00000256
        # - FBbi:00000256
        patterns = [
            r"FBbi[_:](\d+)",
            r"fbbi[_:](\d+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, url_or_id, re.IGNORECASE)
            if match:
                return f"FBbi:{match.group(1)}"

        return None

    def _extract_publications(self, root: dict, entity_map: dict[str, dict]) -> list[Publication]:
        """Extract publications from citation/relatedPublication references."""
        publications = []

        # Try 'citation' (Schema.org) then 'relatedPublication' (BIA style)
        pub_refs = root.get("citation") or root.get("relatedPublication") or []
        if isinstance(pub_refs, dict):
            pub_refs = [pub_refs]

        for ref in pub_refs:
            pub = self._resolve_entity(ref, entity_map)
            if not pub:
                continue

            doi = pub.get("doi") or pub.get("identifier")
            if doi and not doi.startswith("10."):
                doi = None

            publications.append(
                Publication(
                    doi=doi,
                    pubmed_id=pub.get("pubmed_id") or pub.get("pmid"),
                    pmc_id=pub.get("pmc_id") or pub.get("pmcid"),
                    title=pub.get("name") or pub.get("title"),
                    authors_name=pub.get("authorNames"),
                    year=self._extract_year(pub.get("datePublished")),
                )
            )

        return publications

    def _extract_year(self, date_str: str | None) -> int | None:
        """Extract year from date string."""
        if not date_str:
            return None
        try:
            return int(date_str.split("-")[0])
        except (ValueError, IndexError):
            return None

    def _extract_funding(self, root: dict, entity_map: dict[str, dict]) -> list[Funding]:
        """Extract funding information from funder references."""
        funding = []

        funder_refs = root.get("funder") or root.get("grant") or []
        if isinstance(funder_refs, dict):
            funder_refs = [funder_refs]

        for ref in funder_refs:
            grant = self._resolve_entity(ref, entity_map)
            if not grant:
                continue

            funder_name = grant.get("name") or "Unknown"
            grant_id = grant.get("identifier") or grant.get("@id", "").split("/")[-1]

            if funder_name and grant_id:
                funding.append(Funding(funder=funder_name, grant_id=grant_id))

        return funding

    def _extract_keywords(self, root: dict) -> list[str]:
        """Extract keywords from root dataset."""
        keywords = root.get("keyword") or root.get("keywords") or []
        if isinstance(keywords, str):
            return [k.strip() for k in keywords.split(",")]
        return [str(k) for k in keywords if k]
