"""Phase 8 : assembler le compte rendu Markdown depuis nos mesures réelles."""
import json
from commun import ROOT, table_mesures

def main():
    o=json.loads((ROOT/'reports/orange_resultats.json').read_text(encoding='utf-8'))
    k=json.loads((ROOT/'reports/knime_simulation_resultats.json').read_text(encoding='utf-8'))
    f=json.loads((ROOT/'reports/flaml_resultats.json').read_text(encoding='utf-8'))
    validation=json.loads((ROOT/'reports/orange_workflow_validation.json').read_text(encoding='utf-8'))
    texte='# Détection de fraude avec Orange et KNIME\n\n'
    texte+='[NOM] [PRÉNOM] — [FILIÈRE] — [GROUPE]\n\nEMSI — 5IASD — Déploiement d’IA — Année 2026 2027\n\n'
    texte+='Ce TP compare cinq modèles Orange avant et après amélioration, une simulation préparatoire à KNIME et une référence FLAML. '
    texte+='Les calculs Orange reproduisent les scores de l’énoncé à son arrondi. Les captures et les mesures KNIME réelles restent **[À FAIRE PAR L\'ÉTUDIANT]**. '
    texte+='Toutes les mesures sont issues des scripts du dépôt ; les valeurs attendues sont identifiées comme provenant de l’énoncé. '
    texte+='Le F1 porte toujours sur la classe 1, fraude.\n\n'
    texte+='## Données et hypothèses\n\n'
    texte+='L’Annexe A a été exécutée avec la graine 7 : 5000 transactions, 568 fraudes (11,36 %), 5001 lignes avec en-tête. '
    texte+='Provenance des contrôles de données : simulation scikit-learn (génération NumPy/pandas de l’Annexe A). '
    texte+='Attributs : montant, anciennete, freq_24h, nuit ; cible : fraude. Aucun attribut n’est construit à partir de la cible. '
    texte+='Le dossier TP04 voisin est absent ; les paramètres FLAML sont donc supposés selon la consigne. '
    texte+=f"Orange {o['orange']}, Python {o['provenance']['python']}, scikit-learn {o['provenance']['scikit_learn']}, NumPy {o['provenance']['numpy']} ; versions figées dans requirements-orange.txt. "
    texte+='Les deux venv locaux sont séparés ; aucune application Orange ou KNIME n’a été pilotée graphiquement.\n\n'
    texte+='## Partie Orange\n\n'
    texte+='### Cible et partage\n\n'
    texte+='Provenance : **Orange (API Python)**. Fraude est une cible catégorielle 0/1, nuit un attribut catégoriel. '
    texte+='Le Data Sampler officiel à 75 %, stratifié et déterministe (graine interne 42), donne 3750 lignes d’apprentissage dont 426 fraudes et 1250 de test dont 142 fraudes. '
    texte+='Test and Score est reproduit avec TestOnTestData, cible 1. Les Learners utilisent les paramètres lus dans les sources installées ; les graines LR, RF et GB valent 0. '
    texte+='La graine globale de précaution vaut 42 ; Tree et kNN ne font ici aucun tirage aléatoire.\n\n'
    texte+='### Comparaison avant amélioration\n\n'+table_mesures(o['avant'])+'\n\n'
    texte+='### Comparaison après amélioration\n\n'
    texte+='Le kNN reçoit Normalize Features, standardisation des variables continues apprise sur le train ; RF passe de 10 à 100 arbres, Replicable conservé. Les autres modèles restent identiques.\n\n'
    texte+=table_mesures(o['apres'])+'\n\n'
    texte+='[CAPTURE 1 À INSÉRER : Test and Score Orange après amélioration, Test on test data, cible 1, cinq modèles, AUC CA F1 Prec Recall, apprentissage 3750 et test 1250]\n\n'
    texte+='### Mesuré et attendu de l’énoncé\n\n'
    texte+='| F1 classe 1 | Mesuré Orange API Python | Attendu énoncé | Écart signé |\n|---|---|---|---|\n'
    lignes=[('LR avant',o['avant']['Logistic Regression']['F1'],.781),('kNN avant',o['avant']['kNN']['F1'],.478),
            ('Tree avant',o['avant']['Tree']['F1'],.756),('RF avant',o['avant']['Random Forest']['F1'],.813),
            ('GB avant',o['avant']['Gradient Boosting']['F1'],.837),('kNN standardisé',o['apres']['kNN']['F1'],.780),
            ('RF 100',o['apres']['Random Forest']['F1'],.833),
            ('GB CV 5 plis',o['cv']['apres']['Gradient Boosting']['F1'],.818),
            ('LR CV 5 plis',o['cv']['apres']['Logistic Regression']['F1'],.744)]
    for nom,val,att in lignes:
        texte+=f'| {nom} | {val:.6f} | {att:.3f} | {val-att:+.6f} |\n'
    texte+='\nTous ces écarts s’expliquent par l’arrondi de l’énoncé à trois décimales. Les paramètres n’ont pas été ajustés pour forcer les valeurs. '
    texte+='Le détail de toutes les métriques, paramètres et prédictions est conservé dans orange_resultats.md et les JSON/CSV associés.\n\n'
    texte+='### Erreurs et sauvegarde\n\n'
    texte+=f"Matrice GB mesurée : {o['apres']['Gradient Boosting']['matrice']}, identique à l’attendu de l’énoncé ; lignes réelles 0/1 et colonnes prédites 0/1. "
    texte+='113 fraudes détectées sur 142, 29 manquées, 15 fausses alertes. '
    texte+=f"Le modèle models/fraude-gb.pkcls pèse {o['modele_octets']} octets, contre environ 320 Ko annoncés. "
    texte+='Le format a été vérifié dans Save Model : pickle.dump ; la recharge restitue les mêmes prédictions. La cause exacte de l’écart de taille n’est pas établie, la représentation dépendant des bibliothèques.\n\n'
    texte+='[CAPTURE 2 À INSÉRER : Confusion Matrix Orange, Gradient Boosting sélectionné, effectifs [[1093,15],[29,113]], classes et axes visibles, total 1250]\n\n'
    texte+='![Matrice GB — reproduction Python, ne remplace pas la capture](../figures/orange_matrice_gb.png)\n\n'
    texte+=f"Le workflow fraude-orange.ows contient {validation['noeuds']} widgets et {validation['liens']} liens. Il a été rechargé et exécuté en offscreen ; les cinq F1, les types de colonnes et les cibles des widgets d’évaluation ont été contrôlés. "
    texte+='Save Model est connecté au modèle GB appris sur les 3750 lignes ; son autosauvegarde reste désactivée. Predictions reçoit le modèle GB et les 1250 lignes restantes. '
    texte+='La disposition visuelle et les chemins après déplacement doivent encore être vérifiés dans l’application.\n\n'
    texte+='[CAPTURE 3 À INSÉRER : workflow Orange complet et lisible avec File Data Table Data Sampler cinq Learners Preprocess Test and Score Confusion Matrix Save Model Predictions ROC Analysis et leurs connexions]\n\n'
    texte+='## Partie KNIME\n\n'
    texte+='**SIMULATION scikit-learn, pas une mesure KNIME.** KNIME n’a pas été détecté par la recherche locale documentée ; une installation portable ailleurs reste possible. '
    texte+='Aucun .knwf n’a été fabriqué. Le guide_knime.md détaille les 12 nœuds, les types, ports, réglages et contrôles. '
    texte+='La simulation partage les lignes avec train_test_split stratifié 75/25, random_state=42 : 3750 lignes dont 426 fraudes ; 1250 dont 142 fraudes. '
    texte+='LR utilise les attributs bruts et max_iter=2000 ; RF 100 arbres ; GB 100 arbres, profondeur 4, learning_rate=0.1 ; graines des modèles 42.\n\n'
    texte+=table_mesures(k['resultats'])+'\n\n'
    for nom,m in k['resultats'].items():
        texte+=f"- {nom} (simulation scikit-learn) : matrice {m['matrice']}.\n"
    texte+='\nChaque matrice totalise 1250 lignes, dont 1108 réelles 0 et 142 réelles 1. '
    texte+='La LR simulée est sous l’ordre de grandeur indicatif 0,75–0,85 de l’énoncé ; les scores sont conservés. Les lignes tirées, les optimiseurs et les paramètres internes diffèrent de KNIME ; la simulation ne permet pas d’attribuer un résultat à ses nœuds.\n\n'
    texte+='[CAPTURE 4 À INSÉRER : workflow KNIME réel complet des nœuds 1 à 12, trois branches Learner Predictor Scorer, tous les feux au vert et connexions visibles]\n\n'
    texte+='[CAPTURE 5 À INSÉRER : meilleur Scorer KNIME réel, vue Confusion Matrix et second port Accuracy statistics avec ligne classe 1 et F-measure lisibles]\n\n'
    texte+='### Mesures KNIME réelles à relever\n\n| Modèle | F1 classe 1 KNIME réel | Matrice réelle |\n|---|---|---|\n'
    for nom in k['resultats']:
        texte+=f'| {nom} | [À FAIRE PAR L\'ÉTUDIANT] | [À REMPLIR] |\n'
    texte+='\nExporter ensuite workflows/tp-fraude.knwf depuis le Space Explorer.\n\n'
    texte+='## Référence FLAML\n\n'
    texte+='Provenance : **simulation scikit-learn**, recherche réellement pilotée par FLAML. Paramètres supposés : test_size=0.25 NON stratifié, random_state=42, time_budget=60, seed=42, classification, métrique f1, n_jobs=1. '
    texte+=f"Le contrôle trouve 134 fraudes parmi les 1250 lignes de test. Meilleur modèle : {f['meilleur_modele']}, F1 externe {f['resultats']['F1']:.6f}. "
    texte+=f"Durée observée : {f['duree_secondes']:.3f} secondes. Le modèle est sélectionné sur validation interne ; le test externe reste réservé à la mesure finale. "
    texte+='Le budget temps et la machine peuvent modifier le résultat. Aucun enregistrement MLflow n’est revendiqué ici.\n\n'
    comparatif=(ROOT/'reports/comparatif.md').read_text(encoding='utf-8')
    table= comparatif[comparatif.index('| Approche'):comparatif.index('## Dans quel contexte')]
    texte+='## Tableau de synthèse\n\n'+table+'\n'
    texte+='## Conclusion en cinq lignes\n\n'
    texte+=comparatif.split('## Dans quel contexte recommander chaque approche\n\n')[1].split('## Précautions')[0]
    texte+='\nFLAML utilise un test non stratifié ; Orange et KNIME stratifié, avec des lignes pouvant différer selon l’outil. '
    texte+='On compare des ordres de grandeur : 1 à 2 centièmes de différence ne démontrent pas une différence significative. Aucun test statistique n’a été effectué. '
    texte+='L’exploration sur le test et l’étude du seuil restent pédagogiques ; en production, réserver une validation pour les choix et un test final indépendant.\n\n'
    questions=(ROOT/'reports/questions_reponses.md').read_text(encoding='utf-8')
    texte+='## Questions et bonus\n\n'+questions[questions.index('## Q1'):].replace('## ','### ')
    texte+='### B1 AutoML KNIME optionnel\n\n'
    texte+='[À FAIRE PAR L\'ÉTUDIANT] : composant AutoML de classification publié par KNIME sur le Community Hub, branché après Number to String. '
    texte+='Cible fraude, classe positive 1, F-measure si proposée ; désactiver Keras et H2O, exécuter puis capturer le classement réel. '
    texte+='Son partage propre 80/20 empêche une comparaison directe avec le test 75/25. Aucun score B1 simulé. Voir guide_knime.md.\n\n'
    texte+='![ROC après amélioration — reproduction Python, ne remplace pas la capture](../figures/orange_roc_apres.png)\n\n'
    texte+='## Traçabilité et travail restant\n\n'
    texte+='Sources : PDF fourni (15 pages), scripts versionnés, reports/donnees_validation.json, orange_resultats.json, orange_workflow_validation.json, knime_simulation_resultats.json, flaml_resultats.json et prédictions CSV associées. '
    texte+='Les sources Orange installées sont archivées avec leurs empreintes. Toutes les graines et versions utiles sont conservées. '
    texte+='Les Captures 1 à 5, les F1 KNIME réels, le temps humain et l’export .knwf restent [À FAIRE PAR L\'ÉTUDIANT]. '
    texte+='Voir A_FAIRE_MANUELLEMENT.md avant le rendu final. Remplir l’identité, reformuler les observations, insérer les captures et exporter au nom demandé par l’énoncé.\n'
    (ROOT/'reports/compte_rendu.md').write_text(texte,encoding='utf-8')
    assert all(f'[CAPTURE {n} À INSÉRER' in texte for n in range(1,6))
    print('Compte rendu Markdown assemblé ; cinq emplacements de captures contrôlés.')

if __name__ == '__main__':
    main()
