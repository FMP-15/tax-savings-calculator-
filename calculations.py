import json

def load_tax_params(path="tax_params_updated.json"):
    """Charge les paramètres fiscaux depuis un fichier JSON."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def progressive_tax(income, brackets):
    """
    Calcule l'impôt progressif selon les tranches.
    income: revenu taxable
    brackets: liste de dict avec 'min', 'max', 'rate'
    """
    tax = 0.0
    for b in brackets:
        lower = b["min"]
        upper = b["max"] if b["max"] is not None else float("inf")
        rate = b["rate"]
        taxable = max(0, min(income, upper) - lower)
        tax += taxable * rate
        if income <= upper:
            break
    return tax

def calculate_taxes(income, pillar3a, npa, subject, religion, params):
    """
    Calcule impôt fédéral, cantonal, communal et église,
    avec et sans pilier 3a. Retourne dict des montants.
    """
    # Charger profil fédéral
    fed = params["federal"][subject]
    # Taxable fédéral
    income_net_fed = max(0, income - fed["basic_deduction"])
    tax_fed = progressive_tax(income_net_fed, fed["brackets"])
    # Région d'habitation
    region = params["postal_to_region"].get(str(npa))
    if region is None:
        raise ValueError(f"NPA invalide : {npa}")
    canton = region["canton"]
    commune = region["commune"]
    # Cantonal
    can = params["cantons"][canton]["subjects"][subject]
    tax_can_base = progressive_tax(income, can["brackets"])
    # Communal (multiplicateur)
    community = params["cantons"][canton]["communities"][commune]
    mult = community["multiplier"]
    tax_can_comm = tax_can_base * mult
    # Église
    church_rate = community["church_tax"].get(religion, 0)
    tax_church = tax_can_base * church_rate
    # Total sans 3a
    total_without = tax_fed + tax_can_comm + tax_church
    # Avec 3a: on retire pillar3a de l'assiette pour tous les niveaux
    adj_income = max(0, income - pillar3a)
    income_net_fed2 = max(0, adj_income - fed["basic_deduction"])
    tax_fed2 = progressive_tax(income_net_fed2, fed["brackets"])
    tax_can_base2 = progressive_tax(adj_income, can["brackets"])
    tax_can_comm2 = tax_can_base2 * mult
    tax_church2 = tax_can_base2 * church_rate
    total_with = tax_fed2 + tax_can_comm2 + tax_church2
    return {
        "tax_without_3a": total_without,
        "tax_with_3a": total_with,
        "savings": total_without - total_with
    }
