# Détection de fraude avec Orange et KNIME

[NOM] [PRÉNOM] — [FILIÈRE] — [GROUPE]

EMSI — 5IASD — Déploiement d’IA — Année 2026 2027

Ce TP compare cinq modèles Orange avant et après amélioration, une simulation préparatoire à KNIME et une référence FLAML. Les calculs Orange reproduisent les scores de l’énoncé à son arrondi. Les captures et les mesures KNIME réelles restent **[À FAIRE PAR L'ÉTUDIANT]**. Toutes les mesures sont issues des scripts du dépôt ; les valeurs attendues sont identifiées comme provenant de l’énoncé. Le F1 porte toujours sur la classe 1, fraude.

## Données et hypothèses

L’Annexe A a été exécutée avec la graine 7 : 5000 transactions, 568 fraudes (11,36 %), 5001 lignes avec en-tête. Provenance des contrôles de données : simulation scikit-learn (génération NumPy/pandas de l’Annexe A). Attributs : montant, anciennete, freq_24h, nuit ; cible : fraude. Aucun attribut n’est construit à partir de la cible. Le dossier TP04 voisin est absent ; les paramètres FLAML sont donc supposés selon la consigne. Orange 3.40.0, Python 3.13.3, scikit-learn 1.9.1, NumPy 2.3.5 ; versions figées dans requirements-orange.txt. Les deux venv locaux sont séparés ; aucune application Orange ou KNIME n’a été pilotée graphiquement.

## Partie Orange

### Cible et partage

Provenance : **Orange (API Python)**. Fraude est une cible catégorielle 0/1, nuit un attribut catégoriel. Le Data Sampler officiel à 75 %, stratifié et déterministe (graine interne 42), donne 3750 lignes d’apprentissage dont 426 fraudes et 1250 de test dont 142 fraudes. Test and Score est reproduit avec TestOnTestData, cible 1. Les Learners utilisent les paramètres lus dans les sources installées ; les graines LR, RF et GB valent 0. La graine globale de précaution vaut 42 ; Tree et kNN ne font ici aucun tirage aléatoire.

### Comparaison avant amélioration

| Modèle | AUC | CA | F1 classe 1 | Précision 1 | Rappel 1 |
|---|---|---|---|---|---|
| Logistic Regression | 0.979426 | 0.952000 | 0.781022 | 0.810606 | 0.753521 |
| kNN | 0.825183 | 0.904000 | 0.478261 | 0.625000 | 0.387324 |
| Tree | 0.845109 | 0.950400 | 0.755906 | 0.857143 | 0.676056 |
| Random Forest | 0.976617 | 0.958400 | 0.812950 | 0.830882 | 0.795775 |
| Gradient Boosting | 0.989078 | 0.964800 | 0.837037 | 0.882812 | 0.795775 |

### Comparaison après amélioration

Le kNN reçoit Normalize Features, standardisation des variables continues apprise sur le train ; RF passe de 10 à 100 arbres, Replicable conservé. Les autres modèles restent identiques.

| Modèle | AUC | CA | F1 classe 1 | Précision 1 | Rappel 1 |
|---|---|---|---|---|---|
| Logistic Regression | 0.979426 | 0.952000 | 0.781022 | 0.810606 | 0.753521 |
| kNN | 0.964137 | 0.951200 | 0.779783 | 0.800000 | 0.760563 |
| Tree | 0.845109 | 0.950400 | 0.755906 | 0.857143 | 0.676056 |
| Random Forest | 0.983971 | 0.963200 | 0.833333 | 0.858209 | 0.809859 |
| Gradient Boosting | 0.989078 | 0.964800 | 0.837037 | 0.882812 | 0.795775 |

[CAPTURE 1 À INSÉRER : Test and Score Orange après amélioration, Test on test data, cible 1, cinq modèles, AUC CA F1 Prec Recall, apprentissage 3750 et test 1250]

### Mesuré et attendu de l’énoncé

| F1 classe 1 | Mesuré Orange API Python | Attendu énoncé | Écart signé |
|---|---|---|---|
| LR avant | 0.781022 | 0.781 | +0.000022 |
| kNN avant | 0.478261 | 0.478 | +0.000261 |
| Tree avant | 0.755906 | 0.756 | -0.000094 |
| RF avant | 0.812950 | 0.813 | -0.000050 |
| GB avant | 0.837037 | 0.837 | +0.000037 |
| kNN standardisé | 0.779783 | 0.780 | -0.000217 |
| RF 100 | 0.833333 | 0.833 | +0.000333 |
| GB CV 5 plis | 0.818011 | 0.818 | +0.000011 |
| LR CV 5 plis | 0.743786 | 0.744 | -0.000214 |

Tous ces écarts s’expliquent par l’arrondi de l’énoncé à trois décimales. Les paramètres n’ont pas été ajustés pour forcer les valeurs. Le détail de toutes les métriques, paramètres et prédictions est conservé dans orange_resultats.md et les JSON/CSV associés.

### Erreurs et sauvegarde

Matrice GB mesurée : [[1093, 15], [29, 113]], identique à l’attendu de l’énoncé ; lignes réelles 0/1 et colonnes prédites 0/1. 113 fraudes détectées sur 142, 29 manquées, 15 fausses alertes. Le modèle models/fraude-gb.pkcls pèse 141461 octets, contre environ 320 Ko annoncés. Le format a été vérifié dans Save Model : pickle.dump ; la recharge restitue les mêmes prédictions. La cause exacte de l’écart de taille n’est pas établie, la représentation dépendant des bibliothèques.

[CAPTURE 2 À INSÉRER : Confusion Matrix Orange, Gradient Boosting sélectionné, effectifs [[1093,15],[29,113]], classes et axes visibles, total 1250]

![Matrice GB — reproduction Python, ne remplace pas la capture](../figures/orange_matrice_gb.png)

Le workflow fraude-orange.ows contient 14 widgets et 16 liens. Il a été rechargé et exécuté en offscreen ; les cinq F1, les types de colonnes et les cibles des widgets d’évaluation ont été contrôlés. Save Model est connecté au modèle GB appris sur les 3750 lignes ; son autosauvegarde reste désactivée. Predictions reçoit le modèle GB et les 1250 lignes restantes. La disposition visuelle et les chemins après déplacement doivent encore être vérifiés dans l’application.

[CAPTURE 3 À INSÉRER : workflow Orange complet et lisible avec File Data Table Data Sampler cinq Learners Preprocess Test and Score Confusion Matrix Save Model Predictions ROC Analysis et leurs connexions]

## Partie KNIME

**SIMULATION scikit-learn, pas une mesure KNIME.** KNIME n’a pas été détecté par la recherche locale documentée ; une installation portable ailleurs reste possible. Aucun .knwf n’a été fabriqué. Le guide_knime.md détaille les 12 nœuds, les types, ports, réglages et contrôles. La simulation partage les lignes avec train_test_split stratifié 75/25, random_state=42 : 3750 lignes dont 426 fraudes ; 1250 dont 142 fraudes. LR utilise les attributs bruts et max_iter=2000 ; RF 100 arbres ; GB 100 arbres, profondeur 4, learning_rate=0.1 ; graines des modèles 42.

| Modèle | AUC | CA | F1 classe 1 | Précision 1 | Rappel 1 |
|---|---|---|---|---|---|
| Logistic Regression | 0.979420 | 0.940800 | 0.701613 | 0.820755 | 0.612676 |
| Random Forest | 0.980589 | 0.956800 | 0.792308 | 0.872881 | 0.725352 |
| Gradient Boosting | 0.986535 | 0.960000 | 0.813433 | 0.865079 | 0.767606 |

- Logistic Regression (simulation scikit-learn) : matrice [[1089, 19], [55, 87]].
- Random Forest (simulation scikit-learn) : matrice [[1093, 15], [39, 103]].
- Gradient Boosting (simulation scikit-learn) : matrice [[1091, 17], [33, 109]].

Chaque matrice totalise 1250 lignes, dont 1108 réelles 0 et 142 réelles 1. La LR simulée est sous l’ordre de grandeur indicatif 0,75–0,85 de l’énoncé ; les scores sont conservés. Les lignes tirées, les optimiseurs et les paramètres internes diffèrent de KNIME ; la simulation ne permet pas d’attribuer un résultat à ses nœuds.

[CAPTURE 4 À INSÉRER : workflow KNIME réel complet des nœuds 1 à 12, trois branches Learner Predictor Scorer, tous les feux au vert et connexions visibles]

[CAPTURE 5 À INSÉRER : meilleur Scorer KNIME réel, vue Confusion Matrix et second port Accuracy statistics avec ligne classe 1 et F-measure lisibles]

### Mesures KNIME réelles à relever

| Modèle | F1 classe 1 KNIME réel | Matrice réelle |
|---|---|---|
| Logistic Regression | [À FAIRE PAR L'ÉTUDIANT] | [À REMPLIR] |
| Random Forest | [À FAIRE PAR L'ÉTUDIANT] | [À REMPLIR] |
| Gradient Boosting | [À FAIRE PAR L'ÉTUDIANT] | [À REMPLIR] |

Exporter ensuite workflows/tp-fraude.knwf depuis le Space Explorer.

## Référence FLAML

Provenance : **simulation scikit-learn**, recherche réellement pilotée par FLAML. Paramètres supposés : test_size=0.25 NON stratifié, random_state=42, time_budget=60, seed=42, classification, métrique f1, n_jobs=1. Le contrôle trouve 134 fraudes parmi les 1250 lignes de test. Meilleur modèle : xgboost, F1 externe 0.858238. Durée observée : 60.578 secondes. Le modèle est sélectionné sur validation interne ; le test externe reste réservé à la mesure finale. Le budget temps et la machine peuvent modifier le résultat. Aucun enregistrement MLflow n’est revendiqué ici.

## Tableau de synthèse

| Approche | Meilleur modele | F1 classe 1 | Jeu de test | Temps humain | Graine fixee ? | Export du modele |
|---|---|---|---|---|---|---|
| FLAML 60 s (TP04) | xgboost | 0.858238 | 1 250 l., 134 fraudes | [À REMPLIR] | seed=42 | MLflow (référence TP04 ; non produit ici) |
| Orange, avant ameliorat. | Gradient Boosting | 0.837037 | 1 250 l., 142 fraudes | [À REMPLIR] | Sampler=42 ; modèles selon sources | .pkcls |
| Orange, apres ameliorat. | Gradient Boosting | 0.837037 | 1 250 l., 142 fraudes | [À REMPLIR] | Sampler=42 ; modèles selon sources | .pkcls |
| KNIME | Gradient Boosting (sim.) ; [À REMPLIR après exécution KNIME] | 0.813433 (sim.) ; [À REMPLIR après exécution KNIME] | 1 250 l., 142 fraudes (sim.) | [À REMPLIR] | 42 (sim.) ; [À REMPLIR après exécution KNIME] | .knwf [À FAIRE PAR L'ÉTUDIANT] |


## Conclusion en cinq lignes

Orange convient à un premier apprentissage visuel et à une exploration interactive rapide.  
KNIME convient à la construction de traitements explicites et réutilisables par une équipe métier et données.  
FLAML convient à une recherche automatisée intégrée dans un projet Python reproductible.  
Un projet industrialisé doit ajouter tests, service de prédiction, suivi des versions et surveillance des dérives.  
Le choix dépend du public, du coût des erreurs et de la maintenance, au-delà du seul classement F1.


FLAML utilise un test non stratifié ; Orange et KNIME stratifié, avec des lignes pouvant différer selon l’outil. On compare des ordres de grandeur : 1 à 2 centièmes de différence ne démontrent pas une différence significative. Aucun test statistique n’a été effectué. L’exploration sur le test et l’étude du seuil restent pédagogiques ; en production, réserver une validation pour les choix et un test final indépendant.

## Questions et bonus

### Q1 Exactitude et F1

Nos mesures Orange (API Python) donnent au kNN une exactitude de 0.904, mais un F1 fraude de 0.478261. Cette différence vient du déséquilibre : la classe 0 représente 0.8864 des transactions. Une prédiction toujours égale à zéro atteint donc cette exactitude, avec un rappel et un F1 fraude nuls. Le kNN brut ne retrouve que 0.387324 des fraudes du test. L’exactitude masque ainsi une grande partie des erreurs qui intéressent la banque. Le kNN compare des distances ; montant, dont la médiane mesurée vaut 476.55, possède une échelle beaucoup plus grande que nuit, binaire, et peut dominer anciennete ou freq_24h. Les voisinages reflètent alors surtout le montant. La standardisation apprise uniquement sur l’apprentissage rééquilibre les attributs continus. Notre F1 passe à 0.779783 et le rappel à 0.760563. Cette amélioration observée justifie le prétraitement, sans garantir sa pertinence pour toutes les distributions futures. Les arbres reposent davantage sur des seuils que sur des distances et sont donc moins sensibles aux unités.

### Q2 Reproductibilité

Fixer les graines permet d’attribuer une différence de score à une modification identifiable. Notre forêt Orange (API Python) obtient un F1 de 0.812950 avec dix arbres puis 0.833333 avec cent arbres, sur exactement le même test. Le code installé montre que Replicable training transmet random_state=0. Sans graine, les tirages de lignes et d’attributs changeraient : on pourrait retenir un modèle simplement favorisé par le hasard. Nous n’avons pas mesuré ici une forêt non déterministe ; les variations citées dans l’énoncé restent des valeurs attendues non reproduites. En MLOps, cette variabilité complique audit, débogage, comparaison et contrôles de non régression en intégration continue. Dans KNIME, il faut cocher Use static random seed ; dans scikit-learn, renseigner random_state ; dans FLAML, seed. Nous utilisons aussi la graine 42 pour les partages et la validation croisée Orange. Une graine ne suffit toutefois pas à reproduire des versions différentes : dépendances, données, paramètres, parallélisme et budget temps doivent également être consignés.

### Q3 Coût des erreurs et seuil

La matrice mesurée avec Orange (API Python) contient 29 fraudes manquées et 15 fausses alertes, pour 113 fraudes détectées. Une fraude manquée expose généralement la banque à une perte financière ; une fausse alerte provoque de la friction client et mobilise des analystes. Nous ne disposons pas de coûts métier chiffrés : affirmer un coût total serait inventer une information. Le volume d’alertes peut aussi saturer le traitement et rendre certaines fraudes moins visibles. Abaisser le seuil de décision favorise le rappel. Nous avons réellement recalculé les prédictions GB avec un seuil de 0,3 au lieu de 0,5 : la matrice devient [[1078,30],[16,126]], le rappel atteint 0.887324 et le F1 0.845638. Nous récupérons donc 13 fraudes supplémentaires, mais ajoutons 15 fausses alertes. Ce seuil illustre le compromis et n’est pas une recommandation de production. Il faut choisir le seuil sur validation selon les coûts et la capacité des équipes, puis vérifier sur un test indépendant. Les probabilités, les pondérations de classes et ROC Analysis avec coûts FP/FN aident cette décision.

### Q4 Déclarer la cible

Dans le workflow KNIME décrit par l’énoncé, fraude est lue comme un entier par CSV Reader. Les Learners de classification demandent une cible nominale : Number to String convertit uniquement cette colonne en catégories textuelles « 0 » et « 1 ». Une cible numérique peut être absente de Target column ou empêcher la configuration du nœud. Convertir tous les attributs serait une erreur différente, car montant et les compteurs perdraient leur représentation quantitative. Dans Orange, le geste équivalent consiste à choisir Role=target et Type=categorical dans File, puis Apply. Notre domaine Orange (API Python) comporte bien quatre attributs, dont nuit catégorielle, et une cible fraude discrète ; le partage testé contient 568 fraudes au total. Si l’on conserve une cible continue, les widgets compatibles sélectionnent la régression et Test and Score propose notamment MSE/RMSE ; certains Learners exclusivement classificatoires peuvent refuser les données. Le contrôle du type et du rôle doit donc précéder toute lecture de F1. Cette vérification a été répétée lors de la recharge du workflow généré.

### Q5 Deux environnements visuels

Orange recalcule les widgets lorsque les données ou les paramètres changent. Dans notre reproduction Orange (API Python), Test and Score entraîne les cinq Learners sur 3750 lignes et évalue leurs prédictions sur 1250 autres. Pour un débutant, cette interaction facilite l’exploration : le passage du F1 kNN de 0.478 à 0.780 devient immédiatement interprétable. Elle peut toutefois masquer les entraînements déclenchés et rendre le protocole difficile à suivre sans annotations. Selon le fonctionnement décrit dans l’énoncé, KNIME demande une exécution explicite ; les feux signalent configuration, préparation et exécution. Learner et Predictor sont séparés, ce qui rend visibles le modèle appris et les données auxquelles il s’applique. Le workflow est plus long à construire, mais cette explicitation aide à organiser les contrôles et la maintenance en équipe. Les possibilités de partage via Hub et de déploiement présenté dans le bonus favorisent un processus plus structuré, sans assurer seules sa gouvernance. Nous n’avons pas manipulé l’interface KNIME : cette comparaison d’usage doit être complétée par les observations personnelles de l’étudiant.

### Q6 Outils visuels et mise en production

Notre Gradient Boosting atteint 0.837037 de F1 avec Orange (API Python). La référence FLAML réellement exécutée en Python, de provenance simulation scikit-learn, retient xgboost avec un F1 externe de 0.858238. Les tests diffèrent : ces valeurs n’établissent pas une supériorité universelle. La valeur TP2 de 0,8669 reste une valeur attendue de l’énoncé, non reproduite. Les outils visuels gardent un intérêt pour apprendre, expliquer et prototyper avec des utilisateurs peu familiers du code. Orange sert l’exploration rapide ; KNIME explicite les étapes d’un processus ; FLAML et le code facilitent l’automatisation, les tests et l’intégration MLOps. Pour produire fraude-gb.pkcls, nous avons sauvegardé un vrai modèle et vérifié sa recharge. Cela reste insuffisant pour la production du TP05 : il faut figer les dépendances, notamment Orange, conserver le prétraitement dans le pipeline, définir un contrat de données, exposer une API de serving, ajouter tests et conteneurisation, enregistrer les versions dans un registre tel que MLflow, puis surveiller erreurs et dérive. Le seuil, sa justification métier et sa procédure de révision doivent aussi être gérés.

### B2 Validation croisée et test fixe

Avec Orange (API Python), notre F1 GB est 0.837037 sur le test fixe et 0.818011 en validation croisée stratifiée à cinq plis. La régression logistique passe de 0.781022 à 0.743786. Le test fixe entraîne chaque modèle sur 3750 lignes et le juge sur les mêmes 1250 lignes réservées. La validation croisée réentraîne cinq modèles par algorithme : chacun apprend sur 4000 lignes et prédit les 1000 lignes de son pli. Chaque transaction est ainsi évaluée une fois hors apprentissage. Le protocole et la taille d’apprentissage changent ; la difficulté des observations aussi. Le code de scoring Orange calcule ici le F1 sur les prédictions hors pli regroupées. La moyenne des cinq F1 GB vaut 0.818148, légèrement différente du score agrégé ; les deux sont archivés. La CV décrit la variabilité entre plis, mais les ensembles d’apprentissage se recouvrent : elle ne crée pas cinq expériences indépendantes. On ne doit donc pas interpréter l’écart au test fixe comme une dégradation certaine du modèle.

### B3 Prédictions et courbes ROC

Sur notre test fixe avant amélioration, le kNN a la plus faible AUC, 0.825183, contre 0.989078 pour Gradient Boosting, selon Orange (API Python). Ses distances dominées par les grandes échelles produisent un classement moins pertinent des transactions. Après standardisation, son AUC atteint 0.964137 ; Tree devient alors le plus faible globalement, avec 0.845109. Préciser avant ou après est indispensable pour répondre honnêtement à la question. Dans la CV après amélioration, Tree possède aussi la plus faible AUC, 0.800720. Une courbe peut croiser une autre : « la plus basse » désigne ici la plus faible aire globale, pas une domination à chaque seuil. La ROC compare rappel et taux de faux positifs quand le seuil varie ; elle ne donne pas directement le coût des alertes dans une population déséquilibrée. Predictions permet d’inspecter les probabilités individuelles de classe 1 et les erreurs. Nos figures représentent les calculs Python, sans remplacer la capture Orange. Le workflow relie effectivement le modèle GB et les 1250 transactions réservées à Predictions.

### B1 AutoML KNIME optionnel

[À FAIRE PAR L'ÉTUDIANT] : composant AutoML de classification publié par KNIME sur le Community Hub, branché après Number to String. Cible fraude, classe positive 1, F-measure si proposée ; désactiver Keras et H2O, exécuter puis capturer le classement réel. Son partage propre 80/20 empêche une comparaison directe avec le test 75/25. Aucun score B1 simulé. Voir guide_knime.md.

![ROC après amélioration — reproduction Python, ne remplace pas la capture](../figures/orange_roc_apres.png)

## Traçabilité et travail restant

Sources : PDF fourni (15 pages), scripts versionnés, reports/donnees_validation.json, orange_resultats.json, orange_workflow_validation.json, knime_simulation_resultats.json, flaml_resultats.json et prédictions CSV associées. Les sources Orange installées sont archivées avec leurs empreintes. Toutes les graines et versions utiles sont conservées. Les Captures 1 à 5, les F1 KNIME réels, le temps humain et l’export .knwf restent [À FAIRE PAR L'ÉTUDIANT]. Voir A_FAIRE_MANUELLEMENT.md avant le rendu final. Remplir l’identité, reformuler les observations, insérer les captures et exporter au nom demandé par l’énoncé.
