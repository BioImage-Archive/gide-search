from urllib import parse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from typing_extensions import Self

# Prefixes that might occur in object IDs that are likely to get shortened, which would be better left as full IRIs.
PREFIXES_TO_EXPAND = {
    "obo": "http://purl.obolibrary.org/obo/",
    "bao": "http://www.bioassayontology.org/bao#",
}


class JsonLdNode(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,  # accept `id` AND `@id`
        extra="allow",
    )
    id: str = Field(alias="@id")
    type: list[str] = Field(alias="@type")

    @field_validator("id", mode="before")
    @classmethod
    def expand_id(cls, value) -> str:
        # In case context is stripped, it is best to expand object IDs
        if not isinstance(value, str):
            raise TypeError

        split_id = value.split(":", 1)
        if len(split_id) > 1:
            for prefix, full_url in PREFIXES_TO_EXPAND.items():
                if split_id[0] == prefix:
                    return f"{full_url}{split_id[1]}"
        return value


class QuantitiveValue(JsonLdNode):
    value: int
    unitText: str | None = None
    unitCode: str | None = None


class Organization(JsonLdNode):
    name: str

    url: str | None = None
    address: str | None = None


class Publisher(Organization):

    @field_validator("id", mode="after")
    @classmethod
    def standarise_id_url(cls, value: str):
        try:
            x = parse.urlsplit(value)
        except Exception as e:
            raise e

        if not value.endswith("/"):
            return f"{value}/"
        return value


class Person(JsonLdNode):
    name: str

    affiliation: list[Organization] = Field(default_factory=list)
    email: str | None = None


class Grant(JsonLdNode):
    name: str
    identifier: str | None = None


class Publication(JsonLdNode):
    name: str | None = None
    datePublished: str | None = None


class Taxon(JsonLdNode):
    scientificName: str

    name: str | None = None
    vernacularName: str | None = None

    @model_validator(mode="after")
    def fill_name(self) -> Self:
        if not self.name:
            self.name = self.scientificName

        return self

    @field_validator("id", mode="after")
    @classmethod
    def strip_leading_zeroes(cls, value: str) -> str:
        if value.startswith("http://purl.obolibrary.org/obo/NCBITaxon_0"):
            digits = str(value).split("_")[1]
            normalised_digits = int(digits)

            return f"http://purl.obolibrary.org/obo/NCBITaxon_{normalised_digits}"
        else:
            return value


class DefinedTerm(JsonLdNode):
    name: str

    @field_validator("id", mode="after")
    @classmethod
    def fix_common_iri_errors(cls, value: str) -> str:
        # FBbi ids require that specific capitalization, which is easy to get incorrect.
        if value.lower().startswith("http://purl.obolibrary.org/obo/fbbi_"):
            digits = str(value).split("_")[1].zfill(8)[-8:]
            return f"http://purl.obolibrary.org/obo/FBbi_{digits}"
        else:
            return value


class BioSample(JsonLdNode):
    name: str
    description: str

    taxonomicRange: list[Taxon] = Field(default_factory=list)
    hasCellLine: list[DefinedTerm | str] | str = Field(default_factory=list)


class LabProtocol(JsonLdNode):
    name: str
    description: str | None = Field(None)

    measurementTechnique: list[DefinedTerm] = Field(default_factory=list)
    labEquipment: str | None = None


class Dataset(JsonLdNode):
    name: str
    author: list[Person]
    description: str
    datePublished: str
    license: str
    publisher: Publisher
    about: list[BioSample | DefinedTerm | Taxon] = Field()
    measurementMethod: list[LabProtocol | DefinedTerm] = Field()

    thumbnailUrl: list[str] = Field(default_factory=list)
    identifier: str | None = None
    keywords: list[str] = Field(default_factory=list)
    funder: list[Grant] = Field(default_factory=list)
    seeAlso: list[Publication] = Field(default_factory=list)
    size: list[QuantitiveValue] = Field(default_factory=list)

    @field_validator("about", mode="before")
    @classmethod
    def discriminate_about(cls, value):
        if not isinstance(value, list):
            return value
        out = []
        for item in value:
            if isinstance(item, dict):
                types = item.get("@type") or item.get("type") or []
                if isinstance(types, str):
                    types = [types]
                if "BioSample" in types:
                    out.append(BioSample.model_validate(item))
                elif "Taxon" in types:
                    out.append(Taxon.model_validate(item))
                elif "DefinedTerm" in types:
                    out.append(DefinedTerm.model_validate(item))
                else:
                    out.append(item)
            else:
                out.append(item)
        return out

    @field_validator("measurementMethod", mode="before")
    @classmethod
    def discriminate_measurement_method(cls, value):
        if not isinstance(value, list):
            return value
        out = []
        for item in value:
            if isinstance(item, dict):
                types = item.get("@type") or item.get("type") or []
                if isinstance(types, str):
                    types = [types]
                if "LabProtocol" in types:
                    out.append(LabProtocol.model_validate(item))
                elif "DefinedTerm" in types:
                    out.append(DefinedTerm.model_validate(item))
                else:
                    out.append(item)
            else:
                out.append(item)
        return out

    @model_validator(mode="before")
    @classmethod
    def remove_indexing_fields(self, data):
        index_fields = ["taxon_ids", "imaging_method_ids"]

        if isinstance(data, dict):
            for field in index_fields:
                data.pop(field, None)
        return data


class IndexableDataset(Dataset):
    taxon_ids: list[Taxon] = Field(default_factory=list)
    imaging_method_ids: list[DefinedTerm] = Field(default_factory=list)

    @model_validator(mode="after")
    def poplate_additional_index_fields(self) -> Self:
        """
        Populate the fields that get used for facetting
        """
        for biological_object in self.about:
            if isinstance(biological_object, Taxon):
                self.taxon_ids.append(biological_object)

        for measurment_object in self.measurementMethod:
            if isinstance(measurment_object, DefinedTerm) and (
                measurment_object.id.startswith("http://purl.obolibrary.org/obo/FBbi_")
            ):
                self.imaging_method_ids.append(measurment_object)
        return self
