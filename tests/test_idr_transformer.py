"""Tests for the IDR transformer."""

from datetime import date
from pathlib import Path

import pytest

from gide_search.schema import Source
from gide_search.transformers.idr import IDRTransformer


class TestIDRTransformer:
    """Test suite for IDRTransformer."""

    def test_init_accepts_path(self, tmp_path: Path):
        """Test that transformer initializes with a path."""
        transformer = IDRTransformer(tmp_path)
        assert transformer.repo_path == tmp_path

    def test_parse_study_file_basic(self, sample_idr_study_file: Path):
        """Test parsing of basic study.txt file."""
        transformer = IDRTransformer(sample_idr_study_file.parent.parent)
        data = transformer._parse_study_file(sample_idr_study_file)

        assert "Comment[IDR Study Accession]" in data
        assert data["Comment[IDR Study Accession]"] == "idr0001"
        assert "Study Title" in data

    def test_parse_study_file_skips_comments(self, sample_idr_study_file: Path):
        """Test that comment lines are skipped during parsing."""
        transformer = IDRTransformer(sample_idr_study_file.parent.parent)
        data = transformer._parse_study_file(sample_idr_study_file)

        # Comment line should not appear as a key
        assert "# Comment line to skip" not in data

    def test_extract_ncbi_taxon_id_valid(self, tmp_path: Path):
        """Test NCBI Taxon ID extraction from valid accession."""
        transformer = IDRTransformer(tmp_path)
        result = transformer._extract_ncbi_taxon_id("NCBITaxon_4932")
        assert result == 4932

    def test_extract_ncbi_taxon_id_from_full_uri(self, tmp_path: Path):
        """Test NCBI Taxon ID extraction from full URI."""
        transformer = IDRTransformer(tmp_path)
        result = transformer._extract_ncbi_taxon_id("http://purl.obolibrary.org/obo/NCBITaxon_9606")
        assert result == 9606

    def test_extract_ncbi_taxon_id_invalid(self, tmp_path: Path):
        """Test NCBI Taxon ID extraction returns None for invalid input."""
        transformer = IDRTransformer(tmp_path)
        assert transformer._extract_ncbi_taxon_id("invalid") is None
        assert transformer._extract_ncbi_taxon_id("") is None
        assert transformer._extract_ncbi_taxon_id(None) is None

    def test_extract_fbbi_id_valid(self, tmp_path: Path):
        """Test FBbi ID extraction from valid accession."""
        transformer = IDRTransformer(tmp_path)
        result = transformer._extract_fbbi_id("FBbi_00000253")
        assert result == "FBbi:00000253"

    def test_extract_fbbi_id_invalid(self, tmp_path: Path):
        """Test FBbi ID extraction returns None for invalid input."""
        transformer = IDRTransformer(tmp_path)
        assert transformer._extract_fbbi_id("invalid") is None
        assert transformer._extract_fbbi_id("") is None
        assert transformer._extract_fbbi_id(None) is None

    def test_parse_date_valid(self, tmp_path: Path):
        """Test date parsing with valid format."""
        transformer = IDRTransformer(tmp_path)
        result = transformer._parse_date("2020-06-15")
        assert result == date(2020, 6, 15)

    def test_parse_date_invalid_returns_default(self, tmp_path: Path):
        """Test date parsing returns default for invalid format."""
        transformer = IDRTransformer(tmp_path)
        assert transformer._parse_date("invalid") == date(2016, 1, 1)
        assert transformer._parse_date("") == date(2016, 1, 1)
        assert transformer._parse_date("2020-13-45") == date(2016, 1, 1)

    def test_parse_authors_single(self, tmp_path: Path):
        """Test parsing single author list."""
        transformer = IDRTransformer(tmp_path)
        authors = transformer._parse_authors("Smith J, Jones A")

        assert len(authors) == 2
        assert authors[0].name == "Smith J"
        assert authors[1].name == "Jones A"

    def test_parse_authors_empty(self, tmp_path: Path):
        """Test parsing empty author list."""
        transformer = IDRTransformer(tmp_path)
        assert transformer._parse_authors("") == []
        assert transformer._parse_authors([]) == []

    def test_parse_authors_list_input(self, tmp_path: Path):
        """Test parsing when author list is a list (takes first)."""
        transformer = IDRTransformer(tmp_path)
        authors = transformer._parse_authors(["Smith J, Jones A", "Other B"])

        assert len(authors) == 2
        assert authors[0].name == "Smith J"

    def test_parse_publications_single(self, tmp_path: Path):
        """Test parsing single publication."""
        transformer = IDRTransformer(tmp_path)
        data = {
            "Study PubMed ID": "12345678",
            "Study DOI": "10.1000/test",
            "Study Publication Title": "Test Paper"
        }
        pubs = transformer._parse_publications(data)

        assert len(pubs) == 1
        assert pubs[0].pubmed_id == "12345678"
        assert pubs[0].doi == "10.1000/test"
        assert pubs[0].title == "Test Paper"

    def test_parse_publications_multiple(self, tmp_path: Path):
        """Test parsing multiple publications."""
        transformer = IDRTransformer(tmp_path)
        data = {
            "Study PubMed ID": ["12345678", "87654321"],
            "Study DOI": ["10.1000/test1", "10.1000/test2"],
            "Study Publication Title": ["Paper 1", "Paper 2"]
        }
        pubs = transformer._parse_publications(data)

        assert len(pubs) == 2
        assert pubs[0].pubmed_id == "12345678"
        assert pubs[1].pubmed_id == "87654321"

    def test_parse_publications_empty(self, tmp_path: Path):
        """Test parsing when no publications."""
        transformer = IDRTransformer(tmp_path)
        pubs = transformer._parse_publications({})
        assert pubs == []

    def test_transform_study_creates_valid_dataset(self, sample_idr_study_file: Path):
        """Test that study file is transformed into valid ImagingDatasetSummary object."""
        transformer = IDRTransformer(sample_idr_study_file.parent.parent)
        study = transformer.transform_study(sample_idr_study_file)

        assert study is not None
        assert study.source == Source.IDR
        assert study.id == "idr:idr0001"
        assert "Cell Division" in study.title

    def test_transform_study_extracts_organism(self, sample_idr_study_file: Path):
        """Test that organism info is correctly extracted."""
        transformer = IDRTransformer(sample_idr_study_file.parent.parent)
        study = transformer.transform_study(sample_idr_study_file)

        assert len(study.biosamples) > 0
        assert len(study.biosamples[0].organism) > 0
        organism = study.biosamples[0].organism[0]
        assert organism.scientific_name == "Saccharomyces cerevisiae"
        assert organism.ncbi_taxon_id == 4932

    def test_transform_study_extracts_imaging_method(self, sample_idr_study_file: Path):
        """Test that imaging method is correctly extracted."""
        transformer = IDRTransformer(sample_idr_study_file.parent.parent)
        study = transformer.transform_study(sample_idr_study_file)

        assert len(study.image_acquisition_protocols) > 0
        assert len(study.image_acquisition_protocols[0].methods) > 0
        method = study.image_acquisition_protocols[0].methods[0]
        assert method.name == "spinning disk confocal microscopy"
        assert method.fbbi_id == "FBbi:00000253"

    def test_transform_study_extracts_sample_type(self, sample_idr_study_file: Path):
        """Test that sample type is correctly extracted."""
        transformer = IDRTransformer(sample_idr_study_file.parent.parent)
        study = transformer.transform_study(sample_idr_study_file)

        assert study.biosamples[0].sample_type == "cell"

    def test_transform_study_extracts_date(self, sample_idr_study_file: Path):
        """Test that release date is correctly extracted."""
        transformer = IDRTransformer(sample_idr_study_file.parent.parent)
        study = transformer.transform_study(sample_idr_study_file)

        assert study.release_date == date(2020, 6, 15)

    def test_transform_study_extracts_license(self, sample_idr_study_file: Path):
        """Test that license is correctly extracted."""
        transformer = IDRTransformer(sample_idr_study_file.parent.parent)
        study = transformer.transform_study(sample_idr_study_file)

        assert study.license == "CC BY 4.0"

    def test_transform_study_extracts_authors(self, sample_idr_study_file: Path):
        """Test that authors are correctly extracted."""
        transformer = IDRTransformer(sample_idr_study_file.parent.parent)
        study = transformer.transform_study(sample_idr_study_file)

        assert len(study.authors) == 3
        assert study.authors[0].name == "Smith J"

    def test_transform_study_extracts_publications(self, sample_idr_study_file: Path):
        """Test that publications are correctly extracted."""
        transformer = IDRTransformer(sample_idr_study_file.parent.parent)
        study = transformer.transform_study(sample_idr_study_file)

        assert len(study.publications) > 0
        pub = study.publications[0]
        assert pub.pubmed_id == "31234567"
        assert pub.doi == "10.1000/test.study"

    def test_transform_study_generates_source_url(self, sample_idr_study_file: Path):
        """Test that source URL is correctly generated."""
        transformer = IDRTransformer(sample_idr_study_file.parent.parent)
        study = transformer.transform_study(sample_idr_study_file)

        assert "idr.openmicroscopy.org" in study.source_url
        assert "idr0001" in study.source_url

    def test_find_study_files(self, sample_idr_study_file: Path):
        """Test finding study files in repo."""
        transformer = IDRTransformer(sample_idr_study_file.parent.parent)
        files = transformer.find_study_files()

        assert len(files) == 1
        assert files[0].name == "idr0001-study.txt"

    def test_transform_all(self, sample_idr_study_file: Path):
        """Test transforming all studies in repo."""
        transformer = IDRTransformer(sample_idr_study_file.parent.parent)
        studies = transformer.transform_all()

        assert len(studies) == 1
        assert studies[0].source == Source.IDR


