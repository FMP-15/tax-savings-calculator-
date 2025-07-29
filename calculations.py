import json
import os

def load_json(path: str) -> dict:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_paths():
    base = os.path.abspath(os.path.dirname(__file__))
    data_dir = os.path.join(base, 'data')
    return {
        'federal': os.path.join(data_dir, 'confederation', 'confederation.json'),
        'cantons_dir': os.path.join(data_dir, 'cantons'),
        'communal': os.path.join(data_dir, 'communal', 'communes.json'),
        'deductions': os.path.join(data_dir, 'deductions.json')
    }


def load_all_cantons(cantons_dir: str) -> dict:
    """
    Charge tous les fichiers JSON cantonaux et retourne un dict {cantonName: data}
    """
    cantons = {}
    for fname in os.listdir(cantons_dir):
        if not fname.endswith('.json'):
            continue
        cname = fname[:-5]  # enlève '.json'
        path = os.path.join(cantons_dir, fname)
        cantons[cname] = load_json(path)
    return cantons


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
    paths = get_paths()

    # Chargement des données
    fed_data = load_json(paths['federal']).get('federal', {})
    communal_data = load_json(paths['communal']).get('communes', {})
    deductions_data = load_json(paths['deductions'])
    cantons_data = load_all_cantons(paths['cantons_dir'])

    # Région d'habitation via NPA
    region = communal_data.get(npa)
    if not region:
        raise KeyError(f'NPA invalide : {npa}')
    canton_name = region.get('canton')
    commune_name = region.get('commune')

    # Profil clé
    if statut == 'Célibataire':
        subject_key = ('Personne vivant seule, sans enfant'
                       if nb_enfants == 0 else 'Personne vivant seule, avec enfant')
    else:
        subject_key = ('Personne mariée, sans enfant'
                       if nb_enfants == 0 else 'Personne mariée / vivant seule, avec enfant')

    # Déductions par enfant
    child_ded = deductions_data.get('child', 0) * nb_enfants

    # Impôt fédéral
    fed_profile = fed_data.get(subject_key)
    if not fed_profile:
        raise KeyError(f"Profil fédéral introuvable : {subject_key}")
    base_fed = max(0, income - fed_profile.get('basic_deduction', 0) - child_ded)
    tax_fed = progressive_tax(base_fed, fed_profile.get('brackets', []))

    # Impôt cantonal
    canton_profile = cantons_data.get(canton_name)
    if not canton_profile:
        raise KeyError(f"Cantons JSON introuvable pour : {canton_name}")
    cant_subjects = canton_profile.get('subjects', {})
    can = cant_subjects.get(subject_key) or next(iter(cant_subjects.values()), None)
    if not can:
        raise KeyError(f"Profil cantonal introuvable pour {canton_name}: {subject_key}")
    base_cant = max(0, income - canton_profile.get('basic_deduction', 0) - child_ded)
    tax_can_base = progressive_tax(base_cant, can.get('brackets', []))

    # Impôt communal
    comm_profile = canton_profile.get('communities', {}).get(commune_name)
    if not comm_profile:
        raise KeyError(f"Commune introuvable pour {canton_name}: {commune_name}")
    mult = comm_profile.get('multiplier', 1)
    tax_comm = tax_can_base * mult

    # Taxe d'église
    church_rate = comm_profile.get('church_tax', {}).get(religion, 0)
    tax_church = tax_can_base * church_rate

    total_without = tax_fed + tax_comm + tax_church

    # Avec pilier 3a
    adj_income = max(0, income - pillar3a)
    fed2 = max(0, adj_income - fed_profile.get('basic_deduction', 0) - child_ded)
    tax_fed2 = progressive_tax(fed2, fed_profile.get('brackets', []))
    cant2 = max(0, adj_income - canton_profile.get('basic_deduction', 0) - child_ded)
    tax_can2 = progressive_tax(cant2, can.get('brackets', []))
    tax_comm2 = tax_can2 * mult
    tax_church2 = tax_can2 * church_rate
    total_with = tax_fed2 + tax_comm2 + tax_church2

    return {
        'tax_without_3a': total_without,
        'tax_with_3a': total_with,
        'savings': total_without - total_with
    }
