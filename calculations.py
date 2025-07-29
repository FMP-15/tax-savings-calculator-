import json
import os

def load_json(path: str) -> dict:
    """Charge un fichier JSON depuis le chemin donné."""
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
    """
    Calcule l'impôt selon un barème progressif.

    :param income: montant imposable
    :param brackets: liste de dict {'min','max','rate'}
    :returns: montant d'impôt
    """
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
    """
    Calcule l'impôt fédéral, cantonal et communal (et taxe d'église),
    avec et sans pilier 3a, depuis vos JSON:
    - confederation.json
    - cantons.json (contenant plusieurs cantons)
    - communes.json
    - deductions.json

    :param income: revenu imposable annuel
    :param pillar3a: montant versé en pilier 3a
    :param npa: code postal (ex: '1136')
    :param statut: 'Célibataire' ou 'Marié'
    :param nb_enfants: nombre d'enfants à charge
    :param religion: clé parmi params['deductions']
    :returns: dict avec tax_without_3a, tax_with_3a, savings
    """
    # Chargement des paramètres
    fed_profiles = load_json(CONFED_PATH).get('federal', {})
    cantons_data = load_json(CANTONS_PATH)
    communes_data = load_json(COMMUNES_PATH).get('communes', {})
    deductions = load_json(DEDUCTIONS_PATH)

    # Profil fiscal utilisateur
    key = None
    if statut == 'Célibataire':
        key = 'Personne vivant seule, sans enfant' if nb_enfants == 0 else 'Personne vivant seule, avec enfant'
    else:
        key = 'Personne mariée, sans enfant' if nb_enfants == 0 else 'Personne mariée / vivant seule, avec enfant'

    # Déductions enfants
    child_deduction = deductions.get('child', 0) * nb_enfants

    # --- Impôt fédéral ---
    fed = fed_profiles.get(key)
    if not fed:
        raise KeyError(f"Profil fédéral introuvable : {key}")
    net_fed = max(0, income - fed.get('basic_deduction', 0) - child_deduction)
    tax_fed = progressive_tax(net_fed, fed.get('brackets', []))

    # --- Région (canton + commune) via NPA ---
    region = communes_data.get(str(npa))
    if not region:
        raise KeyError(f"NPA invalide : {npa}")
    canton_code = region.get('canton')
    commune_name = region.get('commune')

    canton = cantons_data.get(canton_code)
    if not canton:
        raise KeyError(f"JSON canton invalide : {canton_code}")

    # --- Impôt cantonal ---
    subjects = canton.get('subjects', {})
    subject_cant = subjects.get(key) or next(iter(subjects.values()))
    basic_ded_cant = canton.get('basic_deduction', 0)
    net_cant = max(0, income - basic_ded_cant - child_deduction)
    tax_cant_base = progressive_tax(net_cant, subject_cant.get('brackets', []))

    # --- Impôt communal ---
    community = canton.get('communities', {}).get(commune_name)
    if not community:
        raise KeyError(f"Commune introuvable : {commune_name}")
    mult = community.get('multiplier', 1)
    tax_comm = tax_cant_base * mult

    # --- Taxe d'église ---
    church_rate = community.get('church_tax', {}).get(religion, 0)
    tax_church = tax_cant_base * church_rate

    total_without = tax_fed + tax_comm + tax_church

    # --- Avec pilier 3a ---
    adj_income = max(0, income - pillar3a)
    # Fédéral
    net_fed2 = max(0, adj_income - fed.get('basic_deduction', 0) - child_deduction)
    tax_fed2 = progressive_tax(net_fed2, fed.get('brackets', []))
    # Cantonal
    net_cant2 = max(0, adj_income - basic_ded_cant - child_deduction)
    tax_cant2 = progressive_tax(net_cant2, subject_cant.get('brackets', []))
    tax_comm2 = tax_cant2 * mult
    # Église
    tax_church2 = tax_cant2 * church_rate
    total_with = tax_fed2 + tax_comm2 + tax_church2

    return {
        'tax_without_3a': total_without,
        'tax_with_3a': total_with,
        'savings': total_without - total_with
    }
