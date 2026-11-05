# Référence FLAML exécutée

Provenance : **simulation scikit-learn**, pilotée réellement par FLAML.

Dossier ../tp4-automl absent ; configuration supposée selon la consigne, pas un résultat récupéré du TP04.

FLAML 2.7.0, budget demandé 60 s, durée observée 60.578 s, seed=42, task=classification, metric=f1, n_jobs=1. Partage externe 75/25 NON stratifié, random_state=42 : 1250 lignes de test dont 134 fraudes. Le test externe sert uniquement à l’évaluation finale ; le choix du modèle utilise la validation interne FLAML.

Meilleur modèle : **xgboost**. F1 classe 1 externe **0.858238**, AUC 0.990973, précision 0.881890, rappel 0.835821, matrice `[[1101, 15], [22, 112]]`.

Configuration retenue :

```json
{
  "n_estimators": 333,
  "max_leaves": 4,
  "min_child_weight": 0.06115052475933034,
  "learning_rate": 0.17876820421463074,
  "subsample": 0.7335343083405597,
  "colsample_bylevel": 0.6874325202145412,
  "colsample_bytree": 0.9715496137104597,
  "reg_alpha": 0.0022084629913922114,
  "reg_lambda": 2.4407106398739207
}
```

Le budget temps, la charge et la machine changent le nombre d’essais et parfois le meilleur modèle, même avec seed=42. Aucun export MLflow n’a été réalisé dans ce TP complémentaire ; MLflow reste le format de référence du TP04/TP05 dans l’énoncé.
