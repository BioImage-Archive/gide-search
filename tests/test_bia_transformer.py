"""Tests for the BIA transformer."""

from datetime import date

import pytest
from pytest_httpx import HTTPXMock

from gide_search.schema import Source
from gide_search.transformers.bia import BIATransformer, BIA_API_URL


class TestBIATransformer:
    """Test suite for BIATransformer."""

    def test_init_default_page_size(self):
        """Test that transformer initializes with default page size."""
        transformer = BIATransformer()
        assert transformer.page_size == 50

    def test_init_custom_page_size(self):
        """Test that transformer accepts custom page size."""
        transformer = BIATransformer(page_size=100)
        assert transformer.page_size == 100

    def test_parse_date_valid(self):
        """Test date parsing with valid format."""
        transformer = BIATransformer()
        result = transformer._parse_date("2024-03-20")
        assert result == date(2024, 3, 20)

    def test_parse_date_none_returns_default(self):
        """Test date parsing returns default for None."""
        transformer = BIATransformer()
        result = transformer._parse_date(None)
        assert result == date(2024, 1, 1)

    def test_parse_date_invalid_returns_default(self):
        """Test date parsing returns default for invalid format."""
        transformer = BIATransformer()
        assert transformer._parse_date("invalid") == date(2024, 1, 1)
        assert transformer._parse_date("") == date(2024, 1, 1)
        assert transformer._parse_date("2024-15-45") == date(2024, 1, 1)

    def test_parse_authors_full(self):
        """Test parsing authors with full information."""
        transformer = BIATransformer()
        author_list = [
            {
                "display_name": "Jane Smith",
                "orcid": "0000-0001-2345-6789",
                "contact_email": "jane@example.com",
                "affiliation": [
                    {
                        "display_name": "University of Science",
                        "rorid": "https://ror.org/12345",
                        "address": "123 Science Ave",
                        "website": "https://science.edu"
                    }
                ]
            }
        ]
        authors = transformer._parse_authors(author_list)

        assert len(authors) == 1
        assert authors[0].name == "Jane Smith"
        assert authors[0].orcid == "0000-0001-2345-6789"
        assert authors[0].email == "jane@example.com"
        assert len(authors[0].affiliations) == 1
        assert authors[0].affiliations[0].display_name == "University of Science"
        assert authors[0].affiliations[0].rorid == "https://ror.org/12345"
        assert authors[0].affiliations[0].address == "123 Science Ave"
        assert authors[0].affiliations[0].website == "https://science.edu"

    def test_parse_authors_minimal(self):
        """Test parsing authors with minimal information."""
        transformer = BIATransformer()
        author_list = [
            {
                "display_name": "John Doe",
                "orcid": None,
                "contact_email": None,
                "affiliation": []
            }
        ]
        authors = transformer._parse_authors(author_list)

        assert len(authors) == 1
        assert authors[0].name == "John Doe"
        assert authors[0].orcid is None
        assert authors[0].affiliations == []

    def test_parse_authors_empty(self):
        """Test parsing empty author list."""
        transformer = BIATransformer()
        assert transformer._parse_authors([]) == []

    def test_parse_funding(self):
        """Test parsing funding information."""
        transformer = BIATransformer()
        grant_list = [
            {
                "id": "GRANT-001",
                "funder": [{"display_name": "NSF"}]
            },
            {
                "id": "GRANT-002",
                "funder": [{"display_name": "NIH"}]
            }
        ]
        funding = transformer._parse_funding(grant_list)

        assert len(funding) == 2
        assert funding[0].funder == "NSF"
        assert funding[0].grant_id == "GRANT-001"

    def test_parse_funding_empty_grant_id(self):
        """Test that funding without grant ID is skipped."""
        transformer = BIATransformer()
        grant_list = [{"id": "", "funder": [{"display_name": "NSF"}]}]
        funding = transformer._parse_funding(grant_list)
        assert funding == []

    def test_parse_publications(self):
        """Test parsing publication list."""
        transformer = BIATransformer()
        pub_list = [
            {
                "doi": "10.1234/test",
                "pubmed_id": "12345678",
                "title": "Test Paper"
            }
        ]
        pubs = transformer._parse_publications(pub_list)

        assert len(pubs) == 1
        assert pubs[0].doi == "10.1234/test"
        assert pubs[0].pubmed_id == "12345678"
        assert pubs[0].title == "Test Paper"

    def test_parse_publications_empty_skipped(self):
        """Test that empty publications are skipped."""
        transformer = BIATransformer()
        pub_list = [{"doi": None, "pubmed_id": None, "title": None}]
        pubs = transformer._parse_publications(pub_list)
        assert pubs == []

    def test_extract_organisms(self):
        """Test organism extraction from datasets."""
        transformer = BIATransformer()
        datasets = [
            {
                "biological_entity": [
                    {
                        "organism_classification": [
                            {"scientific_name": "Mus musculus", "common_name": "mouse"}
                        ]
                    }
                ]
            }
        ]
        organisms = transformer._extract_organisms(datasets)

        assert len(organisms) == 1
        assert organisms[0].scientific_name == "Mus musculus"

    def test_extract_organisms_deduplication(self):
        """Test that duplicate organisms are deduplicated."""
        transformer = BIATransformer()
        datasets = [
            {
                "biological_entity": [
                    {"organism_classification": [{"scientific_name": "Mus musculus"}]},
                    {"organism_classification": [{"scientific_name": "Mus musculus"}]}
                ]
            }
        ]
        organisms = transformer._extract_organisms(datasets)

        assert len(organisms) == 1

    def test_extract_organisms_empty_returns_unknown(self):
        """Test that empty datasets return Unknown organism."""
        transformer = BIATransformer()
        organisms = transformer._extract_organisms([])

        assert len(organisms) == 1
        assert organisms[0].scientific_name == "Unknown"

    def test_extract_imaging_methods(self):
        """Test imaging method extraction from datasets."""
        transformer = BIATransformer()
        datasets = [
            {
                "acquisition_process": [
                    {
                        "imaging_method_name": ["confocal microscopy", "fluorescence microscopy"],
                        "fbbi_id": ["00000246", "00000274"]
                    }
                ]
            }
        ]
        methods = transformer._extract_imaging_methods(datasets)

        assert len(methods) == 2
        assert methods[0].name == "confocal microscopy"
        assert methods[0].fbbi_id == "FBbi:00000246"
        assert methods[1].name == "fluorescence microscopy"
        assert methods[1].fbbi_id == "FBbi:00000274"

    def test_extract_imaging_methods_already_formatted_fbbi(self):
        """Test FBbi ID handling when already formatted."""
        transformer = BIATransformer()
        datasets = [
            {
                "acquisition_process": [
                    {
                        "imaging_method_name": ["confocal microscopy"],
                        "fbbi_id": ["FBbi:00000246"]
                    }
                ]
            }
        ]
        methods = transformer._extract_imaging_methods(datasets)

        assert methods[0].fbbi_id == "FBbi:00000246"

    def test_extract_imaging_methods_empty_returns_unknown(self):
        """Test that empty datasets return Unknown method."""
        transformer = BIATransformer()
        methods = transformer._extract_imaging_methods([])

        assert len(methods) == 1
        assert methods[0].name == "Unknown"

    def test_extract_sample_type_tissue(self):
        """Test sample type extraction - tissue."""
        transformer = BIATransformer()
        datasets = [
            {
                "biological_entity": [
                    {"biological_entity_description": "Brain tissue sections", "title": ""}
                ]
            }
        ]
        sample_type = transformer._extract_sample_type(datasets)
        assert sample_type == "tissue"

    def test_extract_sample_type_cell(self):
        """Test sample type extraction - cell."""
        transformer = BIATransformer()
        datasets = [
            {
                "biological_entity": [
                    {"biological_entity_description": "HeLa cell line", "title": ""}
                ]
            }
        ]
        sample_type = transformer._extract_sample_type(datasets)
        assert sample_type == "cell"

    def test_extract_sample_type_unknown(self):
        """Test sample type extraction - unknown."""
        transformer = BIATransformer()
        datasets = [
            {
                "biological_entity": [
                    {"biological_entity_description": "Some specimen", "title": "Sample"}
                ]
            }
        ]
        sample_type = transformer._extract_sample_type(datasets)
        assert sample_type == "unknown"

    def test_extract_file_stats(self):
        """Test file statistics extraction."""
        transformer = BIATransformer()
        datasets = [
            {"file_reference_count": 100, "file_reference_size_bytes": 1000000},
            {"file_reference_count": 50, "file_reference_size_bytes": 500000}
        ]
        file_count, total_size = transformer._extract_file_stats(datasets)

        assert file_count == 150
        assert total_size == 1500000

    def test_extract_file_stats_empty(self):
        """Test file statistics with empty datasets."""
        transformer = BIATransformer()
        file_count, total_size = transformer._extract_file_stats([])

        assert file_count is None
        assert total_size is None

    def test_transform_hit_full(self, sample_bia_api_response: dict):
        """Test transforming a full BIA API hit."""
        transformer = BIATransformer()
        hit = sample_bia_api_response["hits"]["hits"][0]
        study = transformer.transform_hit(hit)

        assert study is not None
        assert study.source == Source.BIA
        assert study.id == "bia:S-BIAD001"
        assert study.title == "Test BIA Study"
        assert "neuronal imaging" in study.description

        # Check authors
        assert len(study.authors) == 2
        assert study.authors[0].name == "Jane Smith"
        assert study.authors[0].orcid == "0000-0001-2345-6789"

        # Check organisms
        assert len(study.biosamples) == 1
        assert len(study.biosamples[0].organism) == 1
        assert study.biosamples[0].organism[0].scientific_name == "Mus musculus"

        # Check imaging methods
        assert len(study.image_acquisition_protocols) == 1
        assert len(study.image_acquisition_protocols[0].methods) == 2
        assert study.image_acquisition_protocols[0].methods[0].name == "confocal microscopy"

        # Check sample type
        assert study.biosamples[0].sample_type == "tissue"

        # Check keywords
        assert "neuroscience" in study.keywords

        # Check file stats
        assert study.file_count == 150
        assert study.total_size_bytes == 5000000000

    def test_transform_hit_minimal(self, sample_bia_hit_minimal: dict):
        """Test transforming a minimal BIA API hit."""
        transformer = BIATransformer()
        study = transformer.transform_hit(sample_bia_hit_minimal)

        assert study is not None
        assert study.source == Source.BIA
        assert study.id == "bia:S-BIAD999"
        assert study.title == "Minimal Study"
        assert study.authors == []
        assert study.publications == []
        assert study.biosamples[0].organism[0].scientific_name == "Unknown"

    def test_transform_hit_missing_accession_id(self):
        """Test that hit without accession_id returns None."""
        transformer = BIATransformer()
        hit = {"_source": {"title": "No ID Study"}}
        study = transformer.transform_hit(hit)

        assert study is None

    def test_transform_hit_generates_source_url(self, sample_bia_api_response: dict):
        """Test that source URL is correctly generated."""
        transformer = BIATransformer()
        hit = sample_bia_api_response["hits"]["hits"][0]
        study = transformer.transform_hit(hit)

        assert "biostudies" in study.source_url
        assert "S-BIAD001" in study.source_url


