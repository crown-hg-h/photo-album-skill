"""Validate original leaf groups and pair adjacent leaves; standard library only."""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


def plan(source):
    source = Path(source).resolve()
    raw = json.loads(source.read_text(encoding='utf-8'))
    pages = raw['pages']
    if not pages or len(pages) % 2:
        raise ValueError('Expected a nonempty even leaf count; decide odd-page treatment explicitly')
    normalized = []; identities = {}; occurrences = Counter()
    for number, page in enumerate(pages, 1):
        if page.get('page') != number:
            raise ValueError(f'Page order is not continuous at {number}')
        photos = []
        for photo in page['photos']:
            pid = photo['id']
            if not isinstance(pid, (str, int)) or isinstance(pid, bool):
                raise ValueError('Photo IDs must be strings or integers')
            path = Path(photo['path'])
            path = (source.parent / path).resolve() if not path.is_absolute() else path.resolve()
            with path.open('rb') as stream:
                digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            if photo.get('sha256') and photo['sha256'] != digest:
                raise ValueError(f'Original hash mismatch: {pid}')
            key = (type(pid).__name__, pid)
            if key in identities and identities[key] != digest:
                raise ValueError(f'ID refers to different originals: {pid}')
            identities[key] = digest; occurrences[key] += 1
            photos.append({'id': pid, 'path': str(path), 'sha256': digest})
        ids = [photo['id'] for photo in photos]
        if len(ids) != len(set(ids)):
            raise ValueError(f'Duplicate photo ID in leaf {number}')
        if 'photo_ids' in page and page['photo_ids'] != ids:
            raise ValueError(f'Photo list order mismatch in leaf {number}')
        poem = page.get('poem', page.get('quote', {}).get('quote', ''))
        if not isinstance(poem, str):
            raise ValueError(f'Expected verbatim poem text in leaf {number}')
        normalized.append({'page': number, 'photo_ids': ids, 'photos': photos, 'poem': poem})
    return {'source': str(source), 'physical_pages': len(pages), 'spreads': len(pages)//2,
            'photo_occurrences': sum(occurrences.values()), 'unique_photo_ids': len(identities),
            'reused_ids': [key[1] for key, count in occurrences.items() if count > 1],
            'entries': [{'spread': i//2+1, 'left': normalized[i], 'right': normalized[i+1]}
                        for i in range(0, len(normalized), 2)]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manuscript', type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    result = plan(args.manuscript)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(f'{result["physical_pages"]} leaves / {result["spreads"]} spreads / {result["unique_photo_ids"]} originals')


if __name__ == '__main__':
    main()
