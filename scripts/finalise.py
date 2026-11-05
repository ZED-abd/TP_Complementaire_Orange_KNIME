"""Phase 9 : README, inventaire et journal de validation en français."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    o=json.loads((ROOT/'reports/orange_resultats.json').read_text(encoding='utf-8'))
    f=json.loads((ROOT/'reports/flaml_resultats.json').read_text(encoding='utf-8'))
    k=json.loads((ROOT/'reports/knime_simulation_resultats.json').read_text(encoding='utf-8'))
    texte='''# Détection de fraude avec Orange et KNIME

TP complémentaire EMSI 5IASD. Objectif : construire et comprendre un workflow ML visuel, évaluer le **F1 de la classe 1 (fraude)**, comparer Orange, KNIME et une référence FLAML, et conserver des preuves reproductibles.

## Structure du dépôt

| Chemin | Contenu |
|---|---|
| TP_Complementaire_Orange_KNIME.pdf | Énoncé fourni, 15 pages |
| scripts/ | Extraction, données, mesures, workflow, synthèse, Word et validations |
| data/transactions.csv | Annexe A, 5000 transactions et 568 fraudes |
| workflows/fraude-orange.ows | Workflow généré, rechargé et exécuté en offscreen |
| models/fraude-gb.pkcls | Vrai modèle Orange, format Save Model, recharge contrôlée |
| reports/ | Compte rendu générique, résultats JSON/CSV/Markdown, sources Orange et guides |
| figures/ | Reproductions Python, jamais des captures d’interface |
| requirements.txt | Versions figées de .venv, Python 3.13.3 lors de l’exécution |
| requirements-orange.txt | Versions figées de .venv-orange, Orange 3.40.0 |

Le Word `reports/Nom_Prénom_Filière_Groupe_TP_lowcode.docx` est généré localement et ignoré par Git comme demandé. Le Markdown et son générateur sont versionnés. L’export KNIME `workflows/tp-fraude.knwf` reste à réaliser manuellement.

## Reproduction PowerShell

Utiliser Python 3.13 pour reproduire ces verrous de versions (Orange exige au moins 3.11). Installer les paquets uniquement dans les deux venv. Prévoir plusieurs Go libres. Depuis la racine du dépôt :

```powershell
python -m venv .venv
python -m venv .venv-orange
.\\.venv\\Scripts\\python.exe -m pip install --no-cache-dir -r requirements.txt
.\\.venv-orange\\Scripts\\python.exe -m pip install --no-cache-dir -r requirements-orange.txt
.\\.venv\\Scripts\\Activate.ps1
python scripts/extrait_pdf.py
python scripts/donnees.py
$env:QT_QPA_PLATFORM = 'offscreen'
$env:PYTHONUTF8 = '1'
.\\.venv-orange\\Scripts\\python.exe scripts/audit_orange.py
.\\.venv-orange\\Scripts\\python.exe scripts/orange_experiences.py
.\\.venv-orange\\Scripts\\python.exe scripts/workflow_orange.py
.\\scripts\\verifie_knime.ps1
python scripts/knime_simulation_sklearn.py
python scripts/flaml_reference.py
python scripts/synthese.py
python scripts/questions.py
python scripts/compte_rendu.py
python scripts/cree_docx.py
python scripts/valide_compte_rendu.py
python scripts/valide_livrables.py
python scripts/finalise.py
```

Si l’activation PowerShell est refusée, utiliser les chemins explicites vers python.exe ; l’activation n’est pas nécessaire. Une autre possibilité est `Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned`, uniquement pour le processus courant.

Pour relancer toute la chaîne sans activation :

```powershell
.\\scripts\\reproduire.ps1
# Ou avec les environnements déjà installés :
.\\scripts\\reproduire.ps1 -SansInstallation
```

**Attention aux versions manuelles** : les scripts reconstruisent les rapports et le Word génériques. Après insertion des captures ou des résultats KNIME réels, conserver une copie avant de relancer la chaîne. FLAML peut sélectionner une autre configuration à budget temps égal : ce résultat dépend de la machine, même avec seed=42. La validation compare les prédictions de l’exécution courante à ses propres JSON, sans imposer le score FLAML historique.

## État d’avancement

| Phase | État et validation |
|---|---|
| 0 Lecture et structure | Fait : PDF extrait intégralement et checklist |
| 1 Données | Fait : 5001 lignes, 568 fraudes, SHA-256 archivé |
| 2 Orange API | Fait : 35 métriques conformes à l’arrondi de l’énoncé, matrice exacte, CV et ROC |
| 3 Workflow Orange | Fait en offscreen : 14 widgets, 16 liens, recharge et cinq F1 identiques ; contrôle visuel manuel |
| 4 KNIME | Simulation scikit-learn et guide faits ; exécution réelle, captures et .knwf manuels |
| 5 FLAML | Recherche réelle de 60 s terminée ; configuration TP04 supposée |
| 6 Synthèse | Fait : comparatif et conclusion de cinq lignes ; temps humain à remplir |
| 7 Questions | Fait : Q1–Q6 et B2–B3 entre 120 et 200 mots |
| 8 Compte rendu | Markdown et Word créés ; structure validée ; rendu visuel non validé faute LibreOffice |
| 9 Guide final | Fait : reports/A_FAIRE_MANUELLEMENT.md, inventaire et validation finale |

## Mesuré et attendu

Toutes les valeurs Orange ci-dessous sont de provenance **Orange (API Python)**. Les attendus viennent de l’énoncé. Écart signé = mesuré moins attendu ; les différences sont compatibles avec l’arrondi à trois décimales.

| F1 classe 1 | Mesuré | Attendu | Écart signé |
|---|---|---|---|
'''
    lignes=[('LR avant',o['avant']['Logistic Regression']['F1'],.781),('kNN avant',o['avant']['kNN']['F1'],.478),
            ('Tree avant',o['avant']['Tree']['F1'],.756),('RF 10',o['avant']['Random Forest']['F1'],.813),
            ('GB',o['avant']['Gradient Boosting']['F1'],.837),('kNN standardisé',o['apres']['kNN']['F1'],.780),
            ('RF 100',o['apres']['Random Forest']['F1'],.833),('GB CV 5 plis',o['cv']['apres']['Gradient Boosting']['F1'],.818),
            ('LR CV 5 plis',o['cv']['apres']['Logistic Regression']['F1'],.744)]
    for nom,val,att in lignes:
        texte+=f'| {nom} | {val:.6f} | {att:.3f} | {val-att:+.6f} |\n'
    texte+='\nMatrice GB mesurée et attendue : **[[1093,15],[29,113]]**, écart nul. '
    texte+=f"FLAML : **{f['meilleur_modele']}**, F1 **{f['resultats']['F1']:.6f}**, provenance simulation scikit-learn, pilotage FLAML réellement exécuté ; aucun F1 TP04 précis imposé par l’énoncé. "
    texte+=f"KNIME simulé : LR {k['resultats']['Logistic Regression']['F1']:.6f}, RF {k['resultats']['Random Forest']['F1']:.6f}, GB {k['resultats']['Gradient Boosting']['F1']:.6f}, provenance **simulation scikit-learn, pas une mesure KNIME**. La LR simulée est sous la plage indicative KNIME de l’énoncé et reste conservée.\n\n"
    texte+='## Hypothèses et limites\n\n'
    texte+='Voir `reports/hypotheses_et_limites.md` pour le détail. Données graine 7 ; Orange Sampler/CV 42 et modèles LR/RF/GB 0 ; simulation KNIME et FLAML 42. '
    texte+='La source du sampler Orange a été utilisée directement : ses lignes diffèrent d’un simple train_test_split(test_size=.25), même à graine identique. '
    texte+='Le modèle sérialisé pèse 141461 octets, contre environ 320 Ko annoncés ; format et prédictions corrects, cause précise de l’écart de taille non établie. '
    texte+='Le test FLAML contient 134 fraudes et les tests Orange/simulation KNIME 142 : comparer des ordres de grandeur, sans conclure sur 1 à 2 centièmes. '
    texte+='Le rendu Word a échoué avec `LibreOffice soffice.exe was not found on PATH` ; vérifier manuellement toutes les pages. '
    texte+='Aucune capture réelle ni exécution KNIME n’est revendiquée. B1 reste un guide optionnel.\n\n'
    texte+='## Avant de rendre\n\n'
    texte+='Suivre **[reports/A_FAIRE_MANUELLEMENT.md](reports/A_FAIRE_MANUELLEMENT.md)** : vérifier Orange, produire les Captures 1–3, construire KNIME, produire les Captures 4–5, remplacer les scores simulés, remplir temps humain et identité, exporter le vrai .knwf, relire et exporter le compte rendu. '
    texte+='Le nom de rendu imposé est Nom_Prénom_Filière_Groupe_TP_lowcode.pdf ou .docx. Le compte rendu générique commité conserve les placeholders d’identité.\n\n'
    texte+='## Git et contrôles\n\n'
    texte+='Le dossier initial a été initialisé sur main ; le distant était vide. Un commit par phase est créé après validation ou documentation explicite d’un écart. Aucun historique réécrit, aucun push forcé. '
    texte+='Les venv, caches et comptes rendus portant le nom personnel sont ignorés. Les preuves sont dans reports/validation_finale.json, reports/journal_validation.md et les prédictions CSV. '
    texte+='Consulter `git log --oneline`, `git status` et `git status -sb` pour l’état courant.\n'
    (ROOT/'README.md').write_text(texte,encoding='utf-8')
    entrees=[]
    for dossier in ['scripts','data','workflows','models','reports','figures']:
        for path in sorted((ROOT/dossier).glob('*')):
            if path.is_file():
                statut='local, ignoré par Git' if path.suffix=='.docx' else 'livrable ou preuve générique'
                entrees.append(f'- `{path.relative_to(ROOT).as_posix()}` — {statut}')
    if not any('reports/fichiers_livres.md' in ligne for ligne in entrees):
        entrees.append('- `reports/fichiers_livres.md` — présent inventaire générique')
    (ROOT/'reports/fichiers_livres.md').write_text('# Inventaire des fichiers produits\n\n'+
        'À la racine : README.md, requirements.txt, requirements-orange.txt, .gitignore, .gitattributes et PDF fourni.\n\n'+
        '\n'.join(entrees)+'\n\nLe .knwf et les cinq captures réelles restent à créer par l’étudiant.\n',encoding='utf-8')
    print('README et inventaire mis à jour.')

if __name__=='__main__':
    main()
