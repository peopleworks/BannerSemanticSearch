"""
BM25 inverted index builder with synonym expansion and fuzzy matching support.
Pure algorithms - no AI/ML dependencies.

BM25 (Best Matching 25) is the ranking function used by Elasticsearch, Apache Lucene,
and was the basis of Google's early search. It improves on TF-IDF by normalizing
for document length and applying a saturation function to term frequency.
"""

import math
import re
from collections import defaultdict

# ==================== STOP WORDS ====================
STOP_WORDS = frozenset({
    'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'shall', 'can', 'need', 'must',
    'of', 'to', 'in', 'for', 'on', 'with', 'at', 'by', 'from', 'as',
    'into', 'through', 'during', 'before', 'after', 'above', 'below',
    'between', 'out', 'off', 'over', 'under', 'again', 'further',
    'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how',
    'all', 'each', 'every', 'both', 'few', 'more', 'most', 'other',
    'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same',
    'than', 'too', 'very', 'just', 'because', 'but', 'and', 'or',
    'if', 'while', 'about', 'against', 'up', 'down',
    'it', 'its', 'this', 'that', 'these', 'those', 'what', 'which', 'who',
    'whom', 'he', 'she', 'they', 'them', 'we', 'you', 'me', 'him', 'her',
    # Banner-specific noise
    'table', 'view', 'column', 'field', 'null', 'value',
    'record', 'associated', 'used', 'contains', 'provides', 'retrieves',
})

# ==================== BANNER SYNONYM MAP ====================
# Maps natural language terms to Banner abbreviations and vice versa.
# This is what makes the search feel "intelligent" - it understands Banner naming.
BANNER_SYNONYMS = {
    # Person / Identity
    'employee': ['empl', 'emp', 'pebempl'],
    'empl': ['employee', 'emp'],
    'person': ['pers', 'pidm', 'spriden'],
    'pidm': ['person', 'pers', 'identification', 'internal'],
    'identification': ['ident', 'id', 'pidm'],
    'name': ['last', 'first', 'middle', 'spriden'],
    'student': ['stud', 'learner'],
    'faculty': ['instructor', 'teacher'],
    'vendor': ['vend'],
    # Address / Contact
    'address': ['addr', 'spraddr', 'street', 'city', 'state', 'zip'],
    'addr': ['address', 'spraddr'],
    'telephone': ['tele', 'phone', 'sprtele'],
    'phone': ['telephone', 'tele'],
    'email': ['mail', 'goremal'],
    # Employment
    'hire': ['hired', 'employment', 'current_hire'],
    'termination': ['terminated', 'term', 'separation'],
    'terminated': ['termination', 'term'],
    'salary': ['wage', 'pay', 'compensation', 'earnings'],
    'wage': ['salary', 'pay', 'compensation'],
    'pay': ['salary', 'wage', 'payroll', 'compensation'],
    'payroll': ['pay', 'phr', 'phrhist'],
    'position': ['posn', 'job', 'nbbposn'],
    'posn': ['position', 'job'],
    'job': ['position', 'posn', 'employment'],
    'department': ['dept', 'orgn', 'organization'],
    'dept': ['department', 'orgn'],
    'organization': ['orgn', 'org', 'department'],
    'orgn': ['organization', 'org', 'department'],
    'campus': ['camp'],
    'college': ['coll'],
    'benefit': ['ben', 'bdca', 'deduction'],
    'deduction': ['dedn', 'ded', 'benefit', 'bdca'],
    'dedn': ['deduction', 'ded'],
    'earnings': ['earn', 'salary', 'wage', 'gross', 'net'],
    'gross': ['earnings', 'total', 'amount'],
    'tax': ['withholding', 'w2', '1042', '1099', '1095'],
    'withholding': ['tax', 'deduction'],
    # Academic
    'course': ['crse', 'class', 'section'],
    'crse': ['course', 'class'],
    'grade': ['grde', 'gpa', 'mark'],
    'grde': ['grade', 'gpa'],
    'term': ['semester', 'period', 'academic'],
    'registration': ['enroll', 'enrollment', 'register'],
    'enrollment': ['enroll', 'registration', 'register'],
    'degree': ['dgre', 'diploma', 'certificate'],
    'major': ['majr', 'program', 'concentration'],
    'majr': ['major', 'program'],
    'advisor': ['advr'],
    'admission': ['admit', 'admissions', 'applicant'],
    'applicant': ['admission', 'recruit'],
    'schedule': ['sched'],
    'transcript': ['academic', 'record', 'grades'],
    # Finance
    'account': ['acct', 'fund', 'foapal'],
    'acct': ['account'],
    'fund': ['funding', 'account'],
    'budget': ['budg'],
    'invoice': ['inv'],
    'purchase': ['purch', 'procurement', 'po'],
    'grant': ['sponsored', 'research'],
    # Financial Aid
    'financial_aid': ['finaid', 'aid', 'award'],
    'scholarship': ['award', 'aid'],
    'loan': ['borrow'],
    # General
    'date': ['dt', 'activity_date', 'effective_date'],
    'amount': ['amt', 'total', 'sum'],
    'amt': ['amount', 'total'],
    'number': ['num', 'no', 'count'],
    'description': ['desc'],
    'desc': ['description'],
    'indicator': ['ind', 'flag', 'yes', 'no'],
    'ind': ['indicator', 'flag'],
    'status': ['stat', 'active', 'inactive'],
    'effective': ['eff', 'effective_date'],
    'activity': ['activity_date', 'audit'],
    'sequence': ['seq', 'seqno'],
    'seq': ['sequence', 'seqno'],
    'surrogate': ['surrogate_id', 'unique', 'key'],
    'origin': ['data_origin', 'source'],
    'user': ['user_id', 'operator'],
    'comment': ['comments', 'remark', 'note'],
    'web': ['self_service', 'online'],
    'report': ['rpt', 'reporting'],
}