class TestBIATransformerAPI:
    """Test BIA API integration with mocked HTTP."""

    def test_fetch_studies(self, httpx_mock: HTTPXMock, sample_bia_api_response: dict):
        """Test fetching studies from BIA API."""
        httpx_mock.add_response(json=sample_bia_api_response)

        transformer = BIATransformer()
        hits = transformer.fetch_studies()

        assert len(hits) == 1
        assert hits[0]["_source"]["accession_id"] == "S-BIAD001"

    def test_fetch_studies_with_query(self, httpx_mock: HTTPXMock, sample_bia_api_response: dict):
        """Test fetching studies with a query."""
        httpx_mock.add_response(json=sample_bia_api_response)

        transformer = BIATransformer()
        hits = transformer.fetch_studies(query="test")

        # Verify the request was made
        request = httpx_mock.get_request()
        assert "query=test" in str(request.url)

    def test_fetch_studies_with_page_size(self, httpx_mock: HTTPXMock, sample_bia_api_response: dict):
        """Test fetching studies with custom page size."""
        httpx_mock.add_response(json=sample_bia_api_response)

        transformer = BIATransformer(page_size=25)
        hits = transformer.fetch_studies()

        request = httpx_mock.get_request()
        assert "pagination.page_size=25" in str(request.url)

    def test_fetch_studies_empty_response(self, httpx_mock: HTTPXMock, sample_bia_empty_response: dict):
        """Test handling empty API response."""
        httpx_mock.add_response(json=sample_bia_empty_response)

        transformer = BIATransformer()
        hits = transformer.fetch_studies()

        assert hits == []

    def test_transform_all(self, httpx_mock: HTTPXMock, sample_bia_api_response: dict):
        """Test transform_all fetches and transforms studies."""
        httpx_mock.add_response(json=sample_bia_api_response)

        transformer = BIATransformer()
        studies = transformer.transform_all()

        assert len(studies) == 1
        assert studies[0].source == Source.BIA
        assert studies[0].id == "bia:S-BIAD001"

    def test_transform_all_empty(self, httpx_mock: HTTPXMock, sample_bia_empty_response: dict):
        """Test transform_all with no results."""
        httpx_mock.add_response(json=sample_bia_empty_response)

        transformer = BIATransformer()
        studies = transformer.transform_all()

        assert studies == []

    def test_transform_all_filters_none_results(self, httpx_mock: HTTPXMock):
        """Test that transform_all filters out None results."""
        response = {
            "hits": {
                "hits": [
                    {"_source": {"accession_id": "S-BIAD001", "title": "Valid"}},
                    {"_source": {"title": "No ID"}},  # Missing accession_id
                ]
            }
        }
        httpx_mock.add_response(json=response)

        transformer = BIATransformer()
        studies = transformer.transform_all()

        # Should only have one valid study
        assert len(studies) == 1
        assert studies[0].id == "bia:S-BIAD001"
