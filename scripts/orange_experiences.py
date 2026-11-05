"""Phase 2 : Orange API, paramètres fidèles aux sources des widgets 3.40.

Exécuter dans .venv-orange. Aucun pilotage d'interface graphique.
"""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import pickle
import random
import numpy as np
import pandas as pd
import Orange
from Orange.data import Table, Domain, ContinuousVariable, DiscreteVariable
from Orange.classification import LogisticRegressionLearner
from Orange.modelling import KNNLearner, TreeLearner, RandomForestLearner, GBLearner
from Orange.preprocess import Normalize
from Orange.widgets.data.owdatasampler import SampleRandomP, OWDataSampler
from commun import (ROOT, mesures, sauvegarde, provenance, table_mesures, figure_matrice)

ATTENDUS = {
    'Logistic Regression':[.979,.952,.781,.811,.754], 'kNN':[.825,.904,.478,.625,.387],
    'Tree':[.845,.950,.756,.857,.676], 'Random Forest':[.977,.958,.813,.831,.796],
    'Gradient Boosting':[.989,.965,.837,.883,.796],
    'kNN standardisé':[.964,.951,.780,.800,.761], 'Random Forest 100':[.984,.963,.833,.858,.810]}

def charger_donnees():
    df = pd.read_csv(ROOT / 'data/transactions.csv')
    domain = Domain([ContinuousVariable('montant'), ContinuousVariable('anciennete'),
                     ContinuousVariable('freq_24h'), DiscreteVariable('nuit', values=('0','1'))],
                    DiscreteVariable('fraude', values=('0','1')))
    data = Table.from_numpy(domain, df[['montant','anciennete','freq_24h','nuit']].to_numpy(),
                            df.fraude.to_numpy())
    assert len(data) == 5000 and data.domain.has_discrete_class
    assert data.domain['nuit'].is_discrete and not data.has_missing()
    return data

def learners(ameliore=False):
    # OWLogisticRegression C_s[61]=1 ; solver auto->lbfgs, sans normalisation ajoutée.
    modeles = {
        'Logistic Regression': LogisticRegressionLearner(penalty='l2', dual=False, tol=.0001, C=1,
            class_weight=None, fit_intercept=True, intercept_scaling=1., max_iter=10000, random_state=0),
        'kNN': KNNLearner(n_neighbors=5, metric='euclidean', weights='uniform',
            preprocessors=Normalize(norm_type=Normalize.NormalizeBySD) if ameliore else None),
        'Tree': TreeLearner(max_depth=100, min_samples_split=5, min_samples_leaf=2,
            binarize=True, sufficient_majority=.95),
        'Random Forest': RandomForestLearner(n_estimators=100 if ameliore else 10,
            random_state=0, min_samples_split=5),
        'Gradient Boosting': GBLearner(n_estimators=100, learning_rate=.1, random_state=0,
            max_depth=3, subsample=1, min_samples_split=2),
    }
    for nom, learner in modeles.items():
        if nom != 'Logistic Regression':
            # OWBaseLearner.update_learner le fait pour les Fitter.
            learner.use_default_preprocessors = True
        learner.name = nom
    return modeles

def evaluer(train, test, modeles):
    res = Orange.evaluation.TestOnTestData(store_data=True, store_models=True)(train,test,list(modeles.values()))
    erreurs = [str(e) for e in res.failed if e]
    if erreurs:
        raise RuntimeError(erreurs)
    scores = {}
    for i, nom in enumerate(modeles):
        m = mesures(res.actual, res.predicted[i], res.probabilities[i,:,1])
        # Contrôle indépendant de nos appels sklearn contre les scores Orange cible 1.
        for cle, score in [('AUC',Orange.evaluation.AUC),('F1',Orange.evaluation.F1),
                           ('Prec',Orange.evaluation.Precision),('Recall',Orange.evaluation.Recall)]:
            assert np.isclose(m[cle], score(res,target=1)[i])
        assert np.isclose(m['CA'], Orange.evaluation.CA(res)[i])
        assert np.array(m['matrice']).sum(axis=1).tolist() == [1108,142]
        scores[nom] = m
    return scores, res

