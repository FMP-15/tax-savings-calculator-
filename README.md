# Simulateur d’économie d’impôt (Pilier 3a)

Ce projet est un outil web interactif, développé avec Python et Streamlit, qui permet à un contribuable suisse de simuler l’économie d’impôt obtenue grâce à une cotisation au pilier 3a.

---

## 📁 Structure du dépôt

```
tax-savings-calculator/
│
├── calculations.py         # Logique de calcul des impôts
├── app.py                  # Interface Streamlit
├── data/
│   └── tax_params.json     # Barèmes fédéraux, cantonaux et communaux
├── requirements.txt        # Dépendances Python
├── .gitignore              # Fichiers ignorés par Git
└── README.md               # Documentation du projet
```

---

## 🛠️ Prérequis

- **Python 3.7+**  
- **pip**

---

## 🚀 Installation

1. **Cloner** le dépôt :  
   ```bash
   git clone https://github.com/<votre-utilisateur>/tax-savings-calculator.git
   cd tax-savings-calculator
   ```

2. **Installer** les dépendances :  
   ```bash
   pip install -r requirements.txt
   ```

---

## 🎯 Utilisation

Lancez l’application Streamlit :

```bash
streamlit run app.py
```

Dans l’interface web, renseignez :

1. **Votre NPA** (numéro postal suisse)  
2. **Revenu imposable annuel** (CHF)  
3. **Montant cotisé au pilier 3a** (CHF)  
4. **Profil fiscal** (état civil + nombre d’enfants)  
5. **Religion** (taxe d’église)  

Le simulateur affichera :

- **Impôt total sans pilier 3a**  
- **Impôt total avec pilier 3a**  
- **Économie d’impôt**

---

## 🎨 Personnalisation

- **Barèmes fiscaux** :  
  Mettez à jour `data/tax_params.json` pour modifier ou ajouter des profils fédéraux, cantonaux et communaux.

- **Import depuis Excel** :  
  Adaptez et lancez un script Python (ex. `excel_to_json.py`) pour régénérer automatiquement `tax_params.json` à partir de vos fichiers Excel.

---

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

---

## 🧑‍💻 Auteurs

Développé par *Votre Nom*. Contributions et améliorations bienvenues !

---

*Dernière mise à jour : juillet 2025*  
