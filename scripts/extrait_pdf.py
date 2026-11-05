"""Phase 0 : extraire intégralement le PDF fourni, sans OCR ni reformulation."""
from pathlib import Path
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
reader = PdfReader(ROOT / 'TP_Complementaire_Orange_KNIME.pdf')
text = '\n\n'.join(f'--- PAGE {i + 1} ---\n{page.extract_text()}'
                    for i, page in enumerate(reader.pages))
(ROOT / 'reports').mkdir(exist_ok=True)
(ROOT / 'reports/enonce_texte.txt').write_text(text, encoding='utf-8')
assert len(reader.pages) == 15 and 'Annexe A' in text and 'Question 6' in text
print(f'{len(reader.pages)} pages extraites vers reports/enonce_texte.txt')
