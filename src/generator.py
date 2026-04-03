"""
Static site generator for Banner Schema Search.
Renders the SPA template with embedded data.
"""

import json
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from src.relationships import serialize_relationships


def build_schema_data(tables: dict, module_summary: dict) -> dict:
    """
    Build the compact schema data structure for embedding in HTML.
    """
    sorted_names = sorted(tables.keys())

    tables_data = {}
    total_columns = 0
    total_tables = 0
    total_views = 0

    for name in sorted_names:
        t = tables[name]
        cols = [[c.name, c.description] for c in t.columns]
        total_columns += len(cols)

        if t.type == 'TABLE':
            total_tables += 1
        else:
            total_views += 1

        tables_data[name] = {
            't': t.type,
            'd': t.description,
            'm': t.module,
            'c': cols,
        }

    modules_data = {}
    for mod_name, info in sorted(module_summary.items(), key=lambda x: -x[1]['count']):
        modules_data[mod_name] = {
            'description': info['description'],
            'count': info['count'],
            'tables': info['tables_count'],
            'views': info['views_count'],
        }

    return {
        'tables': tables_data,
        'modules': modules_data,
        'stats': {
            'totalTables': total_tables,
            'totalViews': total_views,
            'totalColumns': total_columns,
            'totalModules': len(module_summary),
            'built': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
    }


def build_search_index_data(index_result: dict) -> dict:
    """
    Build compact search index for embedding in HTML.
    """
    trigrams = {}
    for tri, tokens in index_result.get('trigrams', {}).items():
        if len(tokens) <= 100:
            trigrams[tri] = tokens

    return {
        'tables': index_result['tables_list'],
        'idf': {k: round(v, 3) for k, v in index_result['idf'].items()},
        'idx': index_result['index'],
        'synonyms': index_result.get('synonyms', {}),
        'trigrams': trigrams,
        'colPatterns': index_result.get('column_patterns', {}),
        'related': index_result.get('related_index', {}),
    }


def generate_site(
    tables: dict,
    module_summary: dict,
    index_result: dict,
    relationships: dict,
    template_dir: str,
    output_dir: str,
):
    """
    Generate the static site with embedded data.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Build data payloads
    schema_data = build_schema_data(tables, module_summary)
    search_index = build_search_index_data(index_result)
    rels_data = serialize_relationships(relationships)

    # Add relationship stats
    total_rels = sum(len(r.get('refs', [])) for r in rels_data.values())
    tables_with_rels = len(rels_data)
    schema_data['stats']['totalRelationships'] = total_rels
    schema_data['stats']['tablesWithRelationships'] = tables_with_rels

    # Load business cases
    business_cases = []
    cases_file = Path(template_dir).parent / 'data' / 'business_cases.txt'
    if cases_file.exists():
        for line in cases_file.read_text(encoding='utf-8', errors='replace').splitlines():
            if line.startswith('CASE_ID') or not line.strip():
                continue
            parts = line.split('|')
            if len(parts) >= 7:
                business_cases.append({
                    'id': parts[0].strip(),
                    'category': parts[1].strip(),
                    'title': parts[2].strip(),
                    'tables': [t.strip().upper() for t in parts[3].split(',')],
                    'description': parts[5].strip(),
                })
        print(f"       Loaded {len(business_cases)} business cases")

    # Render template
    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=False,
    )
    template = env.get_template('index.html')

    html = template.render(
        schema_json=json.dumps(schema_data, separators=(',', ':')),
        index_json=json.dumps(search_index, separators=(',', ':')),
        rels_json=json.dumps(rels_data, separators=(',', ':')),
        business_cases_json=json.dumps(business_cases, separators=(',', ':')),
        build_time=schema_data['stats']['built'],
        stats=schema_data['stats'],
    )

    output_file = output_path / 'index.html'
    output_file.write_text(html, encoding='utf-8')

    return str(output_file)
