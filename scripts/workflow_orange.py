"""Phase 3 : générer ET recharger/exécuter le .ows avec l'API en offscreen.

Ne produit aucune capture et n'ouvre aucune fenêtre visible.
"""
import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
import json
import time
import importlib
from pathlib import Path
import numpy as np
from AnyQt.QtWidgets import QApplication
from AnyQt.QtCore import QCoreApplication, QEventLoop
from orangecanvas.registry import WidgetRegistry
from orangecanvas.scheme import Scheme, SchemeLink
from orangewidget.workflow.discovery import widget_desc_from_module
from orangewidget.workflow.widgetsscheme import WidgetsScheme
from Orange.widgets.utils.filedialogs import RecentPath
from Orange.data import DiscreteVariable
from Orange.widgets.utils.domaineditor import Column, Place
from Orange.widgets.evaluate.owtestandscore import OWTestAndScore
from commun import ROOT, sauvegarde

SPECS = [
    ('file','Orange.widgets.data.owfile',(0,200),{'source':0,'recent_paths':[RecentPath(str(ROOT/'data/transactions.csv'),'basedir','../data/transactions.csv')]}),
    ('table','Orange.widgets.data.owtable',(200,0),{}),
    ('sampler','Orange.widgets.data.owdatasampler',(220,200),{'sampleSizePercentage':75,'stratify':True,'use_seed':True}),
    ('preprocess','Orange.widgets.data.owpreprocess',(220,420),{'storedsettings':{'preprocessors':[('orange.preprocess.scale',{'method':2})]}}),
    ('lr','Orange.widgets.model.owlogisticregression',(440,0),{}),
    ('knn','Orange.widgets.model.owknn',(440,120),{}),
    ('tree','Orange.widgets.model.owtree',(440,240),{}),
    ('rf','Orange.widgets.model.owrandomforest',(440,360),{'n_estimators':100,'use_random_state':True}),
    ('gb','Orange.widgets.model.owgradientboosting',(440,500),{'method_index':0}),
    ('test','Orange.widgets.evaluate.owtestandscore',(690,210),{'resampling':OWTestAndScore.TestOnTest,'n_folds':2,'cv_stratified':True}),
    ('cm','Orange.widgets.evaluate.owconfusionmatrix',(940,90),{'selected_learner':[4]}),
    ('save','Orange.widgets.model.owsavemodel',(690,570),{'stored_path':str(ROOT/'models'),'stored_name':'fraude-gb.pkcls','auto_save':False}),
    ('pred','Orange.widgets.evaluate.owpredictions',(940,470),{}),
    ('roc','Orange.widgets.evaluate.owrocanalysis',(940,280),{}),
]
LIENS = [
    ('file','Data','table','Data'),('file','Data','sampler','Data'),
    ('sampler','Data Sample','test','Data'),('sampler','Remaining Data','test','Test Data'),
    *[(key,'Learner','test','Learner') for key in ['lr','knn','tree','rf','gb']],
    ('preprocess','Preprocessor','knn','Preprocessor'),('test','Evaluation Results','cm','Evaluation Results'),
    ('sampler','Data Sample','gb','Data'),('gb','Model','save','Model'),
    ('gb','Model','pred','Predictors'),('sampler','Remaining Data','pred','Data'),
    ('test','Evaluation Results','roc','Evaluation Results'),
]

def attendre(app, schema, nodes, timeout=120):
    debut = time.monotonic()
    while time.monotonic()-debut < timeout:
        app.processEvents(QEventLoop.AllEvents,50)
        cm = schema.widget_for_node(nodes['cm'])
        res = getattr(cm,'results',None)
        if res is not None and len(res.predicted) == 5 and len(res.actual) == 1250:
            if not schema.signal_manager.has_pending() and not schema.signal_manager.active_nodes():
                return res
        time.sleep(.02)
    erreurs={k:[str(m) for m in schema.widget_for_node(n).Error.active] for k,n in nodes.items()}
    raise TimeoutError(f'Calcul non terminé en {timeout}s : {erreurs}')

def verifier(schema,nodes,res):
    from Orange.evaluation import F1
    noms = res.learner_names
    reference = json.loads((ROOT/'reports/orange_resultats.json').read_text(encoding='utf-8'))['apres']
    f1 = dict(zip(noms,map(float,F1(res,target=1))))
    for nom in reference:
        assert np.isclose(f1[nom],reference[nom]['F1']), (nom,f1)
    sampler=schema.widget_for_node(nodes['sampler'])
    assert sampler.sampled_instances == 3750 and sampler.remaining_instances == 1250
    assert sampler.data.domain.class_var.name == 'fraude'
    assert sampler.data.domain['nuit'].is_discrete
    assert schema.widget_for_node(nodes['test']).class_selection == '1'
    assert schema.widget_for_node(nodes['roc']).target_index == 1
    assert schema.widget_for_node(nodes['cm']).selected_learner == [4]
    return f1