# ==================== COLUMN PATTERN DEFINITIONS ====================
# These describe what common Banner column suffixes mean.
# Exported to JS for display in the UI.
COLUMN_PATTERNS = {
    '_PIDM': {
        'label': 'Person ID',
        'desc': 'Internal person identifier - links to SPRIDEN',
        'color': '#3b82f6',
    },
    '_CODE': {
        'label': 'Code',
        'desc': 'Validation table reference code',
        'color': '#8b5cf6',
    },
    '_IND': {
        'label': 'Indicator',
        'desc': 'Yes/No or multi-value flag',
        'color': '#f59e0b',
    },
    '_DATE': {
        'label': 'Date',
        'desc': 'Date field',
        'color': '#10b981',
    },
    '_ACTIVITY_DATE': {
        'label': 'Audit',
        'desc': 'Last insert/update timestamp',
        'color': '#6b7280',
    },
    '_SURROGATE_ID': {
        'label': 'Key',
        'desc': 'Immutable surrogate primary key',
        'color': '#ef4444',
    },
    '_DATA_ORIGIN': {
        'label': 'Origin',
        'desc': 'Source system that created the record',
        'color': '#6b7280',
    },
    '_USER_ID': {
        'label': 'User',
        'desc': 'User who last modified the record',
        'color': '#6b7280',
    },
    '_SEQNO': {
        'label': 'Sequence',
        'desc': 'Sequence number within a group',
        'color': '#0ea5e9',
    },
    '_DESC': {
        'label': 'Description',
        'desc': 'Text description field',
        'color': '#84cc16',
    },
    '_AMT': {
        'label': 'Amount',
        'desc': 'Currency/monetary amount',
        'color': '#f97316',
    },
    '_PCT': {
        'label': 'Percent',
        'desc': 'Percentage value',
        'color': '#f97316',
    },
    '_VPDI_CODE': {
        'label': 'VPDI',
        'desc': 'Virtual PDI institution code',
        'color': '#6b7280',
    },
}

# Tokenization pattern
TOKEN_RE = re.compile(r'[a-z0-9]+')


def simple_stem(word: str) -> str:
    """Lightweight suffix stripping."""
    if len(word) <= 3:
        return word
    if word.endswith('tion') and len(word) > 5:
        return word[:-3]
    if word.endswith('sion') and len(word) > 5:
        return word[:-3]
    if word.endswith('ment') and len(word) > 5:
        return word[:-4]
    if word.endswith('ness') and len(word) > 5:
        return word[:-4]
    if word.endswith('ing') and len(word) > 5:
        return word[:-3]
    if word.endswith('ed') and len(word) > 4:
        return word[:-2]
    if word.endswith('ly') and len(word) > 4:
        return word[:-2]
    if word.endswith('er') and len(word) > 4:
        return word[:-2]
    if word.endswith('es') and len(word) > 4:
        return word[:-2]
    if word.endswith('s') and not word.endswith('ss') and len(word) > 3:
        return word[:-1]
    return word


def tokenize(text: str) -> list:
    """Tokenize text: lowercase, split, remove stop words, stem."""
    tokens = TOKEN_RE.findall(text.lower())
    result = []
    for t in tokens:
        if t in STOP_WORDS or len(t) < 2:
            continue
        stemmed = simple_stem(t)
        if stemmed and len(stemmed) >= 2:
            result.append(stemmed)
    return result


def expand_synonyms(tokens: list) -> list:
    """
    Expand tokens with Banner-specific synonyms.
    Returns original tokens + synonym tokens (with lower weight marker).
    """
    expanded = list(tokens)  # originals first
    seen = set(tokens)
    for t in tokens:
        syns = BANNER_SYNONYMS.get(t, [])
        for syn in syns:
            stemmed = simple_stem(syn)
            if stemmed not in seen and stemmed not in STOP_WORDS:
                expanded.append(stemmed)
                seen.add(stemmed)
    return expanded


def build_trigrams(word: str) -> set:
    """Build character trigrams for fuzzy matching."""
    if len(word) < 3:
        return {word}
    padded = f'$${word}$$'
    return {padded[i:i+3] for i in range(len(padded) - 2)}


