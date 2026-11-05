"""Phase 8 : construire le Word français avec python-docx depuis le Markdown.

Le rendu visuel doit ensuite être vérifié ; aucune capture d’interface n’est créée.
"""
from pathlib import Path
import re
from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.enum.section import WD_SECTION_START, WD_ORIENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parents[1]

def nettoyer(texte):
    return texte.replace('**', '').replace('`', '')

def section(doc, paysage=False):
    sec = doc.add_section(WD_SECTION_START.NEW_PAGE)
    sec.orientation = WD_ORIENT.LANDSCAPE if paysage else WD_ORIENT.PORTRAIT
    sec.page_width, sec.page_height = (Cm(29.7), Cm(21)) if paysage else (Cm(21), Cm(29.7))
    sec.top_margin = sec.bottom_margin = Cm(1.8)
    sec.left_margin = sec.right_margin = Cm(2)

def main():
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21), Cm(29.7)
    sec.top_margin = sec.bottom_margin = Cm(1.8)
    sec.left_margin = sec.right_margin = Cm(2)
    normal = doc.styles['Normal']
    normal.font.name, normal.font.size = 'Calibri', Pt(10.5)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.08
    for nom, taille in [('Title',24),('Heading 1',16),('Heading 2',13),('Heading 3',11)]:
        s = doc.styles[nom]
        s.font.name, s.font.size, s.font.color.rgb = 'Calibri', Pt(taille), RGBColor(0,0,0)
        s.paragraph_format.keep_with_next = True
        s.paragraph_format.space_before = Pt(12)
        s.paragraph_format.space_after = Pt(6)
    doc.core_properties.author = '[NOM] [PRÉNOM]'
    doc.core_properties.title = 'Détection de fraude avec Orange et KNIME'
    doc.core_properties.subject = 'TP complémentaire EMSI 5IASD'
    lignes = (ROOT / 'reports/compte_rendu.md').read_text(encoding='utf-8').splitlines()
    i, paysage = 0, False
    while i < len(lignes):
        l = lignes[i].strip()
        if not l:
            i += 1
            continue
        if l.startswith('#'):
            niveau = len(l) - len(l.lstrip('#'))
            titre = nettoyer(l[niveau:].strip())
            if paysage:
                section(doc, False)
                paysage = False
            if titre == 'Tableau de synthèse':
                section(doc, True)
                paysage = True
            doc.add_paragraph(titre, style='Title' if i == 0 else f'Heading {min(niveau,3)}')
        elif l.startswith('|'):
            rows = []
            while i < len(lignes) and lignes[i].strip().startswith('|'):
                row = [nettoyer(c.strip()) for c in lignes[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r':?-+:?', c or 'x') for c in row):
                    rows.append(row)
                i += 1
            table = doc.add_table(rows=1, cols=len(rows[0]))
            table.style = 'Table Grid'
            largeur = 25.7 if paysage else 17.0
            for j, cell in enumerate(table.rows[0].cells):
                cell.text = rows[0][j]
                cell.width = Cm(largeur/len(rows[0]))
                for run in cell.paragraphs[0].runs:
                    run.bold = True
            trpr = table.rows[0]._tr.get_or_add_trPr()
            repeat = OxmlElement('w:tblHeader')
            trpr.append(repeat)
            for valeurs in rows[1:]:
                cells = table.add_row().cells
                for j, cell in enumerate(cells):
                    cell.text = valeurs[j]
                    cell.width = Cm(largeur/len(rows[0]))
            for row in table.rows:
                for cell in row.cells:
                    for p in cell.paragraphs:
                        p.paragraph_format.space_after = Pt(4)
                        for run in p.runs:
                            run.font.size = Pt(9)
            doc.add_paragraph()
            continue
        elif l.startswith('!['):
            match = re.match(r'!\[(.*?)\]\((.*?)\)', l)
            if match:
                chemin = (ROOT / 'reports' / match.group(2)).resolve()
                p = doc.add_paragraph()
                p.add_run().add_picture(str(chemin), width=Cm(15.5))
                p.paragraph_format.keep_with_next = True
                doc.add_paragraph(match.group(1), style='Caption')
        else:
            style = 'List Bullet' if l.startswith('- ') else None
            p = doc.add_paragraph(nettoyer(l[2:] if style else l), style=style)
            if l.startswith('[CAPTURE'):
                p.paragraph_format.space_before = Pt(10)
                p.paragraph_format.space_after = Pt(12)
                for run in p.runs:
                    run.bold = True
                    run.font.color.rgb = RGBColor(130,60,0)
        i += 1
    for sec in doc.sections:
        p = sec.footer.paragraphs[0]
        p.alignment = 2
        if not p.text:
            p.add_run('Page ')
            field = OxmlElement('w:fldSimple')
            field.set(qn('w:instr'), 'PAGE')
            p._p.append(field)
    sortie = ROOT / 'reports/Nom_Prénom_Filière_Groupe_TP_lowcode.docx'
    doc.save(sortie)
    controle = Document(sortie)
    contenu = '\n'.join(p.text for p in controle.paragraphs)
    assert all(f'[CAPTURE {n} À INSÉRER' in contenu for n in range(1,6))
    assert all(tag in contenu for tag in ['[NOM]', '[PRÉNOM]', '[FILIÈRE]', '[GROUPE]'])
    print(f'Word créé et rechargé : {sortie.name}, {len(controle.tables)} tableaux. Contrôle visuel distinct requis.')

if __name__ == '__main__':
    main()