def courbes(res, noms, fichier, protocole):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from sklearn.metrics import roc_curve, roc_auc_score
    fig, ax = plt.subplots(figsize=(7.4,5.4))
    for i, nom in enumerate(noms):
        prob = res.probabilities[i,:,1]
        fpr,tpr,_ = roc_curve(res.actual,prob,pos_label=1)
        ax.plot(fpr,tpr,label=f'{nom} (AUC={roc_auc_score(res.actual,prob):.3f})')
    ax.plot([0,1],[0,1],'k--',linewidth=.8)
    ax.set(xlabel='Taux de faux positifs',ylabel='Rappel de la classe 1',
           title=f'Orange (API Python) - {protocole}',xlim=(0,1),ylim=(0,1.01))
    ax.legend(loc='lower right',fontsize=9)
    fig.text(.5,.015,'Reproduction Python, ne remplace pas la capture',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.04,1,1)); fig.savefig(ROOT / fichier,dpi=180); plt.close(fig)

def main():
    np.random.seed(42); random.seed(42)
    data = charger_donnees()
    # Source officielle installée : le grand échantillon est le test_size du splitter interne !
    test_indices, train_indices = SampleRandomP(.75,stratified=True,random_state=OWDataSampler.RandomSeed)(data)
    train,test = data[train_indices],data[test_indices]
    assert len(train) == 3750 and int(train.Y.sum()) == 426
    assert len(test) == 1250 and int(test.Y.sum()) == 142
    assert not set(train_indices) & set(test_indices)
    avant,res_avant = evaluer(train,test,learners(False))
    apres,res_apres = evaluer(train,test,learners(True))
    pred = pd.DataFrame({'indice_csv_base_0':test_indices,'fraude':test.Y.astype(int)})
    for stade,res in [('avant',res_avant),('apres',res_apres)]:
        for i,nom in enumerate(avant):
            pred[f'{stade}_{nom}_prediction'] = res.predicted[i].astype(int)
            pred[f'{stade}_{nom}_probabilite_1'] = res.probabilities[i,:,1]
    pred.to_csv(ROOT / 'reports/orange_predictions.csv',index=False)
    gb = res_apres.models[0,list(apres).index('Gradient Boosting')]
    with open(ROOT / 'models/fraude-gb.pkcls','wb') as fichier:
        pickle.dump(gb,fichier)  # Identique à OWSaveModel.do_save, protocole par défaut.
    with open(ROOT / 'models/fraude-gb.pkcls','rb') as fichier:
        recharge = pickle.load(fichier)
    np.testing.assert_array_equal(gb(test),recharge(test))
    seuil = mesures(test.Y, (pred['apres_Gradient Boosting_probabilite_1'].to_numpy() >= .3).astype(int),
                    pred['apres_Gradient Boosting_probabilite_1'].to_numpy())
    cv = {}
    for stade,ameliore in [('avant',False),('apres',True)]:
        modeles = learners(ameliore)
        res = Orange.evaluation.CrossValidation(k=5,stratified=True,random_state=42,
                                                store_data=True)(data,list(modeles.values()))
        if any(res.failed):
            raise RuntimeError(res.failed)
        score = Orange.evaluation.F1(res,target=1)
        cv[stade] = {}
        export = pd.DataFrame({'indice_csv_base_0':res.row_indices,'fraude':res.actual.astype(int)})
        for i,nom in enumerate(modeles):
            plis = [float(Orange.evaluation.F1(res.get_fold(j),target=1)[i]) for j in range(5)]
            cv[stade][nom] = {'F1':float(score[i]),'F1_par_pli':plis,'F1_moyenne_plis':float(np.mean(plis)),
                              'AUC':float(Orange.evaluation.AUC(res,target=1)[i])}
            export[nom+'_prediction'] = res.predicted[i].astype(int)
            export[nom+'_probabilite_1'] = res.probabilities[i,:,1]
        export.to_csv(ROOT / f'reports/orange_cv_{stade}_predictions.csv',index=False)
        courbes(res,list(modeles),f'figures/orange_roc_cv_{stade}.png',f'CV 5 plis {stade}, cible 1')
    figure_matrice(apres['Gradient Boosting']['matrice'],'Gradient Boosting - Orange (API Python)',
                   'figures/orange_matrice_gb.png')
    courbes(res_avant,list(avant),'figures/orange_roc_avant.png','test fixe avant, cible 1')
    courbes(res_apres,list(apres),'figures/orange_roc_apres.png','test fixe après, cible 1')
    parametres = {}
    for stade in ['avant','apres']:
        parametres[stade] = {}
        for nom,l in learners(stade == 'apres').items():
            effectif = l.get_learner(data) if hasattr(l,'get_learner') else l
            parametres[stade][nom] = {'params':effectif.params,
                                     'pretraitements':[repr(p) for p in effectif.active_preprocessors]}
    resultat = {'provenance':provenance('Orange (API Python)'), 'orange':Orange.__version__,
                'graines':{'donnees':7,'sampler':42,'CV':42,'LR':0,'RF':0,'GB':0},
                'partage':{'train':3750,'fraudes_train':426,'test':1250,'fraudes_test':142},
                'avant':avant,'apres':apres,'cv':cv,'seuil_0_3':seuil,'parametres':parametres,
                'modele_octets':(ROOT/'models/fraude-gb.pkcls').stat().st_size}
    sauvegarde('orange_resultats.json',resultat)
    comparaison=[]
    for nom,valeurs in ATTENDUS.items():
        stade = 'apres' if nom in ['kNN standardisé','Random Forest 100'] else 'avant'
        cle = {'kNN standardisé':'kNN','Random Forest 100':'Random Forest'}.get(nom,nom)
        for metrique,attendu in zip(['AUC','CA','F1','Prec','Recall'],valeurs):
            mesure = resultat[stade][cle][metrique]
            comparaison.append({'provenance':'Orange (API Python)','modele':nom,'stade':stade,
                                'metrique':metrique,'mesure':mesure,'attendu_enonce':attendu,'ecart':mesure-attendu})
    pd.DataFrame(comparaison).to_csv(ROOT/'reports/orange_comparaison_scores.csv',index=False)
    texte = '# Résultats Orange\n\nProvenance de toutes les mesures : **Orange (API Python)**. '
    texte += f"Orange {Orange.__version__}, scikit-learn {resultat['provenance']['scikit_learn']}, NumPy {np.__version__}. "
    texte += 'Aucun widget graphique piloté et aucune capture revendiquée. Les sources installées et leurs SHA-256 sont archivés dans orange_sources_installees.md et orange_sources_manifest.json.\n\n'
    texte += '## Protocole et audit des réglages\n\n'
    texte += 'Domaine explicite : fraude cible catégorielle 0/1 ; nuit catégorielle ; trois autres attributs continus. '
    texte += 'OWDataSampler.RandomSeed=42 ; SampleRandomP(.75) passe 3750 comme test_size à StratifiedShuffleSplit puis nomme ce second sous-ensemble Data Sample. '
    texte += 'On utilise cette classe directement : inverser simplement train_test_split(test_size=.25) ne reproduit pas les mêmes lignes, même à graine 42. '
    texte += '3750 apprentissage dont 426 fraudes ; 1250 test dont 142 fraudes.\n\n'
    texte += 'LR : C=1, L2, max_iter=10000, random_state=0, solver auto (lbfgs), prétraitements par défaut sans standardisation ajoutée. '
    texte += 'kNN : 5 voisins, distance euclidienne, poids uniformes ; après amélioration NormalizeBySD appris sur le train seulement, puis prétraitements par défaut (use_default_preprocessors=True comme OWBaseLearner pour Fitter). '
    texte += 'Tree Orange natif : binarize=True, feuille minimale 2, split minimal 5, profondeur 100, majorité suffisante .95 ; il ne faut pas le remplacer par DecisionTreeClassifier par défaut. '
    texte += 'RF : 10 puis 100 arbres, random_state=0 quand Replicable est coché, min_samples_split=5, max_features=sqrt. '
    texte += 'GB : méthode scikit-learn, 100 arbres, learning_rate=.1, max_depth=3, subsample=1, min_samples_split=2, random_state=0 (Replicable activé par défaut). '
    texte += 'TestAndScore utilise TestOnTestData ; CV utilise random_state=42. Save Model utilise pickle.dump sans protocole explicitement modifié.\n\n'
    texte += '## Étape 1.2 avant amélioration\n\n' + table_mesures(avant) + '\n\n'
    texte += '## Étape 1.3 après amélioration\n\n' + table_mesures(apres) + '\n\n'
    texte += '| Mesure | Mesuré | Attendu de l’énoncé | Écart signé | Explication |\n|---|---|---|---|---|\n'
    for nom,vals in ATTENDUS.items():
        row = next(r for r in comparaison if r['modele']==nom and r['metrique']=='F1')
        exp = 'Compatible avec l’arrondi à trois décimales' if abs(row['ecart']) <= .0005 else 'Écart conservé ; versions des dépendances/implémentation à considérer, aucun réglage forcé'
        texte += f"| F1 {nom} | {row['mesure']:.6f} | {row['attendu_enonce']:.3f} | {row['ecart']:+.6f} | {exp} |\n"
    for nom,att in [('Gradient Boosting',.818),('Logistic Regression',.744)]:
        val=cv['apres'][nom]['F1']
        texte += f'| F1 CV {nom} | {val:.6f} | {att:.3f} | {val-att:+.6f} | Scores Orange agrégés hors pli ; moyenne des F1 par pli également enregistrée |\n'
    texte += '\nTous les écarts AUC/CA/F1/précision/rappel sont aussi dans orange_comparaison_scores.csv ; les attendus ne sont jamais substitués aux mesures.\n\n'
    texte += f"Matrice GB mesurée : `{apres['Gradient Boosting']['matrice']}` ; attendue de l’énoncé : `[[1093,15],[29,113]]`. "
    texte += f"Écart élément par élément : `{(np.array(apres['Gradient Boosting']['matrice'])-np.array([[1093,15],[29,113]])).tolist()}`. "
    texte += f"Modèle sauvegardé : {resultat['modele_octets']} octets ; recharge pickle et prédictions identiques validées. L’énoncé annonce environ 320 Ko : notre fichier est plus petit. Le format a été vérifié dans OWSaveModel.do_save (pickle.dump sans protocole ajouté) et les paramètres sont fidèles ; la représentation sérialisée dépend des bibliothèques. La cause exacte de cet écart de taille n’est pas établie. Aucun remplissage artificiel n’est ajouté ; la taille n’est pas une métrique de qualité.\n\n"
    texte += '## B2 CV stratifiée 5 plis\n\n| Modèle | F1 avant agrégé | F1 après agrégé | Moyenne F1 après par pli |\n|---|---|---|---|\n'
    for nom in avant:
        texte += f"| {nom} | {cv['avant'][nom]['F1']:.6f} | {cv['apres'][nom]['F1']:.6f} | {cv['apres'][nom]['F1_moyenne_plis']:.6f} |\n"
    texte += '\nChaque ligne est validée une fois hors pli ; 4000 lignes entraînent chaque modèle. Le F1 affiché par Orange est calculé sur les prédictions hors pli regroupées, et n’est pas exactement la moyenne des cinq F1. Les deux sont conservés.\n\n'
    texte += '## B3 ROC et seuil pédagogique\n\n'
    for stade, scores in [('avant',avant),('apres',apres)]:
        bas=min(scores,key=lambda k:scores[k]['AUC'])
        texte += f"Sur le test fixe {stade}, la plus faible AUC est celle de {bas} ({scores[bas]['AUC']:.6f}). "
    texte += 'Les courbes peuvent se croiser ; l’AUC mesure le classement global. Les figures ROC avant/après et CV sont légendées reproduction Python.\n\n'
    texte += f"Seuil GB abaissé de .5 à .3, choisi a priori pour illustrer le compromis (pas optimisé sur le test) : matrice `{seuil['matrice']}`, F1 {seuil['F1']:.6f}, précision {seuil['Prec']:.6f}, rappel {seuil['Recall']:.6f}. "
    texte += 'Il s’agit d’une illustration sur le test, pas d’une preuve de gain en production. Choisir un seuil métier sur validation avec coûts explicites et tester ensuite sur un jeu indépendant.\n'
    (ROOT/'reports/orange_resultats.md').write_text(texte,encoding='utf-8')
    print(table_mesures(avant)); print(table_mesures(apres))
    print('CV :',cv); print('Seuil .3 :',seuil)

if __name__ == '__main__':
    main()
