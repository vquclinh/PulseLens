# Tests for M4 triangulation — corroboration count, contradiction detection, recency decay
import pytest
from app.pipeline.m4_triangulation import triangulate, recency_weight, weighted_sentiment
from app.schemas.models import FactObject, VerifiedClaim
