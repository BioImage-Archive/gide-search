"""Tests for the SSBD transformer."""

from datetime import date
from pathlib import Path

import pytest
from rdflib import URIRef

from gide_search.schema import Source
from gide_search.transformers.ssbd import SSBDTransformer


class TestSSBDTransformer:
    """Test suite for SSBDTransformer."""

    def test_init_parses_ttl_file(self, sample_ssbd_ttl_file: Path):
        """Test that transformer initializes and parses TTL file."""
        transformer = SSBDTransformer(sample_ssbd_ttl_file)
        assert transformer.graph is not None
        assert len(transformer.graph) > 0

    def test_extract_ncbi_taxon_id_valid(self, sample_ssbd_ttl_file: Path):
        """Test NCBI Taxon ID extraction from valid URI."""
        transformer = SSBDTransformer(sample_ssbd_ttl_file)
        uri = URIRef("http://purl.obolibrary.org/obo/NCBITaxon_10090")
        result = transformer._extract_ncbi_taxon_id(uri)
        assert result == 10090

    def test_extract_ncbi_taxon_id_different_format(self, sample_ssbd_ttl_file: Path):
        """Test NCBI Taxon ID extraction from different URI formats."""
        transformer = SSBDTransformer(sample_ssbd_ttl_file)

        # Standard format
        uri = URIRef("http://purl.obolibrary.org/obo/NCBITaxon_9606")
        assert transformer._extract_ncbi_taxon_id(uri) == 9606

    def test_extract_ncbi_taxon_id_invalid(self, sample_ssbd_ttl_file: Path):
        """Test NCBI Taxon ID extraction returns None for invalid URI."""
        transformer = SSBDTransformer(sample_ssbd_ttl_file)
        uri = URIRef("http://example.org/invalid")
        result = transformer._extract_ncbi_taxon_id(uri)
        assert result is None

    def test_extract_fbbi_id_valid(self, sample_ssbd_ttl_file: Path):
        """Test FBbi ID extraction from valid URI."""
        transformer = SSBDTransformer(sample_ssbd_ttl_file)
        uri = URIRef("http://purl.obolibrary.org/obo/FBbi_00000246")
        result = transformer._extract_fbbi_id(uri)
        assert result == "FBbi:00000246"

    def test_extract_fbbi_id_invalid(self, sample_ssbd_ttl_file: Path):
        """Test FBbi ID extraction returns None for invalid URI."""
        transformer = SSBDTransformer(sample_ssbd_ttl_file)
        uri = URIRef("http://example.org/invalid")
        result = transformer._extract_fbbi_id(uri)
        assert result is None

    def test_transform_all_returns_datasets(self, sample_ssbd_ttl_file: Path):
        """Test that transform_all returns a list of ImagingDatasetSummary objects."""
        transformer = SSBDTransformer(sample_ssbd_ttl_file)
        studies = transformer.transform_all()

        assert isinstance(studies, list)
        assert len(studies) == 1

    def test_transform_dataset_creates_valid_dataset(self, sample_ssbd_ttl_file: Path):
        """Test that a dataset is transformed into a valid ImagingDatasetSummary object."""
        transformer = SSBDTransformer(sample_ssbd_ttl_file)
        studies = transformer.transform_all()

        assert len(studies) == 1
        study = studies[0]

        # Check core fields
        assert study.source == Source.SSBD
        assert study.id.startswith("ssbd:")
        assert "Test Dataset Title" in study.title
        assert study.license == "CC BY 4.0"

    def test_transform_dataset_extracts_organism(self, sample_ssbd_ttl_file: Path):
        """Test that organism info is correctly extracted."""
        transformer = SSBDTransformer(sample_ssbd_ttl_file)
        studies = transformer.transform_all()
        study = studies[0]

        assert len(study.biosamples) > 0
        assert len(study.biosamples[0].organism) > 0
        organism = study.biosamples[0].organism[0]
        assert organism.scientific_name == "Mus musculus"
        assert organism.ncbi_taxon_id == 10090

    def test_transform_dataset_extracts_imaging_method(self, sample_ssbd_ttl_file: Path):
        """Test that imaging method is correctly extracted."""
        transformer = SSBDTransformer(sample_ssbd_ttl_file)
        studies = transformer.transform_all()
        study = studies[0]

        assert len(study.image_acquisition_protocols) > 0
        assert len(study.image_acquisition_protocols[0].methods) > 0
        method = study.image_acquisition_protocols[0].methods[0]
        assert method.name == "confocal microscopy"
        assert method.fbbi_id == "FBbi:00000246"

    def test_transform_dataset_extracts_publications(self, sample_ssbd_ttl_file: Path):
        """Test that publication info is correctly extracted."""
        transformer = SSBDTransformer(sample_ssbd_ttl_file)
        studies = transformer.transform_all()
        study = studies[0]

        assert len(study.publications) > 0
        pub = study.publications[0]
        assert pub.doi == "10.1234/test.doi"
        assert pub.pubmed_id == "12345678"
        assert pub.title == "Test Paper Title"
        assert pub.authors_name == "John Smith, Jane Doe"
        assert pub.year == 2023

    def test_transform_dataset_extracts_instrument(self, sample_ssbd_ttl_file: Path):
        """Test that instrument info is correctly extracted."""
        transformer = SSBDTransformer(sample_ssbd_ttl_file)
        studies = transformer.transform_all()
        study = studies[0]

        assert study.image_acquisition_protocols[0].imaging_instrument_description is not None
        assert "Zeiss LSM 880" in study.image_acquisition_protocols[0].imaging_instrument_description

    def test_transform_dataset_extracts_project_url(self, sample_ssbd_ttl_file: Path):
        """Test that source URL is correctly extracted from project."""
        transformer = SSBDTransformer(sample_ssbd_ttl_file)
        studies = transformer.transform_all()
        study = studies[0]

        assert "ssbd.riken.jp" in study.source_url

    def test_transform_dataset_parses_date(self, sample_ssbd_ttl_file: Path):
        """Test that release date is correctly parsed."""
        transformer = SSBDTransformer(sample_ssbd_ttl_file)
        studies = transformer.transform_all()
        study = studies[0]

        assert study.release_date == date(2023, 1, 15)


