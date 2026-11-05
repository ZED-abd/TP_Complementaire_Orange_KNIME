# Journal de validation par phase

Les preuves chiffrées sont les JSON et CSV produits par les scripts. Les graines et dépendances sont figées ; aucune valeur attendue n’est substituée à une valeur calculée.

| Phase | Contrôle effectué | Résultat et limite |
|---|---|---|
| 0 | Lecture complète, extraction pypdf, 15 pages, Annexe A et Questions 1–6 présentes | Validé ; structure et checklist créées |
| 1 | Nombre de lignes, transactions, fraudes, absence de valeurs manquantes, SHA-256 | Validé : 5001, 5000, 568 et 11,36 % ; provenance simulation scikit-learn, génération NumPy/pandas |
| 2 | Sources installées lues ; paramètres des widgets ; scores Orange comparés à calcul indépendant sur leurs prédictions ; pickle rechargé | Validé : 35 métriques conformes à l’arrondi, matrice exacte ; CV GB et LR conformes. Modèle de 141461 octets, écart de taille avec l’énoncé documenté |
| 3 | Génération API, version des réglages et sérialiseur officiel ; recharge du .ows dans WidgetsScheme ; recalcul des cinq F1 et vérification cibles/types | Validé en offscreen : 14 widgets, 16 liens, cinq F1 identiques ; aucune capture réelle, vérification visuelle manuelle |
| 4 | Inventaire KNIME sans GUI ; simulation stratifiée ; contrôle des trois matrices et F1 classe 1 | Validé pour simulation scikit-learn : 3750/1250, fraudes 426/142 ; total et lignes des matrices conformes. LR sous la plage indicative, conservée et documentée. KNIME réel reste manuel |
| 5 | FLAML 60 s seed=42 ; test externe non stratifié réservé ; effectifs et matrice | Validé : 134 fraudes test, XGBoost F1 0,858238, durée observée 60,578 s ; provenance simulation scikit-learn, recherche FLAML réelle. Configuration TP04 supposée |
| 6 | Tableau aux sept colonnes demandées ; quatre approches ; valeurs lues des JSON ; cinq lignes de conclusion | Validé ; temps humain et valeurs KNIME réelles explicitement à remplir |
| 7 | Huit réponses, comptage par espaces hors titre, références aux mesures | Validé : 157 à 172 mots par réponse |
| 8 | Compte rendu Markdown ; Word python-docx rechargé ; archive OOXML, placeholders, six tableaux, deux figures, trois sections | Contrôle structurel validé. Écart documenté : rendu visuel non validé, LibreOffice absent ; vérification manuelle nécessaire avant rendu |
| 9 | F1/matrices recalculés depuis les prédictions CSV, indices reliés au CSV source, CV complète, cohérence du workflow et des rapports, fichiers ignorés contrôlés | Voir validation_finale.json ; checklist et README mis à jour |

## Incidents résolus

- Premier accès réseau Git sous restriction : résolution DNS impossible. Vérification réseau autorisée réussie, distant vide confirmé ; main initialisée sans pull applicable.
- Manque d’espace disque : installation interrompue. Cache pip de téléchargement régénérable purgé ; installations locales reprises avec --no-cache-dir, puis pip check réussi dans les deux venv.
- Première génération .ows : métadonnée de version absente, migration indue du protocole Test and Score. Corrigé en utilisant la version effective de chaque widget.
- Sérialisation des contextes : le mode littéral seul omettait des propriétés non littérales. Corrigé avec pickle_fallback=True du sérialiseur officiel, puis recharge et recalcul complets validés avant livraison.

## Écart restant

Le rendu automatique du Word échoue : `FileNotFoundError: LibreOffice soffice.exe was not found on PATH`. Ce point est documenté dans rendu_word_limite.md et A_FAIRE_MANUELLEMENT.md. Aucun contrôle visuel du document final n’est revendiqué. Les cinq captures et l’exécution/export KNIME restent également manuels, conformément au périmètre demandé.
