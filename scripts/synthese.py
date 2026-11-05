"""Phase 6 : comparaison à partir des seules mesures persistées."""
import json
from commun import ROOT

def main():
    orange = json.loads((ROOT / 'reports/orange_resultats.json').read_text(encoding='utf-8'))
    knime = json.loads((ROOT / 'reports/knime_simulation_resultats.json').read_text(encoding='utf-8'))
    flaml = json.loads((ROOT / 'reports/flaml_resultats.json').read_text(encoding='utf-8'))
    avant = max(orange['avant'], key=lambda k: orange['avant'][k]['F1'])
    apres = max(orange['apres'], key=lambda k: orange['apres'][k]['F1'])
    sim = max(knime['resultats'], key=lambda k: knime['resultats'][k]['F1'])
    texte = '# Comparatif des approches\n\n'
    texte += 'F1 = classe 1 (fraude). Provenances : Orange (API Python) ; simulation scikit-learn pour KNIME et référence FLAML exécutée en Python. '
    texte += 'La recherche FLAML est réelle ; les chiffres KNIME sont uniquement simulés.\n\n'
    texte += '| Approche | Meilleur modele | F1 classe 1 | Jeu de test | Temps humain | Graine fixee ? | Export du modele |\n'
    texte += '|---|---|---|---|---|---|---|\n'
    texte += f"| FLAML 60 s (TP04) | {flaml['meilleur_modele']} | {flaml['resultats']['F1']:.6f} | 1 250 l., 134 fraudes | [À REMPLIR] | seed=42 | MLflow (référence TP04 ; non produit ici) |\n"
    texte += f"| Orange, avant ameliorat. | {avant} | {orange['avant'][avant]['F1']:.6f} | 1 250 l., 142 fraudes | [À REMPLIR] | Sampler=42 ; modèles selon sources | .pkcls |\n"
    texte += f"| Orange, apres ameliorat. | {apres} | {orange['apres'][apres]['F1']:.6f} | 1 250 l., 142 fraudes | [À REMPLIR] | Sampler=42 ; modèles selon sources | .pkcls |\n"
    texte += f"| KNIME | {sim} (sim.) ; [À REMPLIR après exécution KNIME] | {knime['resultats'][sim]['F1']:.6f} (sim.) ; [À REMPLIR après exécution KNIME] | 1 250 l., 142 fraudes (sim.) | [À REMPLIR] | 42 (sim.) ; [À REMPLIR après exécution KNIME] | .knwf [À FAIRE PAR L'ÉTUDIANT] |\n\n"
    texte += '## Dans quel contexte recommander chaque approche\n\n'
    texte += 'Orange convient à un premier apprentissage visuel et à une exploration interactive rapide.  \n'
    texte += 'KNIME convient à la construction de traitements explicites et réutilisables par une équipe métier et données.  \n'
    texte += 'FLAML convient à une recherche automatisée intégrée dans un projet Python reproductible.  \n'
    texte += 'Un projet industrialisé doit ajouter tests, service de prédiction, suivi des versions et surveillance des dérives.  \n'
    texte += 'Le choix dépend du public, du coût des erreurs et de la maintenance, au-delà du seul classement F1.\n\n'
    texte += '## Précautions de comparaison\n\n'
    texte += 'FLAML utilise un test non stratifié ; Orange et KNIME utilisent des partages stratifiés propres à leurs outils. '
    texte += 'La simulation KNIME utilise le tirage scikit-learn, qui ne prouve pas l’identité des lignes KNIME. '
    texte += 'On compare des ordres de grandeur : un écart de 1 à 2 centièmes ne constitue pas une différence significative démontrée. '
    texte += 'Aucun test statistique de significativité n’a été réalisé. Le budget de 60 s et la machine influencent FLAML. '
    texte += 'La sélection exploratoire après consultation du test est pédagogique ; une production demanderait un test final indépendant.\n'
    (ROOT / 'reports/comparatif.md').write_text(texte, encoding='utf-8')
    assert texte.count('[À REMPLIR]') >= 4
    print('Comparatif créé à partir des trois fichiers JSON de mesures.')

if __name__ == '__main__':
    main()
