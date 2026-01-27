# GIDE search input ro-crate profile

## ro-crate-metadata structure overview

As input, we expect a _detached RO-Crate_ consisiting solely of an ro-crate-metadata.json. This file _MUST_:

1. Generally abide by the requirements of a detatched ro-crate. At a high level this includes:
    - 1.1 Contain a self-describing RO-Crate Metadata Descriptor, with an @id of ro-crate-metadata.json, and a conformsTo of https://w3id.org/ro/crate/X where X > 1.2 (the version which defined detached ro-crates)
    - 1.2 Have a root dataset entity which the ro-crate-madatada.json describes (via the 'about' property).
2. The root dataset entity has an @id that is an absolute url to a page where the more information can be found about the entry and the data can be obtained.
3. Use the context term definitions in gide-search-context.jsonld. Additional terms _MAY_ be added, however, terms that are defined in this context _CANNOT_ be changed to point at new IRIs.

### Expected objects

The @graph of the ro-crate-metadata _MUST_ include:

- Exactly one self-describing RO-Crate Metadata Descriptor.
- Exactly one root dataset entity of type _Dataset_, linked from the self-describing RO-Crate Metadata Descriptor via the _about_ property.
- One or more Taxon objects, of type _Taxon_, at least linked to the root dataset entity via the _about_ property.
- One or more_ Imaging Method objects, of type _DefinedTerm_, at least linked to the root dataset entity via the _measurementMethod_ property.
- One or more Authors, of type _Person_, linked to the root dataset entity via the _author_ property.
- Exactly one Publisher object, of type _Organisation_ (or _Person_?), linked to the root dataset entity via the _publisher_ property.

We _RECOMMEND_ including additional objects:
- Objects of type _Organisation_ to describe Author _affiliation_
- Further descriptions of the biological content that was captured in the images, with objects of type _BioSample_, and _DefinedTerm_.
- Further descriptions of the methods used to capture the images, with objects of type _LabProtocol_ and _DefinedTerm_.
- Descriptions of the methods used to analyse or annotation images
- Publications, of type _Publication_, which the dataset supported, or which provide additional detail on the methods used to create the dataset.

## Detailed Object schema

Property prefixes:
- rdf: http://www.w3.org/1999/02/22-rdf-syntax-ns#
- schema: http://schema.org/
- dwc: http://rs.tdwg.org/dwc/terms/
- dwciri: http://rs.tdwg.org/dwc/iri/
- bao: http://www.bioassayontology.org/bao#

Note that the requirements requirements below apply to both the json field names as well as the RDF graph that would be produced by a conversion to RDF using the context of the json-ld document.




### Dataset

| Field | Property | Requirement  | Cardinality | Description |
| --- | --- | :---: | --- | --- |
| @id | | REQUIRED | 1 | URL of the entry in its original database |
| @type | rdf:type | REQUIRED | 1+ | MUST include Dataset, but may include other types. |
| name | schema:name | REQUIRED | 1 | SHOULD identify the dataset to humans |
| description | schema:description | REQUIRED | 1 | |
| datePublished | schema:datePublished | REQUIRED | 1 | MUST be single string value in ISO 8601 date format. SHOULD be specified to the day.
| license | schema:license | REQUIRED | 1 | |
| author | schema:author | REQUIRED | 1+ | A _Person_ or _Organsiation_ who created the dataset |
| publisher | schema:publisher | REQUIRED | 1 | MUST be a an _Organisation_ that provides the data at URL of the @id of this entry |
| about | schema:about | REQUIRED | 1+ | MUST contain all the information of on the biological matter relevant to this dataset. These MAY be _BioSamples_, _Taxons_, or _DefinedTerms_. |
| measurementMethod | dwciri:measurementMethod | REQUIRED | 1+ | MUST contain all the information of on the imaging techniques relevant to this dataset. These MAY be _LabProtocols_, or _DefinedTerms_. |
| thumnailUrl | schema:thumbnailUrl | Recommended | 0+ | MUST be a list of URLs from which a thumbnail of an example image for the dataset can be obtained. For use in displaying example images of the dataset in search results. |
| keywords | schema:keywords | optional | 0+ | |  
| funder | schema:funder | optional | 0+ | The _Grants_ which funded the creation of this dataset.  |  
| seeAlso | rdf:seeAlso | optional | 0+ | The _ScholarlyArticles_ that were published alongside, or supported by, this Dataset. |  
| size | schema:size | optional | 0+ | _QuantitiveValues_ defining dimensions of the Dataset. Some dimensions are recommended (see the _QuantitiveValue_ section below) |  

### Person

