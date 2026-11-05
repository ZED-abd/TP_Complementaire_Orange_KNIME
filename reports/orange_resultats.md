# Résultats Orange

Provenance de toutes les mesures : **Orange (API Python)**. Orange 3.40.0, scikit-learn 1.9.1, NumPy 2.3.5. Aucun widget graphique piloté et aucune capture revendiquée. Les sources installées et leurs SHA-256 sont archivés dans orange_sources_installees.md et orange_sources_manifest.json.

## Protocole et audit des réglages

Domaine explicite : fraude cible catégorielle 0/1 ; nuit catégorielle ; trois autres attributs continus. OWDataSampler.RandomSeed=42 ; SampleRandomP(.75) passe 3750 comme test_size à StratifiedShuffleSplit puis nomme ce second sous-ensemble Data Sample. On utilise cette classe directement : inverser simplement train_test_split(test_size=.25) ne reproduit pas les mêmes lignes, même à graine 42. 3750 apprentissage dont 426 fraudes ; 1250 test dont 142 fraudes.

LR : C=1, L2, max_iter=10000, random_state=0, solver auto (lbfgs), prétraitements par défaut sans standardisation ajoutée. kNN : 5 voisins, distance euclidienne, poids uniformes ; après amélioration NormalizeBySD appris sur le train seulement, puis prétraitements par défaut (use_default_preprocessors=True comme OWBaseLearner pour Fitter). Tree Orange natif : binarize=True, feuille minimale 2, split minimal 5, profondeur 100, majorité suffisante .95 ; il ne faut pas le remplacer par DecisionTreeClassifier par défaut. RF : 10 puis 100 arbres, random_state=0 quand Replicable est coché, min_samples_split=5, max_features=sqrt. GB : méthode scikit-learn, 100 arbres, learning_rate=.1, max_depth=3, subsample=1, min_samples_split=2, random_state=0 (Replicable activé par défaut). TestAndScore utilise TestOnTestData ; CV utilise random_state=42. Save Model utilise pickle.dump sans protocole explicitement modifié.

## Étape 1.2 avant amélioration

| Modèle | AUC | CA | F1 classe 1 | Précision 1 | Rappel 1 |
|---|---|---|---|---|---|
| Logistic Regression | 0.979426 | 0.952000 | 0.781022 | 0.810606 | 0.753521 |
| kNN | 0.825183 | 0.904000 | 0.478261 | 0.625000 | 0.387324 |
| Tree | 0.845109 | 0.950400 | 0.755906 | 0.857143 | 0.676056 |
| Random Forest | 0.976617 | 0.958400 | 0.812950 | 0.830882 | 0.795775 |
| Gradient Boosting | 0.989078 | 0.964800 | 0.837037 | 0.882812 | 0.795775 |

## Étape 1.3 après amélioration

| Modèle | AUC | CA | F1 classe 1 | Précision 1 | Rappel 1 |
|---|---|---|---|---|---|
| Logistic Regression | 0.979426 | 0.952000 | 0.781022 | 0.810606 | 0.753521 |
| kNN | 0.964137 | 0.951200 | 0.779783 | 0.800000 | 0.760563 |
| Tree | 0.845109 | 0.950400 | 0.755906 | 0.857143 | 0.676056 |
| Random Forest | 0.983971 | 0.963200 | 0.833333 | 0.858209 | 0.809859 |
| Gradient Boosting | 0.989078 | 0.964800 | 0.837037 | 0.882812 | 0.795775 |

| Mesure | Mesuré | Attendu de l’énoncé | Écart signé | Explication |
|---|---|---|---|---|
| F1 Logistic Regression | 0.781022 | 0.781 | +0.000022 | Compatible avec l’arrondi à trois décimales |
| F1 kNN | 0.478261 | 0.478 | +0.000261 | Compatible avec l’arrondi à trois décimales |
| F1 Tree | 0.755906 | 0.756 | -0.000094 | Compatible avec l’arrondi à trois décimales |
| F1 Random Forest | 0.812950 | 0.813 | -0.000050 | Compatible avec l’arrondi à trois décimales |
| F1 Gradient Boosting | 0.837037 | 0.837 | +0.000037 | Compatible avec l’arrondi à trois décimales |
| F1 kNN standardisé | 0.779783 | 0.780 | -0.000217 | Compatible avec l’arrondi à trois décimales |
| F1 Random Forest 100 | 0.833333 | 0.833 | +0.000333 | Compatible avec l’arrondi à trois décimales |
| F1 CV Gradient Boosting | 0.818011 | 0.818 | +0.000011 | Scores Orange agrégés hors pli ; moyenne des F1 par pli également enregistrée |
| F1 CV Logistic Regression | 0.743786 | 0.744 | -0.000214 | Scores Orange agrégés hors pli ; moyenne des F1 par pli également enregistrée |

Tous les écarts AUC/CA/F1/précision/rappel sont aussi dans orange_comparaison_scores.csv ; les attendus ne sont jamais substitués aux mesures.

Matrice GB mesurée : `[[1093, 15], [29, 113]]` ; attendue de l’énoncé : `[[1093,15],[29,113]]`. Écart élément par élément : `[[0, 0], [0, 0]]`. Modèle sauvegardé : 141461 octets ; recharge pickle et prédictions identiques validées. L’énoncé annonce environ 320 Ko : notre fichier est plus petit. Le format est bien pickle.dump comme OWSaveModel.do_save, les paramètres sont fidèles et les prédictions sont identiques après recharge. La représentation sérialisée dépend des bibliothèques ; la cause exacte de cet écart de taille n’est pas établie. Aucun remplissage artificiel n’est ajouté.

## B2 CV stratifiée 5 plis

| Modèle | F1 avant agrégé | F1 après agrégé | Moyenne F1 après par pli |
|---|---|---|---|
| Logistic Regression | 0.743786 | 0.743786 | 0.742697 |
| kNN | 0.459259 | 0.780261 | 0.780229 |
| Tree | 0.703476 | 0.703476 | 0.702587 |
| Random Forest | 0.806922 | 0.819343 | 0.819262 |
| Gradient Boosting | 0.818011 | 0.818011 | 0.818148 |

Chaque ligne est validée une fois hors pli ; 4000 lignes entraînent chaque modèle. Le F1 affiché par Orange est calculé sur les prédictions hors pli regroupées, et n’est pas exactement la moyenne des cinq F1. Les deux sont conservés.

## B3 ROC et seuil pédagogique

Sur le test fixe avant, la plus faible AUC est celle de kNN (0.825183). Sur le test fixe apres, la plus faible AUC est celle de Tree (0.845109). Les courbes peuvent se croiser ; l’AUC mesure le classement global. Les figures ROC avant/après et CV sont légendées reproduction Python.

Seuil GB abaissé de .5 à .3, choisi a priori pour illustrer le compromis (pas optimisé sur le test) : matrice `[[1078, 30], [16, 126]]`, F1 0.845638, précision 0.807692, rappel 0.887324. Il s’agit d’une illustration sur le test, pas d’une preuve de gain en production. Choisir un seuil métier sur validation avec coûts explicites et tester ensuite sur un jeu indépendant.
