# Comparatif des approches

F1 = classe 1 (fraude). Provenances : Orange (API Python) ; simulation scikit-learn pour KNIME et référence FLAML exécutée en Python. La recherche FLAML est réelle ; les chiffres KNIME sont uniquement simulés.

| Approche | Meilleur modele | F1 classe 1 | Jeu de test | Temps humain | Graine fixee ? | Export du modele |
|---|---|---|---|---|---|---|
| FLAML 60 s (TP04) | xgboost | 0.858238 | 1 250 l., 134 fraudes | [À REMPLIR] | seed=42 | MLflow (référence TP04 ; non produit ici) |
| Orange, avant ameliorat. | Gradient Boosting | 0.837037 | 1 250 l., 142 fraudes | [À REMPLIR] | Sampler=42 ; modèles selon sources | .pkcls |
| Orange, apres ameliorat. | Gradient Boosting | 0.837037 | 1 250 l., 142 fraudes | [À REMPLIR] | Sampler=42 ; modèles selon sources | .pkcls |
| KNIME | Gradient Boosting (sim.) ; [À REMPLIR après exécution KNIME] | 0.813433 (sim.) ; [À REMPLIR après exécution KNIME] | 1 250 l., 142 fraudes (sim.) | [À REMPLIR] | 42 (sim.) ; [À REMPLIR après exécution KNIME] | .knwf [À FAIRE PAR L'ÉTUDIANT] |

## Dans quel contexte recommander chaque approche

Orange convient à un premier apprentissage visuel et à une exploration interactive rapide.  
KNIME convient à la construction de traitements explicites et réutilisables par une équipe métier et données.  
FLAML convient à une recherche automatisée intégrée dans un projet Python reproductible.  
Un projet industrialisé doit ajouter tests, service de prédiction, suivi des versions et surveillance des dérives.  
Le choix dépend du public, du coût des erreurs et de la maintenance, au-delà du seul classement F1.

## Précautions de comparaison

FLAML utilise un test non stratifié ; Orange et KNIME utilisent des partages stratifiés propres à leurs outils. La simulation KNIME utilise le tirage scikit-learn, qui ne prouve pas l’identité des lignes KNIME. On compare des ordres de grandeur : un écart de 1 à 2 centièmes ne constitue pas une différence significative démontrée. Aucun test statistique de significativité n’a été réalisé. Le budget de 60 s et la machine influencent FLAML. La sélection exploratoire après consultation du test est pédagogique ; une production demanderait un test final indépendant.
