import json
import os
import unicodedata

def load_json(path: str) -> dict:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def normalize_string(s: str) -> str:
    cleaned = ''.join(ch for ch in s if unicodedata.category(ch)[0] != 'C')
    return cleaned.strip()

# Paths
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
CONFED_PATH = os.path.join(DATA_DIR, 'confederation.json')
CANTONS_PATH = os.path.join(DATA_DIR, 'cantons.json')
COMMUNES_PATH = os.path.join(DATA_DIR, 'communes.json')
DEDUCTIONS_PATH = os.path.join(DATA_DIR, 'deductions.json')

def progressive_tax(income: float, brackets: list) -> float:
    tax = 0.0
    for b in brackets:
        lower = b.get('min', 0)
        upper = b.get('max') if b.get('max') is not None else float('inf')
        rate = b.get('rate', 0)
        taxable = max(0, min(income, upper) - lower)
        tax += taxable * rate
        if income <= upper:
            break
    return tax

def calculate_taxes(income: float,
                    pillar3a: float,
                    npa: str,
                    statut: str,
                    nb_enfants: int,
                    religion: str) -> dict:
    # Load data
    fed_profiles = load_json(CONFED_PATH).get('federal', {})
    cantons_data = load_json(CANTONS_PATH)
    communes_data = load_json(COMMUNES_PATH).get('communes', {})
    deductions = load_json(DEDUCTIONS_PATH)

    # Clean NPA
    npa_clean = str(npa).strip()

    # Find region by NPA
    region = None
    for commune_key, info in communes_data.items():
        npas = info.get('npa', [])
        if any(npa_clean == normalize_string(c) for c in npas):
            region = {'canton': normalize_string(info.get('canton', '')),
                      'commune': normalize_string(commune_key)}
            break
    if not region:
        raise KeyError(f"NPA invalide : {npa_clean}")
    canton_code = region['canton']
    commune_name = region['commune']

    # Determine profile key
    key = ('Personne vivant seule, sans enfant' if statut == 'Célibataire' and nb_enfants == 0
           else 'Personne vivant seule, avec enfant' if statut == 'Célibataire'
           else 'Personne mariée, sans enfant' if statut == 'Marié' and nb_enfants == 0
           else 'Personne mariée / vivant seule, avec enfant')

    # Child deduction
    child_deduction = deductions.get('child', 0) * nb_enfants

    # Federal
    fed = fed_profiles.get(key)
    if not fed:
        raise KeyError(f"Profil fédéral introuvable : {key}")
    net_fed = max(0, income - fed.get('basic_deduction', 0) - child_deduction)
    tax_fed = progressive_tax(net_fed, fed.get('brackets', []))

    # Canton
    canton = cantons_data.get(canton_code)
    if not canton:
        raise KeyError(f"JSON canton invalide : {canton_code}")
    subjects = canton.get('subjects', {})
    can_profile = subjects.get(key) or next(iter(subjects.values()), None)
    if not can_profile:
        raise KeyError(f"Profil cantonal introuvable : {key} pour le canton {canton_code}")
    basic_ded_cant = canton.get('basic_deduction', 0)
    net_cant = max(0, income - basic_ded_cant - child_deduction)
    tax_cant_base = progressive_tax(net_cant, can_profile.get('brackets', []))

    # Communal
    communities = canton.get('communities', {})
    community = communities.get(commune_name)
    if not community:
        for k, v in communities.items():
            if commune_name.lower() in normalize_string(k).lower():
                community = v
                break
    if not community:
        available = ", ".join(communities.keys())
        raise KeyError(f"Commune introuvable : {commune_name}. Clés disponibles : {available}")
    mult = community.get('multiplier', 1)
    tax_comm = tax_cant_base * mult
    church_rate = community.get('church_tax', {}).get(religion, 0)
    tax_church = tax_cant_base * church_rate

    total_without = tax_fed + tax_comm + tax_church

    # With pillar3a
    adj_income = max(0, income - pillar3a)
    net_fed2 = max(0, adj_income - fed.get('basic_deduction', 0) - child_deduction)
    tax_fed2 = progressive_tax(net_fed2, fed.get('brackets', []))
    net_cant2 = max(0, adj_income - basic_ded_cant - child_deduction)
    tax_cant2 = progressive_tax(net_cant2, can_profile.get('brackets', []))
    tax_comm2 = tax_cant2 * mult
    tax_church2 = tax_cant2 * church_rate
    total_with = tax_fed2 + tax_comm2 + tax_church2

    # Return detailed breakdown
    return {
        'tax_without_3a': total_without,
        'tax_with_3a': total_with,
        'savings': total_without - total_with,
        'debug': {
            'canton_code': canton_code,
            'commune_name': commune_name,
            'net_fed': net_fed,
            'tax_fed': tax_fed,
            'net_cant': net_cant,
            'tax_cant_base': tax_cant_base,
            'multiplier': mult,
            'church_rate': church_rate
        }
    }