| Field | Property | Requirement  | Cardinality | Description |
| --- | --- | :---: | --- | --- |
| @id | | REQUIRED | 1 | SHOULD be an ORCID id, otherwise a local identifier to the document |
| @type | rdf:type | REQUIRED | 1+ | MUST include Person, but may include other types. |
| name | schema:name | REQUIRED | 1 | |
| affiliation | schema:affiliation | Recommended | 0+ | The _Organisations_ a person was a member of at the time of creating or publishing this dataset. |
| email | email | optional | 1 | |
| role | email | optional | 0+ | SHOULD be the _CRediT Role_ of the author. |


### Organisation

| Field | Property | Requirement  | Cardinality | Description |
| --- | --- | :---: | --- | --- |
| @id | | REQUIRED | 1 | SHOULD be an RORID id, otherwise a local identifier to the document. |
| @type | rdf:type | REQUIRED | 1+ | MUST include Organisation, but may include other types. |
| name | schema:name | REQUIRED | 1 | |
| url | schema:url | optional | 1 | |
| address | schema:address | optional | 1 | |

### DefinedTerm

| Field | Property | Requirement  | Cardinality | Description |
| --- | --- | :---: | --- | --- |
| @id | | REQUIRED | 1 | MUST be an absolute URI to documentation about the term |
| @type | rdf:type | REQUIRED | 1+ | MUST include DefinedTerm, but may include other types. |
| name | schema:name | REQUIRED | 1 | SHOULD identify the term to humans |

### Taxon

| Field | Property | Requirement  | Cardinality | Description |
| --- | --- | :---: | --- | --- |
| @id | | REQUIRED | 1 | SHOULD be an NCBI taxonomy ID |
| @type | rdf:type | REQUIRED | 1+ | MUST include Taxon, but may include other types. |
| scientificName | dwc:scientificName | REQUIRED | 1 |  |
| vernacularName | dwc:vernacularName | OPTIONAL | 1 |  |

### BioSample

| Field | Property | Requirement  | Cardinality | Description |
| --- | --- | :---: | --- | --- |
| @id | | REQUIRED | 1 | MUST be an absolute URI to documentation about the term |
| @type | rdf:type | REQUIRED | 1+ | MUST include BioSample, but may include other types. |
| name | schema:name | REQUIRED | 1 | SHOULD identify the term to humans |
| description | schema:description | REQUIRED | 1 | |
| taxonomicRange | schema:taxonomicRange | Recommended | 0+ | The _Taxons_ representing a classification of the  BioSample |
| hasCellLine | bao:hasCellLine | optional | 0+ | The _Taxons_ representing a classification of the  BioSample |

### LabProtocol

| Field | Property | Requirement  | Cardinality | Description |
| --- | --- | :---: | --- | --- |
| @id | | REQUIRED | 1 | MUST be an absolute URI to documentation about the term |
| @type | rdf:type | REQUIRED | 1+ | MUST include LabProtocol, but may include other types. |
| name | schema:name | REQUIRED | 1 | SHOULD identify the term to humans |
| description | schema:description | REQUIRED | 1 | |
| labEquipment | schema:description | Recommended | 0+ | SHOULD be a description of the equipment used in the capture of the image. |
| measurementTechnique | schema:description | Recommended | 0+ | SHOULD be a _DefinedTerm_ from the FBBI ontology if possible. |


### Grant

| Field | Property | Requirement  | Cardinality | Description |
| --- | --- | :---: | --- | --- |
| @id | | REQUIRED | 1 | SHOULD be an RORID id, otherwise a local identifier to the document |
| @type | rdf:type | REQUIRED | 1+ | MUST include Organisation, but may include other types. |
| name | schema:name | REQUIRED | 1 | |
| url | schema:url | optional | 1 | |


### ScholarlyArticle

| Field | Property | Requirement  | Cardinality | Description |
| --- | --- | :---: | --- | --- |
| @id | | REQUIRED | 1 | SHOULD be an RORID id, otherwise a local identifier to the document |
| @type | rdf:type | REQUIRED | 1+ | MUST include Organisation, but may include other types. |
| name | schema:name | REQUIRED | 1 | |
| datePublished | schema:datePublished | Recommended | 1 | MUST be single string value in ISO 8601 date format. |


### QuantitiveValue

| Field | Property | Requirement  | Cardinality | Description |
| --- | --- | :---: | --- | --- |
| @id | | REQUIRED | 1 | SHOULD be a local identifier for the quantititive value. |
| @type | rdf:type | REQUIRED | 1+ | MUST include QuantitativeValue, but may include other types. |
| value | schema:value | REQUIRED | 1 |  |
| unitCode | schema:unitCode | REQUIRED | 1 | |
| unitText | schema:UnitText | REQUIRED | 1 | |
