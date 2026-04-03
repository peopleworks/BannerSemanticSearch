#!/usr/bin/env python3
"""
Banner Schema Search - Static Site Builder

Reads Banner table_info.txt and field_info.txt, builds a TF-IDF search index,
and generates a self-contained HTML application for searching the schema.

Usage:
    python build.py --data <path_to_data_dir> --output <output_dir>
    python build.py  # uses defaults

Requirements:
    pip install jinja2
"""

import argparse
import sys
import time
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.parser import parse_all
from src.categorizer import categorize_tables
from src.indexer import build_index
from src.relationships import build_relationships
from src.generator import generate_site


def main():
    parser = argparse.ArgumentParser(
        description='Banner Schema Search - Static Site Builder'
    )
    parser.add_argument(
        '--data', '-d',
        default=str(PROJECT_ROOT / 'data'),
        help='Directory containing table_info.txt and field_info.txt'
    )
    parser.add_argument(
        '--output', '-o',
        default=str(PROJECT_ROOT / 'docs'),
        help='Output directory for generated site'
    )
    args = parser.parse_args()

    print('=' * 60)
    print('  Banner Schema Search - Build')
    print('=' * 60)

    start_time = time.time()

    # Step 1: Parse data files
    print(f'\n[1/4] Parsing data files from: {args.data}')
    tables = parse_all(args.data)
    total_cols = sum(len(t.columns) for t in tables.values())
    print(f'       Found {len(tables)} tables/views with {total_cols:,} columns')

    # Step 2: Categorize tables
    print('\n[2/4] Categorizing tables by Banner module...')
    module_summary = categorize_tables(tables)
    for mod_name, info in sorted(module_summary.items(), key=lambda x: -x[1]['count']):
        print(f'       {mod_name:25s} {info["count"]:5d} objects')

    # Step 3: Build search index
    print('\n[3/5] Building BM25 search index...')
    index_result = build_index(tables)
    print(f'       Indexed {index_result["total_docs"]:,} documents')
    print(f'       {len(index_result["idf"]):,} unique tokens in vocabulary')
    print(f'       {len(index_result["index"]):,} tokens in inverted index')

    # Step 4: Build relationships
    print(f'\n[4/5] Building table relationships...')
    relationships = build_relationships(tables, args.data)

    # Step 5: Generate site
    template_dir = str(PROJECT_ROOT / 'templates')
    print(f'\n[5/5] Generating site to: {args.output}')
    output_file = generate_site(
        tables=tables,
        module_summary=module_summary,
        index_result=index_result,
        relationships=relationships,
        template_dir=template_dir,
        output_dir=args.output,
    )

    elapsed = time.time() - start_time
    file_size = Path(output_file).stat().st_size
    size_mb = file_size / (1024 * 1024)

    print(f'\n{"=" * 60}')
    print(f'  Build complete in {elapsed:.1f}s')
    print(f'  Output: {output_file}')
    print(f'  Size: {size_mb:.1f} MB')
    print(f'{"=" * 60}')
    print(f'\n  Open in browser: file:///{output_file.replace(chr(92), "/")}')
    print()


if __name__ == '__main__':
    main()
