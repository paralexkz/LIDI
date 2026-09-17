"""Pydantic schemas describing what to extract from a page.

Passing one of these to :func:`lidi.scrape` switches ScrapeGraphAI into
structured-output mode: the model is constrained to the schema and the result
comes back shaped like it, instead of as free-form JSON.

Field descriptions are part of the prompt the model sees, so they are written
as instructions to the extractor — say what counts, and what does not.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class Person(BaseModel):
    full_name: str = Field(description="Person's full name as printed on the page")
    role: Optional[str] = Field(None, description="Job title, exactly as stated")
    linkedin_url: Optional[str] = Field(None, description="Full LinkedIn profile URL if linked")


class Company(BaseModel):
    company_name: str = Field(description="Legal or trading name of the firm")
    website: Optional[str] = Field(None, description="Official website domain")
    jurisdiction: Optional[str] = Field(
        None,
        description="Country of incorporation ONLY if explicitly stated "
        "(e.g. in legal notice or imprint). Not the office address.",
    )
    people: List[Person] = Field(default_factory=list, description="Named founders and executives")


#: Schemas selectable by name from the command line.
REGISTRY: dict[str, type[BaseModel]] = {
    "company": Company,
    "person": Person,
}
