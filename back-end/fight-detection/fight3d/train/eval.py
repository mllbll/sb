from __future__ import annotations

import torch


def compute_metrics(y_true, y_pred) -> dict:
    """Compute binary classification metrics for Fight(1) vs NonFight(0).

    Returns:
      - acc
      - precision_fight, recall_fight, f1_fight
      - confusion_matrix: [[tn, fp], [fn, tp]]
    """
    yt = torch.as_tensor(y_true).detach().to("cpu").long().flatten()
    yp = torch.as_tensor(y_pred).detach().to("cpu").long().flatten()
    if yt.numel() != yp.numel():
        raise ValueError("y_true and y_pred must have same length")

    tn = int(((yt == 0) & (yp == 0)).sum().item())
    fp = int(((yt == 0) & (yp == 1)).sum().item())
    fn = int(((yt == 1) & (yp == 0)).sum().item())
    tp = int(((yt == 1) & (yp == 1)).sum().item())

    total = tn + fp + fn + tp
    acc = (tp + tn) / total if total > 0 else 0.0

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    return {
        "acc": float(acc),
        "precision_fight": float(precision),
        "recall_fight": float(recall),
        "f1_fight": float(f1),
        "confusion_matrix": [[tn, fp], [fn, tp]],
    }

