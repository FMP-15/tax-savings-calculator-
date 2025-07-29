import json
import os

# Paths to JSON files
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "data"))
CONFED_PATH = os.path.join(BASE_DIR, "confederation", "confederation.json")
CANTONS_DIR = os.path.join(BASE_DIR, "cantons")
COMMUNAL_PATH = os.path.join(BASE_DIR, "communal", "communes.json")


def load_json(path: str) -> dict:
    """Charge un fichier JSON et retourne son contenu."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_confederation() -> dict:
    """Charge et retourne la section fédérale entière."""
    data = load_json(CONFED_PATH)
    return data.get("federal", {})


def load_canton(canton_code: str) -> dict:
    """Charge et retourne les données pour un canton donné."""
    path = os.path.join(CANTONS_DIR, f"{canton_code}.json")
    data = load_json(path)
    return data


def load_communal() -> dict:
    """Charge et retourne toutes les communes."""
    data = load_json(COMMUNAL_PATH)
    return data.get("communes", {})


def progressive_tax(income: float, brackets: list) -> float:
    """
    Calcule l'impôt par tranches.
    :param income: montant imposable
    :param brackets: liste de dict {'min','max','rate'}
    """
    tax = 0.0
    for b in brackets:
        lower = b.get("min", 0)
        upper = b.get("max") if b.get("max") is not None else float("inf")
        rate = b.get("rate", 0)
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
    Calcule impôts fédéral, cantonal, communal et église, avec et sans 3a,
    en chargeant dynamiquement les JSON appropriés.
    """
    # 1) Charger barèmes
    fed_profiles = load_confederation()
    communes = load_communal()

    # Trouver canton et commune via NPA
    region = communes.get(npa)
    if not region:
        raise KeyError(f"NPA invalide : {npa}")
    canton_code = region.get("canton")
    commune_name = region.get("commune")

    canton_data = load_canton(canton_code)
    canton_subjects = canton_data.get("subjects", {})
    canton_communes = canton_data.get("communities", {})
    basic_ded = canton_data.get("basic_deduction", 0)

    # 2) Déterminer clé de sujet
    subject_key = None
    if statut == "Célibataire":
        subject_key = "Personne vivant seule, sans enfant" if nb_enfants == 0 else "Personne vivant seule, avec enfant"
    elif statut == "Marié":
        subject_key = "Personne mariée, sans enfant" if nb_enfants == 0 else "Personne mariée / vivant seule, avec enfant"
    else:
        raise ValueError(f"Statut civil inconnu : {statut}")

    fed = fed_profiles.get(subject_key)
    if fed is None:
        raise KeyError(f"Profil fédéral introuvable : {subject_key}")

    # 3) Déductions
    child_ded = load_json(os.path.join(BASE_DIR, "deductions.json")).get("child", 0) * nb_enfants

    # 4) Calcul impôts sans 3a
    # Fédéral
    income_fed = max(0, income - fed.get("basic_deduction", 0) - child_ded)
    tax_fed = progressive_tax(income_fed, fed.get("brackets", []))

    # Cantonal
    can = canton_subjects.get(subject_key)
    if not can:
        can = next(iter(canton_subjects.values()))
    income_cant = max(0, income - basic_ded - child_ded)
    tax_can_base = progressive_tax(income_cant, can.get("brackets", []))

    # Communal
    comm = canton_communes.get(commune_name, {})
    mult = comm.get("multiplier", 1)
    tax_comm = tax_can_base * mult

    # Église
    church_rate = comm.get("church_tax", {}).get(religion, 0)
    tax_church = tax_can_base * church_rate

    total_without = tax_fed + tax_comm + tax_church

    # 5) Calcul avec pilier 3a
    adj_income = max(0, income - pillar3a)
    # Fédéral
    income_fed2 = max(0, adj_income - fed.get("basic_deduction", 0) - child_ded)
    tax_fed2 = progressive_tax(income_fed2, fed.get("brackets", []))
    # Cantonal
    income_cant2 = max(0, adj_income - basic_ded - child_ded)
    tax_can2 = progressive_tax(income_cant2, can.get("brackets", []))
    tax_comm2 = tax_can2 * mult
    # Église
    tax_church2 = tax_can2 * church_rate

    total_with = tax_fed2 + tax_comm2 + tax_church2

    return {
        "tax_without_3a": total_without,
        "tax_with_3a": total_with,
        "savings": total_without - total_with
    }
