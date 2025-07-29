import streamlit as st
from calculations import load_tax_params, calculate_taxes

st.set_page_config(page_title="Simulateur d'économie d'impôt 3a", layout="centered")
st.title("Simulateur d'économie d'impôt (Pilier 3a)")

# --- Chargez les paramètres fiscaux ---
params = load_tax_params("data/tax_params.json")

# --- Champs utilisateur ---
npa = st.text_input("Votre NPA (ex : 8001)", value="")
income = st.number_input("Revenu imposable annuel (CHF)", min_value=0.0, value=80000.0, step=1000.0)
pillar3a = st.number_input("Montant cotisé au pilier 3a (CHF)", min_value=0.0, value=6800.0, step=100.0)

# Statut civil et nombre d'enfants
statut = st.selectbox("Statut civil", ["Célibataire", "Marié"])
nb_enfants = st.number_input("Nombre d'enfants à charge", min_value=0, value=0, step=1)

# Religion pour la taxe d'église
religion = st.selectbox("Religion (taxe d'église)", params["religions"])

# Bouton de calcul
if st.button("Calculer"):
    try:
        result = calculate_taxes(
            income=income,
            pillar3a=pillar3a,
            npa=npa,
            statut=statut,
            nb_enfants=nb_enfants,
            religion=religion,
            params=params
        )
        st.subheader("Résultats de l'impôt")
        st.write(f"• Impôt sans 3a : **{result['tax_without_3a']:.2f} CHF**")
        st.write(f"• Impôt avec 3a : **{result['tax_with_3a']:.2f} CHF**")
        st.write(f"• Économie d'impôt : **{result['savings']:.2f} CHF**")
    except Exception as e:
        st.error(f"Erreur : {e}")
