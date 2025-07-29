import streamlit as st
from calculations import load_tax_params, calculate_taxes

st.set_page_config(page_title="Simulateur d'économie d'impôt 3a", layout="centered")
st.title("Simulateur d'économie d'impôt (Pilier 3a)")

# Charger les paramètres fiscaux depuis le JSON mis à jour
params = load_tax_params("data/tax_params_updated.json")

# Saisie des données utilisateur
npa = st.text_input("Votre NPA (ex : 8001)", value="")
income = st.number_input("Revenu imposable annuel (CHF)", min_value=0.0, value=80000.0, step=1000.0)
pillar3a = st.number_input("Montant cotisé au pilier 3a (CHF)", min_value=0.0, value=6800.0, step=100.0)
subject = st.selectbox("Profil fiscal", list(params["federal"].keys()))
religion = st.selectbox("Religion (taxe d'église)", params["religions"])

if st.button("Calculer"):
    try:
        result = calculate_taxes(income, pillar3a, npa, subject, religion, params)
        st.subheader("Résultats de l'impôt")
        st.write(f"• Impôt sans 3a : **{result['tax_without_3a']:.2f} CHF**")
        st.write(f"• Impôt avec 3a : **{result['tax_with_3a']:.2f} CHF**")
        st.write(f"• Économie d'impôt : **{result['savings']:.2f} CHF**")
    except Exception as e:
        st.error(f"Erreur : {e}")
