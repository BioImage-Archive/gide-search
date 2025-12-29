"""Shared test fixtures for gide-search transformers."""

import pytest
from pathlib import Path
import tempfile


@pytest.fixture
def sample_ssbd_ttl() -> str:
    """Sample SSBD ontology TTL content for testing."""
    return '''@prefix : <http://ssbd.riken.jp/ontology/> .
@prefix obo: <http://purl.obolibrary.org/obo/> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

:ssbd-project-001 rdf:type :SSBD_Project ;
    :has_project_url "https://ssbd.riken.jp/repository/ssbd-repos-000001/" ;
    :has_description "Test project description" ;
    :has_license "CC BY 4.0" ;
    :has_submission_date "2023-01-15" ;
    :has_dataset_output :ssbd-dataset-001 ;
    :has_project_publications :ssbd-paper-001 .

:ssbd-dataset-001 rdf:type :SSBD_dataset ;
    :has_dataset_title "Test Dataset Title" ;
    rdfs:label "ssbd-dataset-001-TestLabel" ;
    :has_biosample_information :ssbd-biosample-001 ;
    :has_imaging_method_total_info :ssbd-imaging-001 .

:ssbd-biosample-001 rdf:type :SSBD_biosample_information ;
    :is_about_organism obo:NCBITaxon_10090 ;
    :is_about_strain :mouse-strain-C57BL6 .

obo:NCBITaxon_10090 rdfs:label "Mus musculus" .

:ssbd-imaging-001 rdf:type :SSBD_imaging_method_information ;
    :has_imaging_method_recorded_type obo:FBbi_00000246 ;
    :has_body "Zeiss LSM 880" .

obo:FBbi_00000246 rdfs:label "confocal microscopy" .

:ssbd-paper-001 rdf:type :SSBD_paper_information ;
    :has_doi "10.1234/test.doi" ;
    :has_PMID "12345678" ;
    :has_paper_information "John Smith, Jane Doe (2023) Test Paper Title, Journal of Science, Volume 1, pp. 1-10" .
'''


@pytest.fixture
def sample_ssbd_ttl_file(sample_ssbd_ttl: str, tmp_path: Path) -> Path:
    """Create a temporary TTL file with sample SSBD data."""
    ttl_file = tmp_path / "ssbd_test.ttl"
    ttl_file.write_text(sample_ssbd_ttl)
    return ttl_file


@pytest.fixture
def sample_idr_study_txt() -> str:
    """Sample IDR study.txt content for testing."""
    return '''"# Comment line to skip"
"Comment[IDR Study Accession]"	"idr0001"
"Study Title"	"Test Study: Investigation of Cell Division"
"Study Description"	"A comprehensive study examining cell division patterns in yeast cells using fluorescence microscopy."
"Study Organism"	"Saccharomyces cerevisiae"
"Study Organism Term Accession"	"NCBITaxon_4932"
"Study Public Release Date"	"2020-06-15"
"Study License"	"CC BY 4.0"
"Study Author List"	"Smith J, Jones A, Brown K"
"Study PubMed ID"	"31234567"
"Study DOI"	"10.1000/test.study"
"Study Publication Title"	"Cell Division Dynamics in Yeast"
"Screen Imaging Method"	"spinning disk confocal microscopy"
"Screen Imaging Method Term Accession"	"FBbi_00000253"
"Screen Sample Type"	"cell"
'''


@pytest.fixture
def sample_idr_study_file(sample_idr_study_txt: str, tmp_path: Path) -> Path:
    """Create a temporary study.txt file with sample IDR data."""
    # Create directory structure like idr0001/idr0001-study.txt
    study_dir = tmp_path / "idr0001"
    study_dir.mkdir()
    study_file = study_dir / "idr0001-study.txt"
    study_file.write_text(sample_idr_study_txt)
    return study_file


@pytest.fixture
def sample_bia_api_response() -> dict:
    """Sample BIA API response for testing."""
    return {
        "hits": {
            "total": {"value": 1},
            "hits": [
                {
                    "_source": {
                        "accession_id": "S-BIAD001",
                        "title": "Test BIA Study",
                        "description": "A study of neuronal imaging in mice using confocal microscopy.",
                        "licence": "CC0",
                        "release_date": "2024-03-20",
                        "doi": "10.5281/zenodo.12345",
                        "keyword": ["neuroscience", "imaging", "confocal"],
                        "author": [
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
                            },
                            {
                                "display_name": "John Doe",
                                "orcid": None,
                                "contact_email": None,
                                "affiliation": []
                            }
                        ],
                        "grant": [
                            {
                                "id": "GRANT-001",
                                "funder": [{"display_name": "National Science Foundation"}]
                            }
                        ],
                        "related_publication": [
                            {
                                "doi": "10.1234/pub.12345",
                                "pubmed_id": "98765432",
                                "title": "Neuronal Imaging Methods"
                            }
                        ],
                        "dataset": [
                            {
                                "biological_entity": [
                                    {
                                        "organism_classification": [
                                            {
                                                "scientific_name": "Mus musculus",
                                                "common_name": "house mouse"
                                            }
                                        ],
                                        "biological_entity_description": "Brain tissue sections",
                                        "title": "Mouse brain"
                                    }
                                ],
                                "acquisition_process": [
                                    {
                                        "imaging_method_name": ["confocal microscopy", "fluorescence microscopy"],
                                        "fbbi_id": ["00000246", "00000274"]
                                    }
                                ],
                                "file_reference_count": 150,
                                "file_reference_size_bytes": 5000000000
                            }
                        ]
                    }
                }
            ]
        }
    }


@pytest.fixture
def sample_bia_empty_response() -> dict:
    """Sample BIA API response with no results."""
    return {
        "hits": {
            "total": {"value": 0},
            "hits": []
        }
    }


@pytest.fixture
def sample_bia_hit_minimal() -> dict:
    """Minimal BIA API hit for testing edge cases."""
    return {
        "_source": {
            "accession_id": "S-BIAD999",
            "title": "Minimal Study",
            "description": "Minimal description",
            "licence": "Unknown",
            "release_date": None,
            "author": [],
            "grant": [],
            "related_publication": [],
            "keyword": [],
            "dataset": []
        }
    }
