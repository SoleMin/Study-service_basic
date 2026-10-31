"""작은 MLP를 합성 데이터로 학습하고 모델을 outputs/ 에 저장하는 예제.

인터넷 없이도 돌아가도록 데이터셋을 직접 생성한다.
환경변수로 하이퍼파라미터를 바꿀 수 있다 (docker run -e EPOCHS=20 ...).
"""
import os
from pathlib import Path

import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

EPOCHS = int(os.getenv("EPOCHS", "10"))
LR = float(os.getenv("LR", "1e-2"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "64"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "/app/outputs"))


def make_data(n=2000, seed=0):
    # 2차원 점이 원 안에 있으면 1, 밖에 있으면 0인 이진 분류 문제
    g = torch.Generator().manual_seed(seed)
    x = torch.rand(n, 2, generator=g) * 2 - 1
    y = (x.pow(2).sum(dim=1) < 0.5).long()
    return TensorDataset(x, y)


def main():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"torch {torch.__version__} | device: {device}")

    loader = DataLoader(make_data(), batch_size=BATCH_SIZE, shuffle=True)
    model = nn.Sequential(nn.Linear(2, 32), nn.ReLU(), nn.Linear(32, 2)).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    loss_fn = nn.CrossEntropyLoss()

    for epoch in range(1, EPOCHS + 1):
        total_loss, correct, count = 0.0, 0, 0
        for x, y in loader:
            x, y = x.to(device), y.to(device)
            logits = model(x)
            loss = loss_fn(logits, y)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * len(y)
            correct += (logits.argmax(dim=1) == y).sum().item()
            count += len(y)
        print(f"epoch {epoch:2d} | loss {total_loss / count:.4f} | acc {correct / count:.3f}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / "model.pt"
    torch.save(model.state_dict(), path)
    print(f"saved model to {path}")


if __name__ == "__main__":
    main()