def main():
    app = QApplication.instance() or QApplication([])
    registry=WidgetRegistry()
    descriptions={}
    for cle,module,_,_ in SPECS:
        desc=widget_desc_from_module(importlib.import_module(module))
        registry.register_widget(desc)
        descriptions[cle]=desc
    schema=WidgetsScheme(title='Détection de fraude avec Orange',env={'basedir':str(ROOT/'workflows')})
    nodes={}
    for cle,module,position,props in SPECS:
        classe=getattr(importlib.import_module(module),descriptions[cle].qualified_name.rsplit('.',1)[1])
        props={**props,'__version__':getattr(classe,'settings_version',0) or 0}
        nodes[cle]=schema.new_node(descriptions[cle],position=position,properties=props)
    for node in nodes.values():
        schema.widget_for_node(node)
    fichier=schema.widget_for_node(nodes['file'])
    fichier.load_data()
    assert fichier.data is not None
    for var in fichier.domain_editor.model().variables:
        if var[Column.name] == 'fraude':
            var[Column.tpe],var[Column.place] = DiscreteVariable,Place.class_var
        elif var[Column.name] == 'nuit':
            var[Column.tpe],var[Column.place] = DiscreteVariable,Place.feature
    fichier.apply_domain_edit()
    for source,out,sink,entree in LIENS:
        schema.add_link(SchemeLink(nodes[source],out,nodes[sink],entree))
    res=attendre(app,schema,nodes)
    test=schema.widget_for_node(nodes['test'])
    test.class_selection='1'
    test._on_target_class_changed()
    roc=schema.widget_for_node(nodes['roc'])
    roc.target_index=1
    roc._replot()
    cm=schema.widget_for_node(nodes['cm'])
    cm.selected_learner=[4]
    cm._update()
    f1=verifier(schema,nodes,res)
    # Enregistrer dans tmp d'abord ; ne publier le .ows qu'après recharge validée.
    candidat=ROOT/'tmp/fraude-orange-candidat.ows'
    schema.save_to(str(candidat),pickle_fallback=True)
    schema.signal_manager.stop()
    nouveau=WidgetsScheme(env={'basedir':str(ROOT/'workflows')})
    nouveau.load_from(str(candidat),registry=registry)
    recharges=dict(zip(nodes,nouveau.nodes))
    for node in nouveau.nodes:
        nouveau.widget_for_node(node)
    res2=attendre(app,nouveau,recharges)
    f12=verifier(nouveau,recharges,res2)
    assert f1 == f12
    destination=ROOT/'workflows/fraude-orange.ows'
    destination.write_bytes(candidat.read_bytes())
    # Vérifier aussi la sérialisation seule, indépendamment des widgets.
    structure=Scheme(); structure.load_from(str(destination),registry=registry)
    assert len(structure.nodes) == 14 and len(structure.links) == len(LIENS)
    sauvegarde('orange_workflow_validation.json',{'provenance':'Orange (API Python), QApplication offscreen',
        'noeuds':len(structure.nodes),'liens':len(structure.links),'recharge_et_execution':True,
        'f1_classe_1_apres_recharge':f12,'cible_test_and_score':'1','cible_ROC':1,
        'matrice_selection':'Gradient Boosting','limite':'Vérification visuelle et captures [À FAIRE PAR L\'ÉTUDIANT] ; chemin CSV à relocaliser si déplacement.'})
    (ROOT/'reports/orange_workflow_validation.md').write_text(
        '# Validation du workflow Orange\n\nProvenance : **Orange (API Python)**, QT_QPA_PLATFORM=offscreen. '
        f'{len(structure.nodes)} widgets et {len(structure.links)} liens construits par orangecanvas/orangewidget. '
        'Le fichier a été rechargé dans WidgetsScheme, ses widgets instanciés et son calcul terminé ; les cinq F1 sont identiques aux mesures après amélioration. '
        'Cible fraude catégorielle, nuit catégorielle, partage 3750/1250, cible 1 dans Test and Score et ROC, matrice GB sélectionnée : contrôlés après recharge. '
        'Save Model conserve un chemin vers models/fraude-gb.pkcls ; Autosave est désactivé pour éviter un écrasement à l’ouverture. '
        'Le modèle réel a déjà été sauvegardé et rechargé en phase 2.\n\n'
        '**[À FAIRE PAR L\'ÉTUDIANT]** : ouvrir le workflow dans Orange, vérifier la disposition et les résultats affichés, relocaliser le CSV si nécessaire, faire les Captures 1 à 3. '
        'Aucune capture d’écran n’est produite par ce script. Voir guide_orange_manuel.md.\n',encoding='utf-8')
    print('Workflow livré après recharge et calcul validés :',f12,flush=True)
    nouveau.signal_manager.stop()
    # Pas d'app.exec() : aucune application graphique bloquante.

if __name__ == '__main__':
    main()
