import torch
import torch.nn as nn


class Model(nn.Module):

    def __init__(self, configs, num_layers=2, hidden_size=256):
        super(Model, self).__init__()
        self.input_size = configs.seq_len
        self.hidden_size = int(getattr(configs, 'rnn_hidden_size', hidden_size))
        self.num_layers = int(getattr(configs, 'rnn_layers', num_layers))
        self.pred_len = configs.pred_len
        
        self.lstm = nn.LSTM(input_size=configs.enc_in, hidden_size=self.hidden_size,
                            num_layers=self.num_layers, batch_first=True)
        
        self.fc = nn.Linear(self.hidden_size, configs.enc_in)

    def forward(self, x, x_mark_enc=None, x_dec=None, x_mark_dec=None, mask=None):
        h_0 = x.new_zeros(self.num_layers, x.size(0), self.hidden_size)
        c_0 = x.new_zeros(self.num_layers, x.size(0), self.hidden_size)
        
        # Encode the observed history and project the final hidden states.
        ula, (h_out, _) = self.lstm(x, (h_0, c_0))
        
        out = self.fc(ula)[:,-self.pred_len:,:]
        
        return out
