# RO-Crate Template for GIDE Imaging Database Federation

This template shows how to create an RO-Crate metadata file (`ro-crate-metadata.json`) that can be indexed by the GIDE federated search system.

## Quick Start

1. Copy `ro-crate-metadata.json` to your dataset directory
2. Update the values to match your study
3. Validate the JSON structure
4. Submit or host the file alongside your data

## Field Reference

### Required Fields

| Field | Description | Example |
|-------|-------------|---------|
| `identifier` | Unique study/dataset ID | `"S-BIAD1234"`, `"idr0164"` |
| `name` | Study title | `"High-resolution imaging of..."` |
| `description` | Detailed study description | Full paragraph describing the study |
| `datePublished` | Release date (ISO 8601) | `"2024-06-15"` |
| `license` | Data license URL | `"https://creativecommons.org/licenses/by/4.0/"` |
| `url` | Landing page URL for the study | `"https://your-database.org/study/ID"` |

### Recommended Fields

| Field | Description |
|-------|-------------|
| `publisher` | Organization hosting the data |
| `author` | List of study contributors |
| `about` | BioSample information (organism, tissue type) |
| `measurementTechnique` | Imaging protocol and methods |
| `keywords` | Search keywords as array |

### Optional Fields

| Field | Description |
|-------|-------------|
| `citation` | Related publications |
| `funder` | Grant/funding information |

## Entity Types

### Publisher (Organization)

```json
{
    "@id": "#publisher",
    "@type": "Organization",
    "name": "Your Database Name",
    "url": "https://your-database.org"
}
```

### Author (Person)

With ORCID (preferred):
```json
{
    "@id": "https://orcid.org/0000-0001-2345-6789",
    "@type": "Person",
    "name": "Jane Researcher",
    "email": "jane@example.org",
    "affiliation": [{"@id": "#org-1"}]
}
```

Without ORCID:
```json
{
    "@id": "#author-1",
    "@type": "Person",
    "name": "John Smith",
    "affiliation": [{"@id": "#org-1"}]
}
```

### Organization (Affiliation)

```json
{
    "@id": "#org-university",
    "@type": "Organization",
    "name": "University Name",
    "url": "https://university.edu",
    "identifier": "https://ror.org/XXXXXXX"
}
```

### BioSample (Organism/Sample)

```json
{
    "@id": "#biosample-1",
    "@type": "BioSample",
    "name": "Sample name",
    "biologicalEntityDescription": "Detailed description of the biological sample...",
    "organismClassification": [{"@id": "#taxon-1"}]
}
```

### Taxon (Species)

Use NCBI Taxonomy IDs when possible. The `@id` should be the NCBI Taxon URI:

```json
{
    "@id": "#biosample-1",
    "@type": "BioSample",
    "name": "Sample name",
    "biologicalEntityDescription": "Description...",
    "organismClassification": [{"@id": "http://purl.obolibrary.org/obo/NCBITaxon_9606"}]
},
{
    "@id": "http://purl.obolibrary.org/obo/NCBITaxon_9606",
    "@type": "Taxon",
    "scientificName": "Homo sapiens",
    "commonName": "human"
}
```

Common NCBI Taxon IDs:
- Human: `NCBITaxon_9606`
- Mouse: `NCBITaxon_10090`
- Zebrafish: `NCBITaxon_7955`
- Drosophila: `NCBITaxon_7227`
- C. elegans: `NCBITaxon_6239`
- Arabidopsis: `NCBITaxon_3702`

### Imaging Protocol

```json
{
    "@id": "#imaging-protocol-1",
    "@type": "DefinedTerm",
    "name": "Protocol name",
    "description": "Detailed protocol description...",
    "imagingMethodName": ["confocal microscopy"],
    "fbbiId": ["obo:FBbi_00000251"],
    "imagingInstrumentDescription": "Microscope and objective details"
}
```

Common FBbi IDs:
- Confocal microscopy: `FBbi_00000251`
- Fluorescence microscopy: `FBbi_00000246`
- Light sheet microscopy: `FBbi_00000369`
- Electron microscopy: `FBbi_00000258`
- Cryo-electron tomography: `FBbi_00000256`
- Super-resolution microscopy: `FBbi_00000336`

### Publication

```json
{
    "@id": "#publication-1",
    "@type": "ScholarlyArticle",
    "name": "Publication title",
    "identifier": "10.1234/doi.here",
    "datePublished": "2024"
}
```

### Funding

```json
{
    "@id": "#grant-1",
    "@type": "Grant",
    "name": "Funding organization name",
    "identifier": "GRANT-ID-12345"
}
```

## Source Identification

The GIDE indexer automatically identifies the source database from:

1. **Publisher name**: If your `publisher.name` contains "IDR", "SSBD", "BIA", etc.
2. **Accession ID pattern**:
   - `IDR*` → IDR
   - `S-BIAD*` or `EMPIAR-*` → BioImage Archive
   - `SSBD*` → SSBD
   - Other → EXTERNAL

## Validation

Test your RO-Crate with the GIDE transformer:

```bash
uv run gide-search transform-rocrate path/to/ro-crate-metadata.json
uv run gide-search stats output/rocrate.json
```

## Resources

- [RO-Crate Specification](https://www.researchobject.org/ro-crate/1.1/)
- [Schema.org](https://schema.org/)
- [NCBI Taxonomy](https://www.ncbi.nlm.nih.gov/taxonomy)
- [FBbi Ontology](https://www.ebi.ac.uk/ols/ontologies/fbbi)
- [BioImage Archive RO-Crate Profile](https://github.com/BioImage-Archive/bia-ro-crate-examples)
