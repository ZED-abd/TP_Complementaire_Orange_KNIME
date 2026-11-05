"""Référence FLAML supposée faute de dossier TP04 ; test externe préservé."""
import json
import time
import platform
import importlib.metadata
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from flaml import AutoML
from commun import ROOT, mesures, sauvegarde, provenance

def main():
    np.random.seed(42)
    df = pd.read_csv(ROOT / 'data/transactions.csv')
    X, y = df.drop(columns='fraude'), df.fraude
    train, test = train_test_split(np.arange(len(y)), test_size=.25, random_state=42)
    assert len(test) == 1250 and y.iloc[test].sum() == 134
    configuration = dict(time_budget=60, seed=42, task='classification', metric='f1',
                         n_jobs=1, verbose=2, log_file_name=str(ROOT / 'reports/flaml_recherche.log'))
    # Un journal par exécution, pas une concaténation d'anciennes recherches.
    (ROOT / 'reports/flaml_recherche.log').write_text('', encoding='utf-8')
    automl = AutoML()
    debut = time.perf_counter()
    automl.fit(X_train=X.iloc[train], y_train=y.iloc[train], **configuration)
    duree = time.perf_counter() - debut
    pred, prob = automl.predict(X.iloc[test]), automl.predict_proba(X.iloc[test])[:,1]
    m = mesures(y.iloc[test], pred, prob)
    assert np.array(m['matrice']).sum() == 1250
    assert np.array(m['matrice']).sum(axis=1).tolist() == [1116,134]
    result = {'provenance': provenance('simulation scikit-learn : exécution réelle FLAML sur estimateurs Python'),
              'flaml': importlib.metadata.version('flaml'),
              'hypothese': 'Dossier ../tp4-automl absent ; configuration supposée selon la consigne, pas un résultat récupéré du TP04.',
              'configuration': configuration, 'meilleur_modele': automl.best_estimator,
              'meilleure_configuration': automl.best_config,
              'perte_validation_interne': automl.best_loss, 'duree_secondes': duree,
              'machine': platform.processor(), 'partage': {'train':3750,'test':1250,'fraudes_test':134},
              'resultats': m}
    sauvegarde('flaml_resultats.json', result)
    pd.DataFrame({'indice_csv_base_0':test, 'fraude':y.iloc[test].to_numpy(),
                  'prediction':pred,'probabilite_1':prob}).to_csv(ROOT / 'reports/flaml_predictions.csv', index=False)
    texte = '# Référence FLAML exécutée\n\nProvenance : **simulation scikit-learn**, pilotée réellement par FLAML.\n\n'
    texte += result['hypothese'] + '\n\n'
    texte += f"FLAML {result['flaml']}, budget demandé 60 s, durée observée {duree:.3f} s, seed=42, task=classification, metric=f1, n_jobs=1. "
    texte += 'Partage externe 75/25 NON stratifié, random_state=42 : 1250 lignes de test dont 134 fraudes. '
    texte += 'Le test externe sert uniquement à l’évaluation finale ; le choix du modèle utilise la validation interne FLAML.\n\n'
    texte += f"Meilleur modèle : **{automl.best_estimator}**. F1 classe 1 externe **{m['F1']:.6f}**, AUC {m['AUC']:.6f}, "
    texte += f"précision {m['Prec']:.6f}, rappel {m['Recall']:.6f}, matrice `{m['matrice']}`.\n\n"
    texte += 'Configuration retenue :\n\n```json\n' + json.dumps(automl.best_config, indent=2) + '\n```\n\n'
    texte += 'Le budget temps, la charge et la machine changent le nombre d’essais et parfois le meilleur modèle, même avec seed=42. '
    texte += 'Aucun export MLflow n’a été réalisé dans ce TP complémentaire ; MLflow reste le format de référence du TP04/TP05 dans l’énoncé.\n'
    (ROOT / 'reports/flaml_reference.md').write_text(texte, encoding='utf-8')
    print(json.dumps(result, ensure_ascii=True, indent=2))

if __name__ == '__main__':
    main()
