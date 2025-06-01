import torch.nn as nn

class ContradictionNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc = nn.Sequential(
            nn.Linear(768, 256),
            nn.ReLU(),
            nn.Linear(256, 1)
        
    def forward(self, emb1, emb2):
        diff = torch.abs(emb1 - emb2)
        return torch.sigmoid(self.fc(diff))
