"""Tests for ROCrateTransformer."""

import json
import tempfile
from datetime import date
from pathlib import Path

import pytest

from gide_search.schema import Source
from gide_search.transformers.rocrate import ROCrateTransformer


# Minimal RO-Crate with Schema.org vocabulary
MINIMAL_CRATE = {
    "@context": "https://w3id.org/ro/crate/1.1/context",
    "@graph": [
        {
            "@type": "CreativeWork",
            "@id": "ro-crate-metadata.json",
            "conformsTo": {"@id": "https://w3id.org/ro/crate/1.1"},
            "about": {"@id": "./"},
        },
        {
            "@id": "./",
            "@type": "Dataset",
            "identifier": "idr0164",
            "name": "Study Title",
            "description": "Study description here",
            "datePublished": "2024-01-15",
            "license": "https://creativecommons.org/licenses/by/4.0/",
            "url": "https://idr.openmicroscopy.org/study/idr0164/",
            "publisher": {"@id": "#idr"},
            "author": [{"@id": "#author1"}],
            "about": [{"@id": "#organism1"}],
            "measurementTechnique": [{"@id": "#method1"}],
        },
        {
            "@id": "#idr",
            "@type": "Organization",
            "name": "IDR",
            "url": "https://idr.openmicroscopy.org/",
        },
        {
            "@id": "#author1",
            "@type": "Person",
            "name": "Jane Researcher",
            "identifier": "https://orcid.org/0000-0002-1234-5678",
        },
        {
            "@id": "#organism1",
            "@type": "BioSample",
            "name": "Mus musculus",
            "url": "http://purl.obolibrary.org/obo/NCBITaxon_10090",
        },
        {
            "@id": "#method1",
            "@type": "DefinedTerm",
            "name": "confocal microscopy",
            "url": "http://purl.obolibrary.org/obo/FBbi_00000251",
        },
    ],
}


# BIA-style RO-Crate with bia: namespace
BIA_CRATE = {
    "@context": [
        "https://w3id.org/ro/crate/1.1/context",
        {
            "bia": "http://bia/",
            "displayName": {"@id": "schema:name"},
            "contactEmail": {"@id": "schema:email"},
            "affiliation": {"@id": "schema:memberOf"},
            "contributor": {"@id": "schema:author"},
            "licence": {"@id": "schema:license"},
            "accessionId": {"@id": "schema:identifier"},
            "keyword": {"@id": "schema:keywords"},
            "biologicalEntityDescription": {"@id": "bia:biologicalEntityDescription"},
            "organismClassification": {"@id": "bia:organismClassification"},
            "imagingMethodName": {"@id": "bia:imagingMethodName"},
            "fbbiId": {"@id": "bia:fbbiId"},
            "imagingInstrumentDescription": {"@id": "bia:imagingInstrumentDescription"},
            "commonName": {"@id": "bia:commonName"},
            "scientificName": {"@id": "bia:scientificName"},
        },
    ],
    "@graph": [
        {
            "@id": "ro-crate-metadata.json",
            "@type": "CreativeWork",
            "conformsTo": {"@id": "https://w3id.org/ro/crate/1.1"},
            "about": {"@id": "./"},
        },
        {
            "@id": "./",
            "@type": ["Dataset", "bia:Study"],
            "title": "BIA Study Title",
            "description": "BIA Study description",
            "licence": "https://creativecommons.org/publicdomain/zero/1.0/",
            "datePublished": "2023-11-13",
            "keyword": ["cryo-ET", "tomography"],
            "accessionId": "S-BIAD1234",
            "contributor": [{"@id": "_:c0"}, {"@id": "https://orcid.org/0000-0003-1234-5678"}],
            "hasPart": [{"@id": "dataset/"}],
        },
        {
            "@id": "_:c0",
            "@type": ["Person", "bia:Contributor"],
            "displayName": "Smith J",
            "contactEmail": "smith@example.org",
            "affiliation": [{"@id": "#org1"}],
        },
        {
            "@id": "https://orcid.org/0000-0003-1234-5678",
            "@type": ["Person", "bia:Contributor"],
            "displayName": "Johnson A",
        },
        {
            "@id": "#org1",
            "@type": "Organization",
            "name": "Research Institute",
            "url": "https://example.org",
        },
        {
            "@id": "dataset/",
            "@type": ["Dataset", "bia:Dataset"],
            "title": "Dataset 1",
            "associatedBiologicalEntity": [{"@id": "_:bio1"}],
            "associatedImageAcquisitionProtocol": [{"@id": "_:iap1"}],
        },
        {
            "@id": "_:bio1",
            "@type": ["bia:BioSample"],
            "title": "Human HeLa cells",
            "biologicalEntityDescription": "HeLa cell culture for imaging",
            "organismClassification": [{"@id": "NCBI:txid9606"}],
        },
        {
            "@id": "NCBI:txid9606",
            "@type": ["bia:Taxon"],
            "scientificName": "Homo sapiens",
            "commonName": "human",
        },
        {
            "@id": "_:iap1",
            "@type": ["bia:ImageAcquisitionProtocol"],
            "title": "Fluorescence Imaging",
            "protocolDescription": "Wide-field fluorescence microscopy protocol",
            "imagingInstrumentDescription": "Zeiss AxioObserver",
            "imagingMethodName": ["fluorescence microscopy"],
            "fbbiId": ["obo:FBbi_00000246"],
        },
    ],
}


