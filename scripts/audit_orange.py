"""Archiver les sources réellement installées utiles à la fidélité des widgets."""
import hashlib
import importlib.metadata
from pathlib import Path
import Orange
from commun import ROOT, sauvegarde

base = Path(Orange.__file__).parent
fichiers = [
    'widgets/data/owdatasampler.py', 'widgets/evaluate/owtestandscore.py',
    'widgets/model/owsavemodel.py', 'widgets/model/owlogisticregression.py',
    'widgets/model/owknn.py', 'widgets/model/owtree.py',
    'widgets/model/owrandomforest.py', 'widgets/model/owgradientboosting.py',
    'classification/logistic_regression.py', 'classification/knn.py',
    'classification/tree.py', 'classification/random_forest.py',
    'classification/gb.py', 'preprocess/preprocess.py', 'evaluation/testing.py',
    'base.py', 'modelling/base.py', 'evaluation/scoring.py',
    'widgets/data/owpreprocess.py', 'widgets/utils/owlearnerwidget.py',
]
extraits, manifeste = [], {}
for relatif in fichiers:
    chemin = base / relatif
    if not chemin.exists():
        raise FileNotFoundError(chemin)
    contenu = chemin.read_text(encoding='utf-8')
    manifeste[relatif] = hashlib.sha256(chemin.read_bytes()).hexdigest()
    extraits.append(f'## {relatif}\n\n```python\n{contenu}\n```\n')
(ROOT / 'reports/orange_sources_installees.md').write_text(
    '# Sources Orange installées consultées\n\nOrange (API Python), version ' + Orange.__version__ +
    '. Sources locales archivées pour rendre les réglages auditables.\n\n' + '\n'.join(extraits), encoding='utf-8')
sauvegarde('orange_sources_manifest.json', {'orange': Orange.__version__, 'sha256': manifeste})
print('Sources Orange archivées :', len(manifeste))
