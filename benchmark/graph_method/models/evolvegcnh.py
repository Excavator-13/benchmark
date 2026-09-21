import torch
from torch.nn import GRU
from torch_geometric.nn import TopKPooling
from torch_geometric_temporal.nn.recurrent.evolvegcno import GCNConv_Fixed_W
from torch_geometric.nn.inits import glorot


class EvolveGCNH(torch.nn.Module):
    r"""An implementation of the Evolving Graph Convolutional Hidden Layer.
    For details see this paper: `"EvolveGCN: Evolving Graph Convolutional
    Networks for Dynamic Graph." <https://arxiv.org/abs/1902.10191>`_

    The graph-convolution weight is recurrent state, not a module attribute:
    :meth:`forward` accepts the weight produced by the previous snapshot and
    returns the weight it produced for the next one.  Passing ``None`` for the
    first snapshot of a traversal starts from the learnable
    :attr:`initial_weight` parameter, which stays connected to autograd.  A new
    traversal must start from ``None`` again; nothing is cached on the layer, so
    state cannot leak between epochs or dataset splits.

    Args:
        num_of_nodes (int): Number of vertices.
        in_channels (int): Number of filters.
        improved (bool, optional): If set to :obj:`True`, the layer computes
            :math:`\mathbf{\hat{A}}` as :math:`\mathbf{A} + 2\mathbf{I}`.
            (default: :obj:`False`)
        cached (bool, optional): If set to :obj:`True`, the layer will cache
            the computation of :math:`\mathbf{\hat{D}}^{-1/2} \mathbf{\hat{A}}
            \mathbf{\hat{D}}^{-1/2}` on first execution, and will use the
            cached version for further executions.
            This parameter should only be set to :obj:`True` in transductive
            learning scenarios. (default: :obj:`False`)
        normalize (bool, optional): Whether to add self-loops and apply
            symmetric normalization. (default: :obj:`True`)
        add_self_loops (bool, optional): If set to :obj:`False`, will not add
            self-loops to the input graph. (default: :obj:`True`)
    """

    def __init__(
        self,
        num_of_nodes: int,
        in_channels: int,
        improved: bool = False,
        cached: bool = False,
        normalize: bool = True,
        add_self_loops: bool = True,
    ):
        super(EvolveGCNH, self).__init__()

        self.num_of_nodes = num_of_nodes
        self.in_channels = in_channels
        self.improved = improved
        self.cached = cached
        self.normalize = normalize
        self.add_self_loops = add_self_loops
        self.initial_weight = torch.nn.Parameter(torch.Tensor(in_channels, in_channels))
        self._create_layers()
        self.reset_parameters()

    def reset_parameters(self):
        glorot(self.initial_weight)

    def initial_state(self) -> torch.Tensor:
        """Return the learnable initial weight that starts a fresh traversal.

        The returned tensor is the registered parameter itself, so a loss that
        backpropagates through the first recurrent update still reaches it.
        """
        return self.initial_weight

    def _create_layers(self):

        self.ratio = self.in_channels / self.num_of_nodes

        self.pooling_layer = TopKPooling(self.in_channels, self.ratio)

        self.recurrent_layer = GRU(
            input_size=self.in_channels, hidden_size=self.in_channels, num_layers=1
        )

        self.conv_layer = GCNConv_Fixed_W(
            in_channels=self.in_channels,
            out_channels=self.in_channels,
            improved=self.improved,
            cached=self.cached,
            normalize=self.normalize,
            add_self_loops=self.add_self_loops
        )

    def _summarize(self, X: torch.Tensor) -> torch.Tensor:
        """Select exactly in_channels nodes, breaking equal scores by node order.

        Count inputs often saturate tanh at 1. PyG's unstable TopK sort then
        chooses different tied nodes on CPU and CUDA. Keep its learnable
        projection and score weighting, but use stable sorting for this single
        graph. Only pooled features are needed by the GRU, not pooled edges.
        """
        if X.shape[0] < self.in_channels:
            raise ValueError("EvolveGCNH needs at least in_channels nodes for its weight summary")
        select = self.pooling_layer.select
        score = select.act((X * select.weight).sum(dim=-1) / select.weight.norm(p=2, dim=-1))
        indices = torch.argsort(score, descending=True, stable=True)[:self.in_channels]
        return X[indices] * score[indices, None]

    def forward(
        self,
        X: torch.FloatTensor,
        edge_index: torch.LongTensor,
        edge_weight: torch.FloatTensor = None,
        previous_weight: torch.FloatTensor = None,
    ):
        """
        Making a forward pass.

        Arg types:
            * **X** *(PyTorch Float Tensor)* - Node embedding.
            * **edge_index** *(PyTorch Long Tensor)* - Graph edge indices.
            * **edge_weight** *(PyTorch Float Tensor, optional)* - Edge weight vector.
            * **previous_weight** *(PyTorch Float Tensor, optional)* - Weight state
              returned by the preceding snapshot, or :obj:`None` to start a
              traversal from :attr:`initial_weight`.

        Return types:
            * **X** *(PyTorch Float Tensor)* - Output matrix for all nodes.
            * **weight** *(PyTorch Float Tensor)* - Weight state for the next snapshot.
        """
        X_tilde = self._summarize(X)[None, :, :]

        if previous_weight is None:
            W = self.initial_weight
        else:
            W = previous_weight
        W = W[None, :, :]

        X_tilde, W = self.recurrent_layer(X_tilde, W)
        W = W.squeeze(dim=0)
        X = self.conv_layer(W, X, edge_index, edge_weight)
        return X, W
