"""Pydantic schema for unified study metadata across IDR, SSBD, and BioImage Archive."""

from datetime import date
from enum import Enum

from pydantic import BaseModel, Field


class Source(str, Enum):
    """Data source identifier."""

    IDR = "IDR"
    SSBD = "SSBD"
    BIA = "BIA"


class Organism(BaseModel):
    """Species with optional NCBI Taxonomy identifier."""

    scientific_name: str = Field(description="Scientific species name (e.g., 'Homo sapiens')")
    common_name: str | None = Field(default=None, description="Common name (e.g., 'human')")
    ncbi_taxon_id: int | None = Field(default=None, description="NCBI Taxonomy ID (e.g., 9606)")


class ImagingMethod(BaseModel):
    """Imaging technique with optional FBbi ontology identifier."""

    name: str = Field(description="Method name (e.g., 'fluorescence microscopy')")
    fbbi_id: str | None = Field(
        default=None, description="FBbi ontology ID (e.g., 'FBbi:00000246')"
    )


class Organisation(BaseModel):
    """Institution or organization affiliation."""

    display_name: str
    rorid: str | None = Field(default=None, description="Research Organization Registry ID")
    address: str | None = None
    website: str | None = None
    country: str | None = None


class Author(BaseModel):
    """Study author."""

    name: str
    orcid: str | None = None
    email: str | None = None
    affiliations: list[Organisation] = Field(default_factory=list)


class Publication(BaseModel):
    """Associated publication."""

    doi: str | None = Field(default=None, description="Publication DOI")
    pubmed_id: str | None = None
    pmc_id: str | None = None
    title: str | None = None
    authors_name: str | None = Field(default=None, description="Free text list of author names")
    year: int | None = None


class Funding(BaseModel):
    """Grant or funding source."""

    funder: str
    grant_id: str


class BioSample(BaseModel):
    """Biological sample information."""

    organism: list[Organism] = Field(description="Species studied")
    sample_type: str = Field(description="Type of sample (cell, tissue, organism)")
    biological_entity_description: str | None = Field(
        default=None, description="Specific tissue/cell type studied"
    )
    strain: str | None = Field(default=None, description="Strain name (for model organisms)")
    cell_line: str | None = Field(default=None, description="Cell line name")


class ImageAcquisitionProtocol(BaseModel):
    """Imaging methodology and equipment."""

    methods: list[ImagingMethod] = Field(description="Imaging techniques used")
    protocol_description: str | None = Field(default=None, description="Description of the imaging protocol")
    imaging_instrument_description: str | None = Field(default=None, description="Description of instruments used")


class Study(BaseModel):
    """Unified study metadata schema.

    Core fields are required and present in all sources.
    Extended fields are optional and vary by source.
    """

    # Core identification
    id: str = Field(description="Unique identifier, prefixed by source (e.g., 'idr:idr0164')")
    source: Source
    source_url: str = Field(description="Original study landing page URL")
    title: str
    description: str
    license: str = Field(description="Data license (e.g., 'CC BY 4.0')")
    release_date: date

    # Structured objects
    biosamples: list[BioSample] = Field(description="Biological samples used in the study")
    image_acquisition_protocols: list[ImageAcquisitionProtocol] = Field(
        description="Image acquisition protocols used in the study"
    )
    publications: list[Publication] = Field(default_factory=list)
    authors: list[Author] = Field(default_factory=list)
    funding: list[Funding] = Field(default_factory=list)

    # Additional metadata
    data_doi: str | None = Field(default=None, description="DOI for the dataset itself")
    keywords: list[str] = Field(default_factory=list)
    study_type: list[str] = Field(
        default_factory=list, description="Type of study (e.g., 'protein localization')"
    )
    file_count: int | None = Field(default=None, description="Number of files in dataset")
    total_size_bytes: int | None = Field(default=None, description="Total data size in bytes")
