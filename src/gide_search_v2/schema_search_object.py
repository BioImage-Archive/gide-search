from pydantic import BaseModel, Field


class JsonLdNode(BaseModel):
    id: str | None = Field(default=None, alias="@id")
    type: list[str] = Field(default_factory=list, alias="@type")


class QuantitiveValue(JsonLdNode):
    value: int | None = None
    unitText: str | None = None
    unitCode: str | None = None


class Organization(JsonLdNode):
    name: str | None = None
    url: str | None = None
    address: str | None = None


class Person(JsonLdNode):
    name: str | None = None
    email: str | None = None
    affiliation: list[Organization] = Field(default_factory=list)


class Grant(JsonLdNode):
    name: str | None = None
    identifier: str | None = None


class Publication(JsonLdNode):
    name: str | None = None
    datePublished: str | None = None


class Taxon(JsonLdNode):
    vernacularName: str | None = None
    scientificName: str | None = None


class CellLine(JsonLdNode):
    name: str | None = None


class BioSample(JsonLdNode):
    name: str | None = None
    description: str | None = None
    taxonomicRange: list[Taxon] = Field(default_factory=list)
    hasCellLine: list[CellLine] = Field(default_factory=list)


class MeasurementTechnique(JsonLdNode):
    name: str | None = None


class MeasurementMethod(JsonLdNode):
    name: str | None = None
    description: str | None = None
    measurementTechnique: list[MeasurementTechnique] = Field(default_factory=list)
    labEquipment: str | None = None


class Entry(JsonLdNode):
    identifier: str | None = None
    name: str | None = None
    description: str | None = None
    datePublished: str | None = None
    license: str | None = None
    keywords: list[str] = Field(default_factory=list)

    publisher: Organization | None = None
    author: list[Person] = Field(default_factory=list)
    funder: list[Grant] = Field(default_factory=list)
    citation: list[Publication] = Field(default_factory=list)
    about: list[BioSample] = Field(default_factory=list)
    measurementMethod: list[MeasurementMethod] = Field(default_factory=list)
    size: list[QuantitiveValue] = Field(default_factory=list)
