"""SIMULATION scikit-learn, pas une mesure KNIME. Phase 4."""
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from commun import ROOT, mesures, sauvegarde, provenance, table_mesures, figure_matrice

def main():
    np.random.seed(42)
    df = pd.read_csv(ROOT / 'data/transactions.csv')
    X, y = df.drop(columns='fraude'), df.fraude
    train, test = train_test_split(np.arange(len(y)), test_size=.25, random_state=42, stratify=y)
    assert len(train) == 3750 and y.iloc[train].sum() == 426
    assert len(test) == 1250 and y.iloc[test].sum() == 142
    learners = {
        'Logistic Regression': LogisticRegression(max_iter=2000, random_state=42),
        'Random Forest': RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=1),
        'Gradient Boosting': GradientBoostingClassifier(n_estimators=100, max_depth=4, learning_rate=.1, random_state=42),
    }
    resultats, parametres = {}, {}
    predictions = pd.DataFrame({'indice_csv_base_0': test, 'fraude': y.iloc[test].to_numpy()})
    for nom, modele in learners.items():
        modele.fit(X.iloc[train], y.iloc[train])
        pred, prob = modele.predict(X.iloc[test]), modele.predict_proba(X.iloc[test])[:,1]
        m = mesures(y.iloc[test], pred, prob)
        assert np.array(m['matrice']).sum() == 1250
        assert np.array(m['matrice']).sum(axis=1).tolist() == [1108,142]
        resultats[nom], parametres[nom] = m, modele.get_params()
        predictions[nom + '_prediction'] = pred
        predictions[nom + '_probabilite_1'] = prob
        figure_matrice(m['matrice'], f'{nom} - simulation scikit-learn',
                       'figures/knime_simulation_' + nom.lower().replace(' ','_') + '.png')
    predictions.to_csv(ROOT / 'reports/knime_simulation_predictions.csv', index=False)
    sauvegarde('knime_simulation_resultats.json', {
        'provenance': provenance('simulation scikit-learn, pas une mesure KNIME'),
        'graine': 42, 'partage': {'train':3750,'fraudes_train':426,'test':1250,'fraudes_test':142},
        'parametres': parametres, 'resultats': resultats})
    texte = '# SIMULATION scikit-learn, pas une mesure KNIME\n\n'
    texte += 'Provenance : **simulation scikit-learn**. Aucun nœud KNIME n’a été exécuté. '
    texte += 'Partage stratifié 75/25, graine 42 : 3750 lignes dont 426 fraudes ; test 1250 dont 142 fraudes. '
    texte += 'Les indices et prédictions sont dans knime_simulation_predictions.csv ; versions et paramètres complets dans knime_simulation_resultats.json.\n\n'
    texte += 'Hypothèses : quatre attributs numériques, sans standardisation ajoutée ; LR avec max_iter=2000 pour convergence ; '
    texte += 'RF 100 arbres ; GB 100 arbres, profondeur 4, learning_rate=0.1 ; graines des trois modèles 42, un seul processus. '
    texte += 'Les algorithmes, encodages et lignes du partage peuvent différer des nœuds KNIME.\n\n'
    texte += table_mesures(resultats) + '\n\n'
    for nom, m in resultats.items():
        texte += f"- {nom} : matrice réelle/prédite [0,1] = `{m['matrice']}` ; total 1250, lignes réelles [1108,142] contrôlées.\n"
    texte += '\nL’énoncé indique 0,75 à 0,85 comme ordre de grandeur KNIME, pas comme égalité de validation. '
    texte += f"Notre LR simulée vaut {resultats['Logistic Regression']['F1']:.6f} : elle est sous cette plage indicative. "
    texte += 'La simulation conserve les attributs bruts, les paramètres sklearn explicites et son propre tirage de lignes ; '
    texte += 'elle ne reproduit pas l’optimiseur, les réglages internes ni le tirage exact de KNIME. '
    texte += 'L’identité des causes avec une future exécution KNIME ne peut pas être établie avant cette exécution ; aucune valeur n’est forcée.\n'
    texte += '\nLes F1 KNIME réels restent **[À FAIRE PAR L\'ÉTUDIANT]**, voir guide_knime.md.\n'
    (ROOT / 'reports/knime_simulation_sklearn.md').write_text(texte, encoding='utf-8')
    print(table_mesures(resultats))

if __name__ == '__main__':
    main()
