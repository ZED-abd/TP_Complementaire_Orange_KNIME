# Contrôle du compte rendu Word

Le fichier `Nom_Prénom_Filière_Groupe_TP_lowcode.docx` a été créé avec python-docx, rechargé et contrôlé structurellement : archive OOXML valide, six tableaux, deux figures Python, trois sections, cinq emplacements de captures et placeholders d’identité. Les questions contiennent chacune entre 120 et 200 mots.

Le rendu a été tenté avec le script `render_docx.py` fourni par la compétence documents, en utilisant le Python du runtime documentaire. Erreur exacte :

```text
FileNotFoundError: LibreOffice soffice.exe was not found on PATH
```

Le runtime Windows ne fournit pas ici de LibreOffice, et aucune commande soffice n’a été trouvée. Aucun PDF ni PNG du Word n’a donc été obtenu ; **la vérification visuelle de toutes les pages n’est pas validée**. Le contrôle des figures matplotlib ne remplace pas cette vérification du document.

**[À FAIRE PAR L'ÉTUDIANT]** : ouvrir le Word, vérifier les sauts de page, la table comparative en paysage, les tableaux de scores, les figures et légendes, puis réexaminer toutes les pages après insertion des Captures 1 à 5 et de l’identité. Exporter le PDF depuis Word si ce format est choisi.

Le Word portant le nom générique imposé est volontairement ignoré par Git selon la règle `Nom_Prénom_*.docx`. Son contenu Markdown et les scripts de reconstruction sont versionnés. Il est présent localement dans reports/. Le script `scripts/valide_compte_rendu.py` contrôle la structure et maintient explicitement le statut de rendu visuel non validé.