@pytest.fixture
def minimal_crate_file(tmp_path: Path) -> Path:
    """Create a temporary minimal RO-Crate file."""
    crate_path = tmp_path / "ro-crate-metadata.json"
    with open(crate_path, "w") as f:
        json.dump(MINIMAL_CRATE, f)
    return crate_path


@pytest.fixture
def bia_crate_file(tmp_path: Path) -> Path:
    """Create a temporary BIA-style RO-Crate file."""
    crate_path = tmp_path / "ro-crate-metadata.json"
    with open(crate_path, "w") as f:
        json.dump(BIA_CRATE, f)
    return crate_path


@pytest.fixture
def crate_directory(tmp_path: Path) -> Path:
    """Create a directory with multiple RO-Crate files."""
    # Create two subdirectories with crates
    dir1 = tmp_path / "study1"
    dir1.mkdir()
    with open(dir1 / "ro-crate-metadata.json", "w") as f:
        json.dump(MINIMAL_CRATE, f)

    dir2 = tmp_path / "study2"
    dir2.mkdir()
    with open(dir2 / "ro-crate-metadata.json", "w") as f:
        json.dump(BIA_CRATE, f)

    return tmp_path


class TestROCrateTransformer:
    """Tests for ROCrateTransformer class."""

    def test_transform_minimal_crate(self, minimal_crate_file: Path):
        """Test transformation of minimal Schema.org style RO-Crate."""
        transformer = ROCrateTransformer(minimal_crate_file)
        studies = transformer.transform_all()

        assert len(studies) == 1
        study = studies[0]

        assert study.id == "idr:idr0164"
        assert study.source == Source.IDR
        assert study.title == "Study Title"
        assert study.description == "Study description here"
        assert study.license == "https://creativecommons.org/licenses/by/4.0/"
        assert study.release_date == date(2024, 1, 15)
        assert study.source_url == "https://idr.openmicroscopy.org/study/idr0164/"

    def test_transform_bia_crate(self, bia_crate_file: Path):
        """Test transformation of BIA-style RO-Crate with bia: namespace."""
        transformer = ROCrateTransformer(bia_crate_file)
        studies = transformer.transform_all()

        assert len(studies) == 1
        study = studies[0]

        assert study.id == "bia:S-BIAD1234"
        assert study.source == Source.BIA
        assert study.title == "BIA Study Title"
        assert study.license == "https://creativecommons.org/publicdomain/zero/1.0/"
        assert study.keywords == ["cryo-ET", "tomography"]

    def test_extract_authors_bia_style(self, bia_crate_file: Path):
        """Test author extraction from BIA-style contributors."""
        transformer = ROCrateTransformer(bia_crate_file)
        studies = transformer.transform_all()
        study = studies[0]

        assert len(study.authors) == 2

        # First author has email and affiliation
        author1 = study.authors[0]
        assert author1.name == "Smith J"
        assert author1.email == "smith@example.org"
        assert len(author1.affiliations) == 1
        assert author1.affiliations[0].display_name == "Research Institute"

        # Second author has ORCID in @id
        author2 = study.authors[1]
        assert author2.name == "Johnson A"
        assert author2.orcid == "https://orcid.org/0000-0003-1234-5678"

    def test_extract_organisms_bia_style(self, bia_crate_file: Path):
        """Test organism extraction from BIA BioSample entities."""
        transformer = ROCrateTransformer(bia_crate_file)
        studies = transformer.transform_all()
        study = studies[0]

        assert len(study.biosamples) == 1
        biosample = study.biosamples[0]

        assert len(biosample.organism) == 1
        organism = biosample.organism[0]
        assert organism.scientific_name == "Homo sapiens"
        assert organism.common_name == "human"
        assert organism.ncbi_taxon_id == 9606

        assert biosample.biological_entity_description == "HeLa cell culture for imaging"

    def test_extract_imaging_methods_bia_style(self, bia_crate_file: Path):
        """Test imaging method extraction from BIA ImageAcquisitionProtocol."""
        transformer = ROCrateTransformer(bia_crate_file)
        studies = transformer.transform_all()
        study = studies[0]

        assert len(study.image_acquisition_protocols) == 1
        protocol = study.image_acquisition_protocols[0]

        assert len(protocol.methods) == 1
        method = protocol.methods[0]
        assert method.name == "fluorescence microscopy"
        assert method.fbbi_id == "FBbi:00000246"

        assert protocol.protocol_description == "Wide-field fluorescence microscopy protocol"
        assert protocol.imaging_instrument_description == "Zeiss AxioObserver"

    def test_transform_directory(self, crate_directory: Path):
        """Test transforming multiple crates from a directory."""
        transformer = ROCrateTransformer(crate_directory)
        studies = transformer.transform_all()

        assert len(studies) == 2
        sources = {s.source for s in studies}
        assert Source.IDR in sources
        assert Source.BIA in sources

    def test_source_detection_from_accession_id(self, tmp_path: Path):
        """Test source detection from accession ID patterns."""
        transformer = ROCrateTransformer(tmp_path)

        # Test patterns
        test_cases = [
            ("IDR0001", Source.IDR),
            ("idr0164", Source.IDR),
            ("S-BIAD123", Source.BIA),
            ("EMPIAR-11756", Source.BIA),
            ("SSBD-123", Source.SSBD),
            ("unknown-id", Source.EXTERNAL),
        ]

        for accession, expected_source in test_cases:
            root = {"accessionId": accession}
            source = transformer._extract_source(root, {})
            assert source == expected_source, f"Failed for {accession}"


