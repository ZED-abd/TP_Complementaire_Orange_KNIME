# Checklist issue de l’énoncé

Source : `TP_Complementaire_Orange_KNIME.pdf`, 15 pages, extraction intégrale dans `enonce_texte.txt`.
Les valeurs ci-dessous sont des **valeurs attendues de l’énoncé, non reproduites à ce stade**.

## Livrables et identité

- Compte rendu PDF ou Word, Captures 1 à 5, tableau comparatif et conclusion en cinq lignes, Questions 1 à 6.
- Workflow Orange `workflows/fraude-orange.ows` et workflow KNIME `workflows/tp-fraude.knwf`.
- Modèle `models/fraude-gb.pkcls` et données `data/transactions.csv`.
- Bonus facultatifs : AutoML KNIME B1, validation croisée B2, Predictions et ROC B3.
- Nom imposé : `Nom_Prénom_Filière_Groupe_TP_lowcode.pdf` ou `.docx`.
- Identité de la version Git : [NOM], [PRÉNOM], [FILIÈRE], [GROUPE].

## Contrôles et valeurs attendues

| Étape | Attendu de l’énoncé |
|---|---|
| Annexe A | 5001 lignes avec en-tête, 5000 transactions, 568 fraudes, 11,36 %, graine 7 |
| 1.1 | 5 colonnes au total, 4 attributs et 1 cible ; nuit catégorielle ; fraude cible catégorielle 0/1 ; aucune valeur manquante |
| 1.2 | Data Sampler 75 %, replicable et stratifié ; 3750 apprentissage, 1250 test ; RF replicable ; Test on test data, target 1 |
| 1.3 | kNN standardisé ; RF de 10 à 100 arbres ; sauvegarde GB, environ 320 Ko annoncés |
| 2.1 | CSV Reader 5000 × 5 ; Number to String convertit uniquement fraude en chaîne 0/1 |
| 2.2 | Partition 75 % stratifiée, graine 42 ; 3750 dont 426 fraudes et 1250 dont 142 fraudes ; trois Learners/Predictors |
| 2.3 | Scorer : fraude versus Prediction (fraude) ; matrice total 1250 ; lignes réelles 0=1108 et 1=142 ; F1 classe 1 d’ordre 0,75 à 0,85, sans score KNIME imposé |
| 2.4 | Export du workflow KNIME au format .knwf |
| B2 | CV stratifiée 5 plis sur 5000 lignes ; GB F1 0,818 ; LR F1 0,744 |
| B3 | Predictions sur 1250 lignes ; ROC des cinq modèles, cible 1 pour nos mesures ; capture illustrative de l’énoncé en cible 0 |

| Modèle Orange avant | AUC | CA | F1 classe 1 | Précision | Rappel |
|---|---|---|---|---|---|
| Logistic Regression | 0,979 | 0,952 | 0,781 | 0,811 | 0,754 |
| kNN | 0,825 | 0,904 | 0,478 | 0,625 | 0,387 |
| Tree | 0,845 | 0,950 | 0,756 | 0,857 | 0,676 |
| Random Forest | 0,977 | 0,958 | 0,813 | 0,831 | 0,796 |
| Gradient Boosting | 0,989 | 0,965 | 0,837 | 0,883 | 0,796 |
| kNN standardisé après | 0,964 | 0,951 | 0,780 | 0,800 | 0,761 |
| RF 100 arbres après | 0,984 | 0,963 | 0,833 | 0,858 | 0,810 |

Matrice GB attendue, lignes réelles 0 puis 1, colonnes prédites 0 puis 1 : `[[1093,15],[29,113]]`.
FLAML TP04 : recherche 60 s, test non stratifié 1250 dont 134 fraudes. TP2 : F1 0,8669, valeur attendue de l’énoncé, non reproduite.
Attention : « 5 features » dans le texte de l’étape 1.1 désigne les cinq colonnes ; le modèle utilise quatre attributs, sans la cible.

## Questions obligatoires

1. Exactitude ou F1 : déséquilibre, distances kNN, normalisation.
2. Reproductibilité : pourquoi fixer les graines ; équivalents KNIME, scikit-learn, FLAML.
3. Coût des erreurs : faux négatifs, fausses alertes et seuil.
4. Cible : Number to String et équivalent Orange ; conséquences d’une cible numérique.
5. Exécution : Orange automatique ; KNIME explicite, feux et Learner/Predictor ; débutant et entreprise.
6. Intérêt des outils visuels face au code/FLAML ; éléments manquants pour la production TP05.

## Captures réelles restant à produire

- [À FAIRE PAR L'ÉTUDIANT] Capture 1 : Test and Score après amélioration, cible 1, cinq modèles et scores.
- [À FAIRE PAR L'ÉTUDIANT] Capture 2 : matrice de confusion GB sur 1250 lignes.
- [À FAIRE PAR L'ÉTUDIANT] Capture 3 : workflow Orange complet et lisible.
- [À FAIRE PAR L'ÉTUDIANT] Capture 4 : workflow KNIME complet, tous les feux verts.
- [À FAIRE PAR L'ÉTUDIANT] Capture 5 : Confusion Matrix et Accuracy statistics, ligne classe 1, meilleur Scorer KNIME réel.

## Validation de phase 0

Le PDF fourni a été lu intégralement. Les répertoires, le .gitignore et le README sont présents. Aucun chiffre de cette checklist ne constitue une mesure d’exécution.
