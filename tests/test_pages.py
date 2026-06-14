import pytest

from app.pages import parse_page_selection


def test_parse_all_pages_when_spec_empty():
    assert parse_page_selection(None, 3) == [0, 1, 2]
    assert parse_page_selection("", 3) == [0, 1, 2]
    assert parse_page_selection("   ", 3) == [0, 1, 2]


def test_parse_single_page():
    assert parse_page_selection("2", 3) == [1]


def test_parse_range_and_list():
    assert parse_page_selection("1,3-4", 4) == [0, 2, 3]


def test_parse_reversed_range():
    assert parse_page_selection("4-2", 4) == [1, 2, 3]


def test_parse_ignores_out_of_range_pages():
    assert parse_page_selection("0,5,2", 3) == [1]


def test_parse_empty_document():
    assert parse_page_selection(None, 0) == []


def test_parse_invalid_integer_raises():
    with pytest.raises(ValueError):
        parse_page_selection("abc", 3)


def test_parse_no_valid_pages_raises():
    with pytest.raises(ValueError, match="No valid pages"):
        parse_page_selection("9,10", 3)