class TestNCBITaxonExtraction:
    """Tests for NCBI Taxon ID extraction."""

    def test_extract_obo_url(self):
        """Test extraction from OBO Foundry URL."""
        transformer = ROCrateTransformer(".")
        result = transformer._extract_ncbi_taxon_id(
            "http://purl.obolibrary.org/obo/NCBITaxon_9606"
        )
        assert result == 9606

    def test_extract_ncbi_txid(self):
        """Test extraction from NCBI:txid format."""
        transformer = ROCrateTransformer(".")
        result = transformer._extract_ncbi_taxon_id("NCBI:txid3055")
        assert result == 3055

    def test_extract_ncbi_taxon_colon(self):
        """Test extraction from NCBITaxon:ID format."""
        transformer = ROCrateTransformer(".")
        result = transformer._extract_ncbi_taxon_id("NCBITaxon:10090")
        assert result == 10090

    def test_extract_none(self):
        """Test None input returns None."""
        transformer = ROCrateTransformer(".")
        assert transformer._extract_ncbi_taxon_id(None) is None

    def test_extract_invalid(self):
        """Test invalid input returns None."""
        transformer = ROCrateTransformer(".")
        assert transformer._extract_ncbi_taxon_id("not-a-taxon-id") is None


class TestFBbiExtraction:
    """Tests for FBbi ontology ID extraction."""

    def test_extract_obo_url(self):
        """Test extraction from OBO Foundry URL."""
        transformer = ROCrateTransformer(".")
        result = transformer._extract_fbbi_id(
            "http://purl.obolibrary.org/obo/FBbi_00000246"
        )
        assert result == "FBbi:00000246"

    def test_extract_obo_prefix(self):
        """Test extraction from obo: prefix format."""
        transformer = ROCrateTransformer(".")
        result = transformer._extract_fbbi_id("obo:FBbi_00000256")
        assert result == "FBbi:00000256"

    def test_extract_direct(self):
        """Test extraction from direct FBbi format."""
        transformer = ROCrateTransformer(".")
        result = transformer._extract_fbbi_id("FBbi_00000251")
        assert result == "FBbi:00000251"

    def test_extract_colon_format(self):
        """Test extraction from FBbi:ID format."""
        transformer = ROCrateTransformer(".")
        result = transformer._extract_fbbi_id("FBbi:00000300")
        assert result == "FBbi:00000300"

    def test_extract_none(self):
        """Test None input returns None."""
        transformer = ROCrateTransformer(".")
        assert transformer._extract_fbbi_id(None) is None


class TestRealWorldCrate:
    """Tests using real BIA EMPIAR example if available."""

    @pytest.fixture
    def empiar_crate(self) -> Path | None:
        """Return path to real EMPIAR crate if it exists."""
        path = Path("resources/rocrate/empiar-11756/ro-crate-metadata.json")
        if path.exists():
            return path
        return None

    def test_transform_empiar_example(self, empiar_crate: Path | None):
        """Test transformation of real EMPIAR-11756 RO-Crate."""
        if empiar_crate is None:
            pytest.skip("EMPIAR example not available")

        transformer = ROCrateTransformer(empiar_crate)
        studies = transformer.transform_all()

        assert len(studies) == 1
        study = studies[0]

        # Verify key fields
        assert study.id == "bia:EMPIAR-11756"
        assert study.source == Source.BIA
        assert "cryo-ET" in study.title.lower() or "chlamydomonas" in study.title.lower()

        # Verify organism extraction
        assert len(study.biosamples) == 1
        organisms = study.biosamples[0].organism
        assert len(organisms) >= 1
        assert organisms[0].ncbi_taxon_id == 3055  # Chlamydomonas reinhardtii

        # Verify imaging method
        assert len(study.image_acquisition_protocols) == 1
        methods = study.image_acquisition_protocols[0].methods
        assert len(methods) >= 1
        assert methods[0].fbbi_id == "FBbi:00000256"

        # Verify authors
        assert len(study.authors) > 0
