from vecs_io import *
from pq_residual import *
from sorter import *
from run import execute


if __name__ == '__main__':
    import sys
    dataset = sys.argv[1]
    topk = int(sys.argv[2])
    codebook = int(sys.argv[3])
    Ks = int(sys.argv[4])
    method = 'kmeans' if len(sys.argv) <= 5 else sys.argv[5]

    X, Q, G = loader(dataset, topk, 'product')
    # pq, rq, or component of norm-pq
    pqs = [PQ(M=7, Ks=Ks) for _ in range(1)]
    quantizer = ResidualPQ(pqs=pqs)
    quantizer = NormPQ(n_percentile=codebook, quantize=quantizer, method=method)
    execute(quantizer, X, Q, G, 'product')
