"""
backend/tests/test_dependencies.py
─────────────────────────────────────────────────────────────────────────────
Unit tests for backend/api/dependencies.py
─────────────────────────────────────────────────────────────────────────────
"""

import pytest
from backend.api.dependencies import (
    PaginationParams,
    get_pagination,
    get_score_filter,
)
from fastapi import HTTPException


class TestPaginationParams:

    def test_page_1_offset_0(self):
        p = PaginationParams(page=1, limit=20)
        assert p.offset == 0

    def test_page_2_offset_20(self):
        p = PaginationParams(page=2, limit=20)
        assert p.offset == 20

    def test_page_3_limit_10(self):
        p = PaginationParams(page=3, limit=10)
        assert p.offset == 20  # (3-1) * 10

    def test_stores_page_and_limit(self):
        p = PaginationParams(page=5, limit=50)
        assert p.page == 5
        assert p.limit == 50


class TestGetScoreFilter:

    def test_valid_range(self):
        min_s, max_s = get_score_filter(min_score=20.0, max_score=80.0)
        assert min_s == 20.0
        assert max_s == 80.0

    def test_equal_values_allowed(self):
        min_s, max_s = get_score_filter(min_score=50.0, max_score=50.0)
        assert min_s == max_s == 50.0

    def test_min_exceeds_max_raises_400(self):
        with pytest.raises(HTTPException) as exc_info:
            get_score_filter(min_score=80.0, max_score=20.0)
        assert exc_info.value.status_code == 400
        assert 'min_score' in exc_info.value.detail

    def test_full_range_valid(self):
        min_s, max_s = get_score_filter(min_score=0.0, max_score=100.0)
        assert min_s == 0.0
        assert max_s == 100.0