class TestIDRTransformerEdgeCases:
    """Test edge cases and error handling for IDRTransformer."""

    def test_empty_study_file(self, tmp_path: Path):
        """Test handling of empty study file."""
        study_dir = tmp_path / "idr0002"
        study_dir.mkdir()
        study_file = study_dir / "idr0002-study.txt"
        study_file.write_text("")

        transformer = IDRTransformer(tmp_path)
        study = transformer.transform_study(study_file)

        assert study is None

    def test_study_file_only_comments(self, tmp_path: Path):
        """Test handling of study file with only comments."""
        study_dir = tmp_path / "idr0003"
        study_dir.mkdir()
        study_file = study_dir / "idr0003-study.txt"
        study_file.write_text('# This is a comment\n"# Another comment"\n')

        transformer = IDRTransformer(tmp_path)
        study = transformer.transform_study(study_file)

        assert study is None

    def test_missing_study_accession_uses_filename(self, tmp_path: Path):
        """Test that filename is used when accession is missing."""
        study_dir = tmp_path / "idr0004"
        study_dir.mkdir()
        study_file = study_dir / "idr0004-study.txt"
        study_file.write_text('"Study Title"\t"Test Study"\n')

        transformer = IDRTransformer(tmp_path)
        study = transformer.transform_study(study_file)

        # Should extract ID from filename
        assert study is not None
        assert "idr0004" in study.id

    def test_list_values_handled_correctly(self, tmp_path: Path):
        """Test that list values are handled when single value expected."""
        study_dir = tmp_path / "idr0005"
        study_dir.mkdir()
        study_file = study_dir / "idr0005-study.txt"
        # Simulate multiple values for same field
        study_file.write_text('''"Comment[IDR Study Accession]"\t"idr0005"
"Study Title"\t"Title 1"\t"Title 2"
"Study Organism"\t"Homo sapiens"\t"Mus musculus"
''')

        transformer = IDRTransformer(tmp_path)
        study = transformer.transform_study(study_file)

        assert study is not None
        # Should take first value when multiple present
        assert study.title == "Title 1"

    def test_no_study_files_returns_empty(self, tmp_path: Path):
        """Test that transform_all returns empty list when no study files."""
        transformer = IDRTransformer(tmp_path)
        studies = transformer.transform_all()

        assert studies == []
