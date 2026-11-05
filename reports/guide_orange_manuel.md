# Guide Orange et vérification manuelle

**[À FAIRE PAR L'ÉTUDIANT] : ouvrir l’application, vérifier visuellement le workflow et produire les captures réelles.**
Le script de génération et son rapport de validation précisent si le fichier .ows a pu être livré. Une recharge sans interface ne remplace pas cette vérification graphique.

## Ouvrir ou reconstruire le workflow

Depuis PowerShell, à la racine du dépôt, lancer soi-même :

```powershell
.\.venv-orange\Scripts\python.exe -m Orange.canvas
```

File > Open > `workflows/fraude-orange.ows` s’il existe. Sinon New puis suivre les étapes ci-dessous. Si Orange demande de retrouver le CSV après déplacement du dépôt, choisir `data/transactions.csv`.

1. Poser **File**. Browse (…) > transactions.csv. Dans Columns, `fraude` : Role **target**, Type **categorical**, valeurs 0 et 1 ; `nuit` : categorical, feature ; montant, anciennete et freq_24h : numeric, feature. Apply. Relier File > Data Table et vérifier 5000 lignes, quatre attributs et une cible, sans valeurs manquantes. Ne pas inclure fraude dans les attributs.
2. File > **Data Sampler**. Fixed proportion of data = **75 %**, Replicable (deterministic) sampling et Stratify sample (when possible) cochés. Sample Data. Vérifier 3750 / 1250.
3. Poser **Test and Score**. Relier Data Sampler **Data Sample > Data**, puis un second lien **Remaining Data > Test Data**. Dans Edit Links, vérifier les deux entrées. Sélectionner **Test on test data**, puis **Evaluation results for target = 1**.
4. Poser Logistic Regression, kNN, Tree, Random Forest, Gradient Boosting. Relier leurs sorties **Learner** à l’entrée **Learner** de Test and Score. Au départ conserver les réglages des widgets ; Random Forest : **Replicable training** coché, 10 arbres. GB : méthode Gradient Boosting scikit-learn, pas XGBoost/CatBoost. Attendre la fin du calcul et relever les cinq scores avant amélioration.
5. Poser **Preprocess**. Glisser **Normalize Features** dans la liste active, Standardize to μ=0, σ²=1. Relier **Preprocessor > Preprocessor** à kNN, sans normaliser le CSV complet avant le partage. Le prétraitement doit être appris dans chaque entraînement. Passer Random Forest à **100 arbres**, Replicable toujours coché. Relever les cinq lignes après amélioration.
6. Test and Score > **Confusion Matrix**. Choisir **Gradient Boosting**. Lignes réelles, colonnes prédites ; sélectionner les effectifs, pas les pourcentages. Contrôler total 1250 et ligne fraude 142.
7. Data Sampler **Data Sample > Data** de Gradient Boosting. Sa sortie **Model > Model** de **Save Model**. Save as > `models/fraude-gb.pkcls`. Ne pas entraîner le modèle sauvegardé sur les 5000 lignes si l’on veut reproduire le modèle du test fixe.
8. Gradient Boosting **Model > Predictors** de **Predictions** ; Data Sampler **Remaining Data > Data** de Predictions. Vérifier 1250 lignes, prédiction et probabilité de classe 1.
9. Test and Score **Evaluation Results > Evaluation Results** de **ROC Analysis**. Target = **1**. Montrer les cinq modèles et leurs courbes. Une figure matplotlib du dépôt reste une reproduction Python et ne remplace pas la capture du widget.
10. File > Save As > `workflows/fraude-orange.ows`. Sauvegarder régulièrement après réglages.

## Captures 1 à 3

- **[À FAIRE PAR L'ÉTUDIANT] Capture 1** : Test and Score **après** standardisation kNN et RF 100 arbres, cible 1, protocole Test on test data et cinq lignes avec AUC, CA, F1, Prec, Recall. Faire apparaître les effectifs 3750/1250 si le widget les affiche.
- **[À FAIRE PAR L'ÉTUDIANT] Capture 2** : Confusion Matrix, Gradient Boosting sélectionné, les quatre effectifs, axes et classes 0/1, total 1250.
- **[À FAIRE PAR L'ÉTUDIANT] Capture 3** : canevas complet avec File, Data Table, Sampler, cinq Learners, Preprocess, Test and Score, Confusion Matrix, Save Model, Predictions, ROC Analysis et connexions lisibles.

## B2 Validation croisée

Faire une copie du workflow, par exemple `fraude-orange-cv.ows`, pour garder le test fixe. Retirer le lien Data Sample > Data de Test and Score ; relier **File > Data**. Retirer Remaining Data > Test Data pour éviter un test présent mais inutilisé. Choisir **Cross validation**, **5 plis**, **Stratified** coché, Target 1. Conserver les modèles après amélioration pour B2, et relever les scores. Le rapport fournit aussi la version avant amélioration pour lever toute ambiguïté. Ne pas brancher un prétraitement ajusté sur tout le jeu avant la validation croisée.

## B3 et dépannage

La ROC peut être observée sur le test fixe ou sur la CV : indiquer le protocole dans la légende. Ne pas mélanger les deux AUC. La courbe d’un modèle peut croiser une autre : « la plus basse » signifie ici la plus faible AUC globale.

- « Test data is present but unused » : sélectionner Test on test data, ou retirer le test pour B2.
- MSE/RMSE à la place du F1 : fraude est restée numérique ; revenir dans File, categorical + target, Apply.
- Triangle jaune : survoler le widget et lire le message avant de poursuivre.
- Info de File indique encore « no target » : vérifier le rôle dans Columns et le domaine transmis ; l’Info peut décrire le fichier brut.
- Scores différents : noter versions Orange/scikit-learn, type de nuit, cibles, graines, paramètres et protocole. Conserver les valeurs réellement observées.
