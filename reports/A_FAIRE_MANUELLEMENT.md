# Ce qu’il reste à faire avant le rendu

Les étapes ci-dessous sont **[À FAIRE PAR L'ÉTUDIANT]**. Les résultats Python sont prêts ; les captures et mesures KNIME réelles n’ont pas été produites.

1. [ ] **Ouvrir `workflows/fraude-orange.ows` dans Orange.** Depuis la racine : `.\.venv-orange\Scripts\python.exe -m Orange.canvas`, puis File > Open. La recharge et le calcul offscreen ont été validés, mais vérifier la disposition et le calcul dans l’interface. Si File ne retrouve pas le CSV, Browse > `data/transactions.csv`, fraude target/categorical, nuit categorical, Apply. Suivre `guide_orange_manuel.md`.
2. [ ] **Faire les Captures 1 à 3 réelles.** Capture 1 : Test and Score après standardisation kNN et RF 100 arbres, Test on test data, cible 1, cinq scores. Capture 2 : Confusion Matrix, Gradient Boosting, axes et effectifs sur 1250 lignes. Capture 3 : workflow Orange complet avec tous les liens. Ne pas utiliser les figures matplotlib comme captures.
3. [ ] **Construire et exécuter le workflow KNIME réel** en suivant `guide_knime.md`, nœuds 1 à 12. Installer KNIME localement si nécessaire, sans démarrer depuis les scripts Python. Vérifier fraude nominale, partition 75 % stratifiée, graine 42, 3750/1250 lignes et 426/142 fraudes.
4. [ ] **Faire les Captures 4 et 5 réelles.** Capture 4 : workflow KNIME entier, tous les feux au vert. Capture 5 : meilleur Scorer réel, vue Confusion Matrix et Accuracy statistics, ligne 1 avec F-measure. Vérifier total matrice 1250, ligne réelle 0 = 1108 et ligne réelle 1 = 142.
5. [ ] **Relever les trois F1 KNIME réels**, avec précision, rappel, matrice et version. Remplir le tableau vide de `guide_knime.md`, remplacer la ligne KNIME simulée dans `comparatif.md` et la partie correspondante de `compte_rendu.md`. Conserver le rapport `knime_simulation_sklearn.md` comme simulation, sans le renommer en résultat KNIME. Adapter les conclusions à vos observations ; ne jamais attribuer un score Python à KNIME.
6. [ ] **Remplir « Temps humain »** dans les quatre lignes du comparatif et du compte rendu. Utiliser vos durées de manipulation, pas les 60 s de calcul FLAML.
7. [ ] **Exporter `workflows/tp-fraude.knwf`.** Space Explorer > clic droit sur tp-fraude > Export. Réimporter et vérifier chemins, réglages et résultats. Aucun .knwf n’a été généré automatiquement.
8. [ ] **Insérer les cinq captures et compléter l’identité.** Remplacer [NOM], [PRÉNOM], [FILIÈRE], [GROUPE]. Relire et reformuler les réponses avec vos observations. Si vous modifiez le Markdown, régénérer le Word avec `.\.venv\Scripts\python.exe scripts/cree_docx.py` ; attention, cette commande écrase le Word générique : conserver séparément toute version où vous avez déjà inséré vos captures. Le contrôle structurel se relance avec `scripts/valide_compte_rendu.py`.
9. [ ] **Vérifier visuellement toutes les pages, renommer et exporter.** Le rendu automatique Word n’a pas pu être vérifié : `LibreOffice soffice.exe was not found on PATH` (voir `rendu_word_limite.md`). Vérifier en particulier la table comparative en paysage, les sauts de page, tableaux, figures et légendes. Produire `Nom_Prénom_Filière_Groupe_TP_lowcode.pdf` ou `.docx` en remplaçant les champs par l’identité réelle. Ces fichiers personnels sont exclus de Git selon les règles demandées.

## Bonus facultatifs

- [ ] B1 : composant AutoML KNIME, exécution et capture réelles, sans score simulé ; guide en fin de `guide_knime.md`.
- [ ] B2 : copie Orange en CV stratifiée 5 plis sur File > Data ; capturer les résultats si le bonus est rendu.
- [ ] B3 : vérifier Predictions et ROC Analysis, cible 1 ; indiquer test fixe ou CV et avant/après. Après amélioration, Tree a la plus faible AUC ; avant, c’est kNN sur le test fixe.

## Préserver les modifications manuelles

Les scripts de synthèse reconstruisent les rapports depuis les JSON de mesures Python. Après remplacement par vos résultats KNIME réels, ne pas relancer `synthese.py`, `questions.py`, `compte_rendu.py` ou `reproduire.ps1` sur votre version finale sans conserver une copie : ils rétabliraient les mentions de simulation. Ajouter vos captures réelles dans figures/ avec des noms explicites, sans écraser les reproductions Python.

Après validation des ajouts manuels, versionner uniquement les éléments voulus : workflows/tp-fraude.knwf, rapports génériques et captures appropriées, jamais venv ou identité personnelle. Le compte rendu générique versionné doit garder les placeholders d’identité.