def build_index(tables: dict) -> dict:
    """
    Build a BM25 inverted index with synonym support.

    BM25 formula:
        score(D, Q) = sum over q in Q of:
            IDF(q) * (tf(q,D) * (k1 + 1)) / (tf(q,D) + k1 * (1 - b + b * |D|/avgdl))

    Where k1=1.5, b=0.75 are standard parameters.
    """
    # BM25 parameters
    K1 = 1.5
    B = 0.75

    tables_list = sorted(tables.keys())
    table_id_map = {name: idx for idx, name in enumerate(tables_list)}

    # Phase 1: Build document tokens
    doc_tokens = {}  # (table_id, col_idx) -> [tokens]
    doc_lengths = {}

    for table_name in tables_list:
        table = tables[table_name]
        tid = table_id_map[table_name]

        # Table-level document
        table_text = f"{table.name} {table.description}"
        table_toks = tokenize(table_text)
        doc_tokens[(tid, -1)] = table_toks
        doc_lengths[(tid, -1)] = len(table_toks)

        # Column-level documents
        for col_idx, col in enumerate(table.columns):
            col_text = f"{col.name} {col.description}"
            col_toks = tokenize(col_text)
            doc_tokens[(tid, col_idx)] = col_toks
            doc_lengths[(tid, col_idx)] = len(col_toks)

    total_docs = len(doc_tokens)
    avg_dl = sum(doc_lengths.values()) / max(total_docs, 1)

    # Phase 2: Document frequency
    df = defaultdict(int)
    for tokens in doc_tokens.values():
        seen = set(tokens)
        for t in seen:
            df[t] += 1

    # Phase 3: IDF (BM25 variant)
    idf = {}
    for token, freq in df.items():
        if freq / total_docs > 0.4:
            continue
        # BM25 IDF: log((N - df + 0.5) / (df + 0.5) + 1)
        idf[token] = math.log((total_docs - freq + 0.5) / (freq + 0.5) + 1)

    # Phase 4: Build inverted index with BM25 scores
    inverted = defaultdict(list)

    for (tid, col_idx), tokens in doc_tokens.items():
        if not tokens:
            continue
        dl = doc_lengths[(tid, col_idx)]
        tf_counts = defaultdict(int)
        for t in tokens:
            tf_counts[t] += 1

        for token, count in tf_counts.items():
            if token not in idf:
                continue
            # BM25 score component
            tf_norm = (count * (K1 + 1)) / (count + K1 * (1 - B + B * dl / avg_dl))
            score = round(idf[token] * tf_norm, 3)
            if score > 0.01:
                inverted[token].append([tid, col_idx, score])

    # Phase 5: Sort and limit posting lists
    for token in inverted:
        inverted[token].sort(key=lambda x: x[2], reverse=True)
        if len(inverted[token]) > 150:
            inverted[token] = inverted[token][:150]

    # Phase 6: Build trigram index for fuzzy matching
    # Maps trigram -> list of tokens that contain it
    trigram_index = defaultdict(list)
    for token in idf:
        if len(token) >= 3:
            for tri in build_trigrams(token):
                trigram_index[tri].append(token)

    # Only keep trigrams that aren't too common (< 500 tokens)
    trigram_index = {
        tri: toks for tri, toks in trigram_index.items()
        if len(toks) < 500
    }

    # Phase 7: Build related tables index (tables sharing column patterns)
    # For each column suffix pattern, find which tables have it
    shared_columns = defaultdict(set)  # column_suffix -> set of table names
    for table_name in tables_list:
        table = tables[table_name]
        for col in table.columns:
            # Extract the part after the table prefix
            parts = col.name.split('_', 1)
            if len(parts) > 1:
                suffix = '_' + parts[1]
                # Only track common linking columns
                if suffix in ('_PIDM', '_TERM_CODE', '_ATYP_CODE', '_CAMP_CODE',
                              '_COLL_CODE', '_DEPT_CODE', '_ECLS_CODE', '_POSN',
                              '_FUND_CODE', '_ORGN_CODE', '_ACCT_CODE', '_PROG_CODE',
                              '_SEQNO', '_MAJR_CODE', '_LEVL_CODE', '_DEGC_CODE',
                              '_SUBJ_CODE', '_CRSE_NUMB'):
                    shared_columns[suffix].add(table_name)

    # Convert to serializable format (only keep useful ones)
    related_index = {}
    for suffix, tbl_set in shared_columns.items():
        if 3 <= len(tbl_set) <= 500:
            related_index[suffix] = sorted(tbl_set)

    return {
        'tables_list': tables_list,
        'table_id_map': table_id_map,
        'index': dict(inverted),
        'idf': idf,
        'total_docs': total_docs,
        'trigrams': dict(trigram_index),
        'synonyms': BANNER_SYNONYMS,
        'column_patterns': COLUMN_PATTERNS,
        'related_index': related_index,
    }
