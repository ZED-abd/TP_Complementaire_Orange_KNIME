# Guide KNIME manuel

**[À FAIRE PAR L'ÉTUDIANT] : toutes les manipulations, exécutions, captures et valeurs KNIME réelles.**
Ce guide reprend les pages 9 à 12 du PDF local. Il n’atteste aucune exécution KNIME. Aucun fichier .knwf n’est fabriqué par Python. Les libellés des fenêtres peuvent varier entre versions 5.x.

## Préparation

1. Lancer KNIME manuellement ; ouvrir Modern UI si nécessaire, puis Home > Local space > Create workflow (+). Nommer `tp-fraude`.
2. Dans Nodes, rechercher chaque nœud ci-dessous et le glisser sur le canevas. Double-clic pour Configure, OK/Apply pour valider, F7 ou clic droit > Execute pour exécuter.
3. Rouge signifie à configurer, jaune signifie prêt, vert signifie exécuté. Ctrl+S régulièrement ; Maj+F7 pour Execute all.

## Nœuds 1 à 3 et contrôles des tables

**1 — CSV Reader.** Browse > sélectionner `data/transactions.csv` du dépôt. Séparateur virgule, première ligne comme en-tête. Vérifier l’aperçu : montant décimal, anciennete/freq_24h/nuit/fraude entiers. Exécuter puis ouvrir la table via le node monitor : 5000 lignes, 5 colonnes, aucune valeur manquante.

**2 — Number to String.** Relier le triangle de sortie de 1 au triangle d’entrée de 2. Dans la sélection des colonnes, inclure **uniquement fraude**, exclure les quatre attributs. Exécuter. Vérifier fraude de type String (S), catégories « 0 » et « 1 ». Ne pas transformer montant ni les autres attributs en texte.

**3 — Table Partitioner** (ancien nom Partitioning). Relier 2 > 3. Partition relative 75 %, méthode Stratified, colonne fraude, fixed random seed = 42. Exécuter. Sortie haute : 3750 lignes dont 426 fraudes ; sortie basse : 1250 dont 142 fraudes et 1108 non-fraudes. Lire les tables de sortie et compter les catégories avant de continuer. La même graine entre logiciels ne garantit pas les mêmes indices de lignes.

## Trois branches d’apprentissage

**4 — Logistic Regression Learner.** Relier la sortie haute du 3 à sa table d’entrée, Target column = fraude. Conserver les autres réglages par défaut et en noter les valeurs/version. Exécuter.

**5 — Logistic Regression Predictor.** Relier le modèle carré de 4 au port modèle carré de 5 ; la sortie basse du 3 au port table triangulaire de 5. Exécuter. Vérifier 1250 lignes et la nouvelle colonne `Prediction (fraude)`.

**6 — Scorer.** Relier la table de 5 à 6. First column = `fraude`, Second column = `Prediction (fraude)`. Exécuter. Clic droit > vue Confusion Matrix. Ouvrir le second port de sortie **Accuracy statistics** ; ligne **classe 1**, relever Precision, Recall et **F-measure**. Ce F-measure est le F1 fraude ; Overall Accuracy et la ligne classe 0 ne conviennent pas.

**7 — Random Forest Learner.** Relier la sortie haute du 3 au Learner. Target column = fraude ; Number of models = 100 ; **Use static random seed** coché, renseigner 42 si un champ de graine est proposé. Noter la valeur effective. Exécuter.

**8 — Random Forest Predictor.** Modèle carré de 7 vers entrée modèle ; sortie basse du 3 vers entrée table. Cocher **Append individual class confidences**. Exécuter. Contrôler 1250 lignes, Prediction (fraude) et les probabilités des deux classes.

**9 — Scorer.** Sortie de 8 vers 9, mêmes First/Second columns qu’au nœud 6. Exécuter et relever la ligne 1 d’Accuracy statistics ainsi que la matrice.

**10 — Gradient Boosted Trees Learner.** Sortie haute du 3 vers entrée table. Target column = fraude ; 100 modèles, profondeur maximale 4, learning rate = 0,1. Fixer 42 si une option de graine existe et noter les réglages. Exécuter.

**11 — Gradient Boosted Trees Predictor.** Modèle carré de 10 vers modèle, sortie basse du 3 vers table. Exécuter et vérifier 1250 prédictions.

**12 — Scorer.** Sortie de 11 vers 12 ; First column = fraude ; Second column = Prediction (fraude). Exécuter et relever matrice, Precision, Recall et F-measure de **classe 1**.

Pour chaque matrice, vérifier l’orientation des axes : ici on transcrit les lignes réelles puis les colonnes prédites, dans l’ordre 0,1. Total = 1250, ligne réelle 0 = 1108, ligne réelle 1 = 142. Un axe inversé doit être transposé avant comparaison.

## Tableau à remplir avec les mesures KNIME réelles

| Modèle | F1 classe 1 KNIME réel | Précision 1 | Rappel 1 | Matrice réelle [[TN,FP],[FN,TP]] | Version et réglages |
|---|---|---|---|---|---|
| Logistic Regression | [À REMPLIR] | [À REMPLIR] | [À REMPLIR] | [À REMPLIR] | [À REMPLIR] |
| Random Forest | [À REMPLIR] | [À REMPLIR] | [À REMPLIR] | [À REMPLIR] | [À REMPLIR] |
| Gradient Boosted Trees | [À REMPLIR] | [À REMPLIR] | [À REMPLIR] | [À REMPLIR] | [À REMPLIR] |

Les chiffres de `knime_simulation_sklearn.md` servent seulement de répétition Python. Les implémentations, le traitement des catégories et le tirage KNIME peuvent différer.

## Captures et export

- **Capture 4 [À FAIRE PAR L'ÉTUDIANT]** : afficher le workflow entier, nœuds 1 à 12, connexions lisibles, trois branches, tous les feux au vert.
- **Capture 5 [À FAIRE PAR L'ÉTUDIANT]** : ouvrir la Confusion Matrix du meilleur Scorer d’après le F1 réel et son Accuracy statistics ; montrer la ligne 1 et F-measure. Deux panneaux ou deux vues regroupées dans l’emplacement Capture 5 conviennent.
- Space Explorer > clic droit sur `tp-fraude` > Export > enregistrer **`workflows/tp-fraude.knwf`**. Réimporter pour vérifier. Le fichier exporte le workflow et ses réglages ; vérifier les chemins du CSV sur un autre poste.

## Dépannage

- Fraude absente de Target column ou nœud rouge : revenir au nœud 2, convertir seulement fraude en chaîne et réexécuter les nœuds dépendants.
- Lien refusé : carré = modèle, triangle = table ; relier chaque port au même type.
- F1 = 0 : vérifier la ligne classe 1, les colonnes du Scorer, les catégories produites par le Predictor et la présence de fraudes dans le train/test. Si le modèle prédit uniquement 0, le F1 fraude est réellement 0. Lire la ligne 0 donne une autre métrique, pas nécessairement zéro.
- Matrice à une seule colonne : vérifier qu’aucune prédiction n’a été perdue et que les deux classes sont présentes ; distinguer absence de prédictions 1 et mauvaise configuration du Scorer.
- KNIME ne démarre pas : fermer les applications gourmandes ; l’énoncé conseille 8 Go de RAM. Réaliser la partie sur un autre poste si nécessaire et le mentionner.

## Bonus B1 AutoML optionnel

**[À FAIRE PAR L'ÉTUDIANT]**, sans simulation et sans score inventé. D’après le PDF, rechercher « AutoML » sur le KNIME Community Hub, choisir le composant de classification publié par KNIME dans Examples > 00_Components > Automation (pas Regression), puis le glisser sur le canevas en nœud 13. Installer les extensions proposées et redémarrer si demandé. Relier la sortie du nœud 2 au composant : il effectue son propre partage stratifié 80/20. Cible fraude, classe positive 1, métrique F-measure si proposée. Désactiver Deep Learning (Keras) et H2O AutoML ; conserver LR, Decision Tree, RF, GB et XGBoost Trees. Exécuter, relever le classement et le meilleur score dans la vue du composant, faire une capture réelle. Facultativement relier Workflow Writer (nœud 14) et écrire `models/knime-automl`. Ne pas comparer directement ce score 80/20 au test 75/25. Si les extensions sont bloquées, omettre ce bonus.
