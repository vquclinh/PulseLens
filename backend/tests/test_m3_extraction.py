# Tests for M3 fact extraction — validates quote grounding and schema constraints
import pytest
from app.pipeline.m3_fact_extraction import extract_facts, validate_fact
from app.schemas.models import RawDocument, FactObject
