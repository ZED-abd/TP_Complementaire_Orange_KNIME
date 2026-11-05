# Détection de fraude avec Orange et KNIME

TP complémentaire EMSI 5IASD. Objectif : comparer un workflow visuel Orange, un workflow KNIME à réaliser manuellement et une référence FLAML, avec F1 de la classe 1.

## Structure

`scripts/` : reproduction ; `data/` : transactions ; `workflows/` : workflows validés ; `models/` : modèle Orange ; `reports/` : résultats, analyses et guides ; `figures/` : reproductions Python, jamais des captures d’interface.

## Reproduction PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\Activate.ps1
python scripts/extrait_pdf.py
python scripts/donnees.py
```

Un second environnement `.venv-orange` est réservé à Orange (Python 3.11 ou supérieur). Les commandes des phases suivantes seront ajoutées après validation.

## État initial

Phase 0 : extraction et checklist. Phases 1 à 9 en préparation. Toutes les captures et exécutions KNIME réelles sont [À FAIRE PAR L'ÉTUDIANT]. Les valeurs attendues sont dans `reports/00_checklist.md` ; aucune mesure ML n’est encore revendiquée.
