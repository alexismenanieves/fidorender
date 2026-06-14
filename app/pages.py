"""Page selection parsing for PDF rendering."""


def _all_page_indices(page_count: int) -> list[int]:
    return list(range(page_count))


def _add_page_if_valid(selected: set[int], page_num: int, page_count: int) -> None:
    if 1 <= page_num <= page_count:
        selected.add(page_num - 1)


def _parse_range_part(part: str, selected: set[int], page_count: int) -> None:
    start_s, end_s = part.split("-", 1)
    start = int(start_s.strip())
    end = int(end_s.strip())
    if start > end:
        start, end = end, start
    for page_num in range(start, end + 1):
        _add_page_if_valid(selected, page_num, page_count)


def _parse_single_part(part: str, selected: set[int], page_count: int) -> None:
    _add_page_if_valid(selected, int(part), page_count)


def _parse_spec_part(part: str, selected: set[int], page_count: int) -> None:
    if "-" in part:
        _parse_range_part(part, selected, page_count)
    else:
        _parse_single_part(part, selected, page_count)


def parse_page_selection(spec: str | None, page_count: int) -> list[int]:
    """Parse a page selection string into zero-based page indices.

    Page numbers in ``spec`` are 1-based. Supported syntax:
    comma-separated values and inclusive ranges (e.g. ``"1,3-5"``).
    An empty or missing spec selects all pages.

    Args:
        spec: Page selection string, or None for all pages.
        page_count: Total number of pages in the document.

    Returns:
        Sorted list of zero-based page indices.

    Raises:
        ValueError: If spec contains no valid pages or invalid integers.
    """
    if page_count == 0:
        return []
    if not spec or not spec.strip():
        return _all_page_indices(page_count)

    selected: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if part:
            _parse_spec_part(part, selected, page_count)

    if not selected:
        raise ValueError("No valid pages in selection")
    return sorted(selected)
