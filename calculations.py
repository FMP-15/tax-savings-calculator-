import json

def load_tax_params(path: str = "data/tax_params.json") -> dict:
    """Charge les paramètres fiscaux depuis un fichier JSON."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def progressive_tax(income: float, brackets: list) -> float:
    """
    Calcule l'impôt progressif selon les tranches.

    :param income: montant imposable
    :param brackets: liste de dict {"min", "max", "rate"}
    :returns: montant d'impôt
    """
    tax = 0.0
    for b in brackets:
        lower = b["min"]
        upper = b.get("max") if b.get("max") is not None else float("inf")
        rate = b["rate"]
        taxable = max(0, min(income, upper) - lower)
        tax += taxable * rate
        if income <= upper:
            break
    return tax


def derive_subject_key(statut: str, nb_enfants: int) -> str:
    """
    Retourne la clé du profil fédéral selon l'état civil et le nombre d'enfants.
    """
    if statut == "Célibataire":
        return "Personne vivant seule, sans enfant" if nb_enfants == 0 else "Personne vivant seule, avec enfant"
    elif statut == "Marié":
        return "Personne mariée, sans enfant" if nb_enfants == 0 else "Personne mariée / vivant seule, avec enfant"
    else:
        raise ValueError(f"Statut civil inconnu: {statut}")


def calculate_taxes(income: float,
                    pillar3a: float,
                    npa: str,
                    statut: str,
                    nb_enfants: int,
                    religion: str,
                    params: dict) -> dict:
    """
    Calcule impôts fédéral, cantonal, communal et église,
    avec et sans pilier 3a.

    :param income: revenu annuel imposable
    :param pillar3a: montant déduit du pilier 3a
    :param npa: code postal suisse de résidence
    :param statut: "Célibataire" ou "Marié"
    :param nb_enfants: nombre d'enfants à charge
    :param religion: clé parmi params['religions']
    :param params: dictionnaire des paramètres fiscaux
    :returns: dict {"tax_without_3a", "tax_with_3a", "savings"}
    """
    # Profil fédéral
    subject_key = derive_subject_key(statut, nb_enfants)
    fed = params.get("federal", {}).get(subject_key)
    if fed is None:
        raise KeyError(f"Profil fédéral introuvable: {subject_key}")

    # Impôt fédéral
    income_net_fed = max(0, income - fed.get("basic_deduction", 0))
    tax_fed = progressive_tax(income_net_fed, fed.get("brackets", []))

    # Région d'habitation
    region = params.get("postal_to_region", {}).get(str(npa))
    if not region:
        raise KeyError(f"NPA invalide: {npa}")
    canton = region.get("canton")
    commune = region.get("commune")

    # Données cantonales
    canton_data = params.get("cantons", {}).get(canton, {})
    subjects = canton_data.get("subjects", {})
    communities = canton_data.get("communities", {})

    # Choisir profil cantonal adapté
    can = subjects.get(subject_key)
    if can is None:
        # Si célibataire, prendre la première clé contenant 'vivant seule'
        if statut == "Célibataire":
            for k, v in subjects.items():
                if "vivant seule" in k:
                    can = v
                    break
        # Si marié, prendre la clé 'Marié(e)'
        elif statut == "Marié":
            can = subjects.get("Marié(e)")
        if can is None:
            raise KeyError(f"Profil cantonal introuvable pour {canton}: {subject_key}")

    # Déduction cantonale
    cant_deduction = canton_data.get("basic_deduction", 0)
    income_net_cant = max(0, income - cant_deduction)
    tax_can_base = progressive_tax(income_net_cant, can.get("brackets", []))

    # Impôt communal
    community = communities.get(commune)
    if community is None:
        raise KeyError(f"Commune introuvable pour {canton}: {commune}")
    mult = community.get("multiplier", 1)
    tax_can_comm = tax_can_base * mult

    # Taxe d'église
    church_rate = community.get("church_tax", {}).get(religion, 0)
    tax_church = tax_can_base * church_rate

    # Total sans pilier 3a
    total_without = tax_fed + tax_can_comm + tax_church

    # Avec pilier 3a
    adj_income = max(0, income - pillar3a)
    income_net_fed2 = max(0, adj_income - fed.get("basic_deduction", 0))
    tax_fed2 = progressive_tax(income_net_fed2, fed.get("brackets", []))
    income_net_cant2 = max(0, adj_income - cant_deduction)
    tax_can_base2 = progressive_tax(income_net_cant2, can.get("brackets", []))
    tax_can_comm2 = tax_can_base2 * mult
    tax_church2 = tax_can_base2 * church_rate
    total_with = tax_fed2 + tax_can_comm2 + tax_church2

    return {
        "tax_without_3a": total_without,
        "tax_with_3a": total_with,
        "savings": total_without - total_with
    }

