def parse_page_selection(spec: str | None, page_count: int) -> list[int]:
    if page_count == 0:
        return []
    if not spec or not spec.strip():
        return list(range(page_count))
    
    selected: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start_s, end_s = part.split("-", 1)
            start = int(start_s.strip())
            end = int(end_s.strip())
            if start > end:
                start, end = end, start
            for page_num in range(start, end + 1):
                if 1 <= page_num <= page_count:
                    selected.add(page_num - 1)
        else:
            page_num = int(part)
            if 1 <= page_num <= page_count:
                selected.add(page_num - 1)

    if not selected:
        raise ValueError("No valid pages in selection")
    return sorted(selected)

