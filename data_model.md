# Data Model Summary

The schema defines a unified metadata model for biological imaging datasets across three sources: **IDR**, **SSBD**, and **BIA**.

## Core Models

### ImagingDatasetSummary (main entity)

The top-level model representing high-level summary information about an imaging dataset (not detailed image-level information):

- **Core identification**: `id`, `source`, `source_url`, `title`, `description`, `license`, `release_date`
- **Structured objects**: `biosamples`, `image_acquisition_protocols`, `publications`, `authors`, `funding`
- **Additional metadata**: `data_doi`, `keywords`, `study_type`, `file_count`, `total_size_bytes`

### BioSample

Biological sample information:

- `organism`: list[Organism] - Species studied
- `sample_type`: str - Type of sample (cell, tissue, organism)
- `biological_entity_description`: str | None - Specific tissue/cell type studied
- `strain`: str | None - Strain name (for model organisms)
- `cell_line`: str | None - Cell line name

#### Organism
- `scientific_name`: str - Scientific species name (e.g., 'Homo sapiens')
- `common_name`: str | None - Common name (e.g., 'human')
- `ncbi_taxon_id`: int | None - NCBI Taxonomy ID (e.g., 9606)

### ImageAcquisitionProtocol

Imaging methodology and equipment:
- `methods`: list[ImagingMethod] - Imaging techniques used
- `protocol_description`: str | None - Description of the imaging protocol
- `imaging_instrument_description`: str | None - Description of instruments used

#### ImagingMethod
- `name`: str - Method name (e.g., 'fluorescence microscopy')
- `fbbi_id`: str | None - FBbi ontology ID (e.g., 'FBbi:00000246')

### Other Nested Models

| Model | Purpose | Key Fields |
|-------|---------|------------|
| `Source` | Enum for data sources | IDR, SSBD, BIA |
| `Organisation` | Institution | `display_name`, `rorid`, `address`, `website`, `country` |
| `Author` | Study author | `name`, `orcid`, `email`, `affiliations` |
| `Publication` | Associated paper | `doi`, `pubmed_id`, `pmc_id`, `title`, `authors_name`, `year` |
| `Funding` | Grant info | `funder`, `grant_id` |

## Ontology Support
- **NCBI Taxonomy**: `Organism.ncbi_taxon_id` (links `scientific_name` to taxonomy)
- **FBbi (imaging methods)**: `ImagingMethod.fbbi_id`
- **ORCID**: `Author.orcid`
- **ROR**: `Organisation.rorid`
