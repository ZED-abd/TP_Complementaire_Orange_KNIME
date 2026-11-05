"""Utilitaires de provenance, métriques binaires et figures reproductibles."""
from pathlib import Path
import hashlib
import json
import platform
import numpy as np
from sklearn.metrics import (roc_auc_score, accuracy_score, f1_score,
                             precision_score, recall_score, confusion_matrix)

ROOT = Path(__file__).resolve().parents[1]

def sauvegarde(nom, contenu):
    (ROOT / 'reports' / nom).write_text(json.dumps(contenu, indent=2, ensure_ascii=False), encoding='utf-8')

def mesures(y, pred, prob):
    y, pred = np.asarray(y).ravel(), np.asarray(pred).ravel()
    return {'AUC': float(roc_auc_score(y, prob)), 'CA': float(accuracy_score(y, pred)),
            'F1': float(f1_score(y, pred, pos_label=1, zero_division=0)),
            'Prec': float(precision_score(y, pred, pos_label=1, zero_division=0)),
            'Recall': float(recall_score(y, pred, pos_label=1, zero_division=0)),
            'matrice': confusion_matrix(y, pred, labels=[0, 1]).tolist()}

def provenance(source):
    import sklearn
    return {'source': source, 'python': platform.python_version(), 'numpy': np.__version__,
            'scikit_learn': sklearn.__version__,
            'donnees_sha256': hashlib.sha256((ROOT / 'data/transactions.csv').read_bytes()).hexdigest()}

def table_mesures(resultats):
    lignes = ['| Modèle | AUC | CA | F1 classe 1 | Précision 1 | Rappel 1 |',
              '|---|---|---|---|---|---|']
    for nom, m in resultats.items():
        lignes.append('| ' + nom + ' | ' + ' | '.join(f'{m[k]:.6f}' for k in ['AUC','CA','F1','Prec','Recall']) + ' |')
    return '\n'.join(lignes)

def figure_matrice(matrice, titre, chemin):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from sklearn.metrics import ConfusionMatrixDisplay
    fig, ax = plt.subplots(figsize=(6.4, 4.8))
    ConfusionMatrixDisplay(np.array(matrice), display_labels=['0','1']).plot(ax=ax, cmap='Blues', colorbar=False)
    ax.set(xlabel='Classe prédite', ylabel='Classe réelle', title=titre)
    fig.text(0.5, 0.02, 'Reproduction Python, ne remplace pas la capture', ha='center', fontsize=9)
    fig.tight_layout(rect=(0, .05, 1, 1))
    fig.savefig(ROOT / chemin, dpi=170)
    plt.close(fig)
