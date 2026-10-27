"""Merge name and content results without hiding content behind a full name list."""
def merge_results(names, contents, limit=40):
    snippets = {row['path']: row['snippet'] for row in contents}
    annotated = []
    for row in names:
        item = dict(row)
        path = item.get('path')
        if path in snippets:
            item['snippet'] = snippets[path]
        annotated.append(item)
    reserved = min(len(contents), limit // 2)
    kept = annotated[:limit-reserved]
    kept_paths = {row.get('path') for row in kept}
    for row in contents:
        if len(kept) == limit:
            break
        if row['path'] not in kept_paths:
            kept.append(row)
            kept_paths.add(row['path'])
    for row in annotated[limit-reserved:]:
        if len(kept) == limit:
            break
        path = row.get('path')
        if path is None or path not in kept_paths:
            kept.append(row)
            if path is not None: kept_paths.add(path)
    return kept
