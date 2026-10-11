"""Conservative identity matching. A baseline candidate is not a reference label."""
import unicodedata


def normalize_title(value):
    value = unicodedata.normalize('NFKC', value or '').casefold().replace('×', 'x')
    return ''.join(c for c in value if c.isalnum())


def assess_identity(candidate, rule):
    if not candidate:
        return 'not_found', 'no_candidate'
    if not rule:
        return 'review_required', 'no_independent_identity_reference'
    cid = str(candidate.get('id', candidate.get('tmdb_id', '')))
    original = normalize_title(candidate.get('original_name', ''))
    year = str(candidate.get('first_air_date', ''))[:4]
    if cid != str(rule['tmdb_id']):
        return 'review_required', 'tmdb_id_conflict'
    if original not in {normalize_title(s) for s in rule['original_names']}:
        return 'review_required', 'original_name_conflict'
    if year != str(rule['year']):
        return 'review_required', 'production_year_conflict'
    if rule.get('require_edition_choice'):
        return 'review_required', 'edition_not_specified_1999_or_2011'
    if not rule.get('reference_verified'):
        return 'review_required', 'reference_id_not_independently_verified'
    return 'identity_verified', 'reference_id_original_name_year_agree'


def choose_candidate(results, rule, aliases):
    """Never silently choose the first search result; preserve ambiguity."""
    unique = {str(r['id']): r for r in results if r.get('id') is not None}
    if rule and str(rule['tmdb_id']) in unique:
        candidate = unique[str(rule['tmdb_id'])]
        status, reason = assess_identity(candidate, rule)
        return candidate, status, reason
    names = {normalize_title(a) for a in aliases}
    matches = [r for r in unique.values() if any(
        normalize_title(r.get(key, '')) in names for key in ('name', 'original_name'))]
    if len(matches) == 1:
        candidate = matches[0]
        status, reason = assess_identity(candidate, rule)
        return candidate, status, reason
    return None, 'review_required' if unique else 'not_found', 'ambiguous_candidates' if unique else 'no_candidate'
