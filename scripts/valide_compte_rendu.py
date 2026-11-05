"""Contrôles structurels du Word ; ne prétend pas valider son rendu visuel."""
import json
from pathlib import Path
from zipfile import ZipFile
from docx import Document

ROOT=Path(__file__).resolve().parents[1]

def main():
    path=ROOT/'reports/Nom_Prénom_Filière_Groupe_TP_lowcode.docx'
    doc=Document(path)
    with ZipFile(path) as z:
        assert z.testzip() is None
        assert len([n for n in z.namelist() if n.startswith('word/media/')]) == 2
    paragraphs='\n'.join(p.text for p in doc.paragraphs)
    assert all(f'[CAPTURE {n} À INSÉRER' in paragraphs for n in range(1,6))
    assert all(p in paragraphs for p in ['[NOM]','[PRÉNOM]','[FILIÈRE]','[GROUPE]'])
    assert len(doc.tables) == 6 and len(doc.sections) == 3
    assert 'simulation scikit-learn' in paragraphs
    assert '0.837037' in '\n'.join(c.text for t in doc.tables for r in t.rows for c in r.cells)
    assert not any(p._p.xpath('./w:pPr/w:pBdr') for p in doc.paragraphs if p.style.name=='Title')
    result={'structure_validee':True,'tableaux':6,'figures_reproduction_python':2,
            'sections':3,'captures_reelles_inserees':0,'placeholders_identite':True,
            'controle_visuel_valide':False,
            'erreur_rendu_exacte':'FileNotFoundError: LibreOffice soffice.exe was not found on PATH',
            'action':'[À FAIRE PAR L\'ÉTUDIANT] : ouvrir dans Word, vérifier toutes les pages et exporter après insertion des captures.'}
    (ROOT/'reports/compte_rendu_validation.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
