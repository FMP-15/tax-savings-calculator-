import json
import os

def load_json(path: str) -> dict:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

# Définition des chemins en fonction de votre structure
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
    # Chargement des paramètres
    fed_profiles = load_json(CONFED_PATH).get('federal', {})
    cantons_data = load_json(CANTONS_PATH)
    communes_data = load_json(COMMUNES_PATH).get('communes', {})
    deductions = load_json(DEDUCTIONS_PATH)

    # Nettoyage du NPA
    npa_clean = str(npa).strip()

    # Recherche de la région via NPA dans communes.json
    region = None
    for commune_name, info in communes_data.items():
        # info['npa'] est une liste de codes postaux
        if npa_clean in info.get('npa', []):
            region = {'canton': info.get('canton'), 'commune': commune_name}
            break
    if not region:
        raise KeyError(f"NPA invalide : {npa_clean}")
    canton_code = region['canton']
    commune_name = region['commune']

    # Détermination du profil fédéral
    if statut == 'Célibataire':
        key = 'Personne vivant seule, sans enfant' if nb_enfants == 0 else 'Personne vivant seule, avec enfant'
    else:
        key = 'Personne mariée, sans enfant' if nb_enfants == 0 else 'Personne mariée / vivant seule, avec enfant'

    # Déduction par enfant
    child_deduction = deductions.get('child', 0) * nb_enfants

    # --- Calcul impôt fédéral ---
    fed = fed_profiles.get(key)
    if not fed:
        raise KeyError(f"Profil fédéral introuvable : {key}")
    net_fed = max(0, income - fed.get('basic_deduction', 0) - child_deduction)
    tax_fed = progressive_tax(net_fed, fed.get('brackets', []))

    # --- Calcul impôt cantonal ---
    canton = cantons_data.get(canton_code)
    if not canton:
        raise KeyError(f"JSON canton invalide : {canton_code}")
    subjects = canton.get('subjects', {})
    can_profile = subjects.get(key) or next(iter(subjects.values()), None)
    if not can_profile:
        raise KeyError(f"Profil cantonal introuvable : {key} dans {canton_code}")
    basic_ded_cant = canton.get('basic_deduction', 0)
    net_cant = max(0, income - basic_ded_cant - child_deduction)
    tax_can_base = progressive_tax(net_cant, can_profile.get('brackets', []))

    # --- Calcul impôt communal ---
    community = canton.get('communities', {}).get(commune_name)
    if not community:
        raise KeyError(f"Commune introuvable : {commune_name}")
    mult = community.get('multiplier', 1)
    tax_comm = tax_can_base * mult

    # --- Taxe d'église ---
    church_rate = community.get('church_tax', {}).get(religion, 0)
    tax_church = tax_can_base * church_rate

    total_without = tax_fed + tax_comm + tax_church

    # --- Calcul avec pilier 3a ---
    adj_income = max(0, income - pillar3a)
    net_fed2 = max(0, adj_income - fed.get('basic_deduction', 0) - child_deduction)
    tax_fed2 = progressive_tax(net_fed2, fed.get('brackets', []))
    net_cant2 = max(0, adj_income - basic_ded_cant - child_deduction)
    tax_can2 = progressive_tax(net_cant2, can_profile.get('brackets', []))
    tax_comm2 = tax_can2 * mult
    tax_church2 = tax_can2 * church_rate
    total_with = tax_fed2 + tax_comm2 + tax_church2

    return {
        'tax_without_3a': total_without,
        'tax_with_3a': total_with,
        'savings': total_without - total_with
    }