class TestSSBDTransformerEdgeCases:
    """Test edge cases and error handling for SSBDTransformer."""

    def test_missing_biosample_info(self, tmp_path: Path):
        """Test handling of dataset without biosample info."""
        ttl_content = '''@prefix : <http://ssbd.riken.jp/ontology/> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

:ssbd-dataset-minimal rdf:type :SSBD_dataset ;
    :has_dataset_title "Dataset Without Biosample" .
'''
        ttl_file = tmp_path / "minimal.ttl"
        ttl_file.write_text(ttl_content)

        transformer = SSBDTransformer(ttl_file)
        studies = transformer.transform_all()

        assert len(studies) == 1
        study = studies[0]
        # Should have default unknown organism
        assert len(study.biosamples) > 0
        assert len(study.biosamples[0].organism) > 0
        assert study.biosamples[0].organism[0].scientific_name == "Unknown"

    def test_missing_imaging_method(self, tmp_path: Path):
        """Test handling of dataset without imaging method info."""
        ttl_content = '''@prefix : <http://ssbd.riken.jp/ontology/> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

:ssbd-dataset-minimal rdf:type :SSBD_dataset ;
    :has_dataset_title "Dataset Without Imaging Method" .
'''
        ttl_file = tmp_path / "minimal.ttl"
        ttl_file.write_text(ttl_content)

        transformer = SSBDTransformer(ttl_file)
        studies = transformer.transform_all()

        assert len(studies) == 1
        study = studies[0]
        # Should have default unknown method
        assert len(study.image_acquisition_protocols) > 0
        assert len(study.image_acquisition_protocols[0].methods) > 0
        assert study.image_acquisition_protocols[0].methods[0].name == "Unknown"

    def test_empty_graph(self, tmp_path: Path):
        """Test handling of empty TTL file."""
        ttl_content = '''@prefix : <http://ssbd.riken.jp/ontology/> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
'''
        ttl_file = tmp_path / "empty.ttl"
        ttl_file.write_text(ttl_content)

        transformer = SSBDTransformer(ttl_file)
        studies = transformer.transform_all()

        assert studies == []

    def test_dataset_id_extraction_standard_format(self, sample_ssbd_ttl_file: Path):
        """Test dataset ID extraction from standard URI format."""
        transformer = SSBDTransformer(sample_ssbd_ttl_file)
        uri = URIRef("http://ssbd.riken.jp/ontology/ssbd-dataset-141-TestDataset")
        result = transformer._get_dataset_id(uri)
        assert result == "ssbd-dataset-141-TestDataset"

    def test_dataset_id_extraction_fallback(self, sample_ssbd_ttl_file: Path):
        """Test dataset ID extraction falls back to full URI."""
        transformer = SSBDTransformer(sample_ssbd_ttl_file)
        uri = URIRef("http://example.org/other-format")
        result = transformer._get_dataset_id(uri)
        assert result == "http://example.org/other-format"
