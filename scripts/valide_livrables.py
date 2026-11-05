"""Validation finale : recalculer les métriques depuis les prédictions archivées."""
import json
from pathlib import Path
import hashlib
import numpy as np
import pandas as pd
from sklearn.metrics import f1_score, confusion_matrix, roc_auc_score

ROOT=Path(__file__).resolve().parents[1]

def lire(nom):
    return json.loads((ROOT/'reports'/nom).read_text(encoding='utf-8-sig'))

def main():
    df=pd.read_csv(ROOT/'data/transactions.csv')
    d=lire('donnees_validation.json'); o=lire('orange_resultats.json')
    k=lire('knime_simulation_resultats.json'); f=lire('flaml_resultats.json')
    assert len(df)==5000 and df.fraude.sum()==568
    assert len((ROOT/'data/transactions.csv').read_text().splitlines())==5001
    empreinte=hashlib.sha256((ROOT/'data/transactions.csv').read_bytes()).hexdigest()
    assert empreinte==d['sha256']
    assert all(r['provenance']['donnees_sha256']==empreinte for r in [o,k,f])
    orange=pd.read_csv(ROOT/'reports/orange_predictions.csv')
    knime=pd.read_csv(ROOT/'reports/knime_simulation_predictions.csv')
    flaml=pd.read_csv(ROOT/'reports/flaml_predictions.csv')
    for tab,nfraudes in [(orange,142),(knime,142),(flaml,134)]:
        assert len(tab)==1250 and tab.fraude.sum()==nfraudes
        assert tab.indice_csv_base_0.is_unique
        assert tab.fraude.tolist()==df.fraude.iloc[tab.indice_csv_base_0].tolist()
    for stade in ['avant','apres']:
        for nom,m in o[stade].items():
            pred=orange[f'{stade}_{nom}_prediction']
            assert np.isclose(f1_score(orange.fraude,pred,pos_label=1),m['F1'])
            assert confusion_matrix(orange.fraude,pred,labels=[0,1]).tolist()==m['matrice']
            assert np.isclose(roc_auc_score(orange.fraude,orange[f'{stade}_{nom}_probabilite_1']),m['AUC'])
        cv=pd.read_csv(ROOT/f'reports/orange_cv_{stade}_predictions.csv')
        assert len(cv)==5000 and cv.indice_csv_base_0.is_unique
        assert cv.fraude.tolist()==df.fraude.iloc[cv.indice_csv_base_0].tolist()
        for nom in o[stade]:
            assert np.isclose(f1_score(cv.fraude,cv[nom+'_prediction'],pos_label=1),o['cv'][stade][nom]['F1'])
    for nom,m in k['resultats'].items():
        assert np.isclose(f1_score(knime.fraude,knime[nom+'_prediction'],pos_label=1),m['F1'])
        assert confusion_matrix(knime.fraude,knime[nom+'_prediction'],labels=[0,1]).tolist()==m['matrice']
        assert np.array(m['matrice']).sum(axis=1).tolist()==[1108,142]
    assert np.isclose(f1_score(flaml.fraude,flaml.prediction,pos_label=1),f['resultats']['F1'])
    assert confusion_matrix(flaml.fraude,flaml.prediction,labels=[0,1]).tolist()==f['resultats']['matrice']
    assert o['apres']['Gradient Boosting']['matrice']==[[1093,15],[29,113]]
    pred3=(orange['apres_Gradient Boosting_probabilite_1']>=.3).astype(int)
    assert confusion_matrix(orange.fraude,pred3,labels=[0,1]).tolist()==o['seuil_0_3']['matrice']
    comparaison=pd.read_csv(ROOT/'reports/orange_comparaison_scores.csv')
    assert len(comparaison)==35 and (comparaison.ecart.abs()<=.0005).all()
    assert round(o['cv']['apres']['Gradient Boosting']['F1'],3)==.818
    assert round(o['cv']['apres']['Logistic Regression']['F1'],3)==.744
    q=lire('questions_validation.json')
    assert len(q['mots_par_reponse'])==8 and all(120<=n<=200 for n in q['mots_par_reponse'].values())
    w=lire('orange_workflow_validation.json')
    assert w['recharge_et_execution'] and w['noeuds']==14 and w['liens']==16
    for nom,valeur in w['f1_classe_1_apres_recharge'].items():
        assert np.isclose(valeur,o['apres'][nom]['F1'])
    assert (ROOT/'models/fraude-gb.pkcls').stat().st_size==o['modele_octets']
    texte=(ROOT/'reports/compte_rendu.md').read_text(encoding='utf-8')
    assert all(f'[CAPTURE {n} À INSÉRER' in texte for n in range(1,6))
    assert (ROOT/'reports/A_FAIRE_MANUELLEMENT.md').exists()
    assert not lire('compte_rendu_validation.json')['controle_visuel_valide']
    result={'validation_calculs':True,'sha256_csv':empreinte,
            'comparaisons_orange_conformes_arrondi':35,
            'CV_conforme_arrondi':True,'predictions_et_matrices_recalculees':True,
            'workflow_Orange_recharge_execute':True,'reponses_120_200_mots':True,
            'KNIME_reel':False,'export_knime_present':(ROOT/'workflows/tp-fraude.knwf').exists(),
            'captures_reelles':False,'rendu_visuel_Word':False,
            'limites':'Voir A_FAIRE_MANUELLEMENT.md et rendu_word_limite.md.'}
    (ROOT/'reports/validation_finale.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(result,indent=2,ensure_ascii=False))

if __name__=='__main__':
    main()
