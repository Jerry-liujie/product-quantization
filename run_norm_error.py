import scipy
import numpy as np
from vecs_io import *
from pq_residual import *
from sorter import *
from transformer import *
from numpy.linalg import norm as l2norm
import matplotlib.pyplot as plt


def execute(quantizer, X, Q, G, train_size=100000):
    quantizer.fit(X[:train_size], iter=20)
    compressed = quantizer.compress(X)

    mse_errors = [
        l2norm(X[i] - compressed[i])
        for i in range(len(X))
    ]

    mse_relative = [
        l2norm(X[i] - compressed[i])
        / l2norm(X[i])
        for i in range(len(X))
    ]

    norm_errors = [
        np.abs(
            l2norm(compressed[i]) - l2norm(X[i])
        )
        for i in range(len(X))
    ]

    norm_relative = [
        np.abs(
            l2norm(compressed[i]) - l2norm(X[i])
        )
        / l2norm(X[i])
        for i in range(len(X))
    ]

    return np.mean(mse_errors), np.mean(mse_relative), np.mean(norm_errors), np.mean(norm_relative)


def print_error():
    codebook = 8
    norm_book = 1
    for dataset in ['netflix', 'yahoomusic', 'imagenet', 'sift1m']:
        X, Q, G = loader(dataset, 20, 'product')
        pqs = [PQ(M=1, Ks=256, verbose=False) for _ in range(codebook)]
        pq = ResidualPQ(pqs=pqs, verbose=False)
        mse_error, mse_relative, norm_error, norm_relative = execute(pq, X, Q, G)
        print('RQ: {}, {}, {}, {}, {}'.format(dataset, mse_error, mse_relative, norm_error, norm_relative))

        pqs = [PQ(M=1, Ks=256, verbose=False) for _ in range(codebook-norm_book)]
        pq = ResidualPQ(pqs=pqs, verbose=False)
        pq = NormPQ(n_percentile=256**norm_book, quantize=pq, verbose=False)
        mse_error, mse_relative, norm_error, norm_relative = execute(pq, X, Q, G)
        print('NormRQ: {}, {}, {}, {}, {}'.format(dataset, mse_error, mse_relative, norm_error, norm_relative))


def linear_fit(x, y):
    # when
    return linear_fit_through_origin(x, y)
    from sklearn import datasets, linear_model
    from sklearn.metrics import mean_squared_error, r2_score
    # Create linear regression object
    regr = linear_model.LinearRegression()
    # Train the model using the training sets
    regr.fit(np.array(x).reshape((-1, 1)) if np.array(x).ndim == 1 else x, y)
    # Make predictions using the testing set
    y_pred = regr.predict(x)
    return x, y_pred

def linear_fit_through_origin(x, y):
    x = np.reshape(x, -1)
    y = np.reshape(y, -1)
    k = np.dot(x, y) / np.dot(x, x)
    return x, k * x

fontsize=40
ticksize=32

def linear_analyze():
    codebook = 4
    norm_book = 1
    for dataset in ['netflix', 'yahoomusic', 'imagenet', 'sift1m']:
        X, T, Q, G = loader(dataset, 20, 'product')
        quantizer = PQ(M=codebook, Ks=256, verbose=True)
        quantizer.fit(X[:100000], iter=20)
        compressed = quantizer.compress(X)

        norm_errors = [
            [np.abs(l2norm(X[i]) - l2norm(compressed[i])) / l2norm(X[i]) for i in xs]
            for q, xs in zip(Q, G)
        ]
        angular_errors = [
            [1 - np.dot(X[i], compressed[i]) / l2norm(X[i]) / l2norm(compressed[i]) for i in xs]
            for q, xs in zip(Q, G)
        ]
        ip_errors = [
            [np.abs(np.dot(X[i], q) - np.dot(compressed[i], q)) / np.dot(X[i], q) for i in xs]
            for q, xs in zip(Q, G)
        ]
        norm_errors = np.reshape(norm_errors, -1)
        angular_errors = np.reshape(angular_errors, -1)
        ip_errors = np.reshape(ip_errors, -1)

        norm_x, norm_y = linear_fit(norm_errors.reshape(-1, 1), ip_errors)
        ag_x, ag_y = linear_fit(angular_errors.reshape(-1, 1), ip_errors)
        x, y = linear_fit((angular_errors + norm_errors).reshape(-1, 1), ip_errors)

        plt.title(dataset)
        plt.plot(norm_x, norm_y, 'red', label='norm')
        plt.plot(ag_x, ag_y, 'black', label='angular')
        plt.plot(x, y, 'green', label='sum')
        plt.plot(x, x, 'yellow', label='y=x')
        plt.legend()
        plt.show()


def fit_error():
    # codebook, layer = 1, 8  # RQ
    codebook, layer = 8, 1  # PQ
    for dataset in ['sift1m']:
        X, Q, G = loader(dataset, 20, 'product')
        quantizer = ResidualPQ([PQ(M=codebook, Ks=256, verbose=True) for _ in range(layer)])
        quantizer.fit(X[:100000], iter=20)
        compressed_vec = quantizer.compress(X)
        from transformer import normalize

        compressed_norm, compressed_angular = normalize(compressed_vec)
        X_norm, X_angular = normalize(X)

        def combine_norm_angular(norms, angular):
            return (angular.transpose() * norms).transpose()

        # using compressed norm and true direction
        compressed_norm_vecs = combine_norm_angular(compressed_norm, X_angular)
        # using compressed direction and true norm
        compressed_angular_vecs = combine_norm_angular(X_norm, compressed_angular)

        compressed = compressed_norm_vecs
        # norm errors of items appear in ground truth
        norm_errors = [
            [
                np.abs(l2norm(X[i]) - l2norm(compressed[i])) / l2norm(X[i])
                for i in xs
            ]
            for q, xs in zip(Q, G)
        ]
        # errors of inner product of query and items
        norm_ip_errors = [
            [
                np.abs(np.dot(X[i], q) - np.dot(compressed[i], q))
                /
                np.abs( np.dot(X[i], q) )
                for i in xs
            ]
            for q, xs in zip(Q, G)
        ]
        norm_l2_errors = [
            [
                np.abs(np.linalg.norm(X[i] - q) - np.linalg.norm(compressed[i] - q))
                /
                np.abs(np.linalg.norm(X[i] - q))
                if np.linalg.norm(X[i] - q) > 0 else 0.0
                for i in xs
            ]
            for q, xs in zip(Q, G)
        ]

        compressed = compressed_angular_vecs
        # angular errors of items appear in ground truth
        angular_errors = [
            [
                1 - np.dot(X[i], compressed[i]) / l2norm(X[i]) / l2norm(compressed[i])
                for i in xs
            ]
            for q, xs in zip(Q, G)
        ]
        angular_ip_errors = [
            [
                np.abs(np.dot(X[i], q) - np.dot(compressed[i], q))
                /
                np.abs( np.dot(X[i], q) )
                for i in xs
            ]
            for q, xs in zip(Q, G)
        ]
        angular_l2_errors = [
            [
                np.abs(np.linalg.norm(X[i] - q) - np.linalg.norm(compressed[i] - q))
                /
                np.abs(np.linalg.norm(X[i] - q))
                if np.linalg.norm(X[i] - q) > 0 else 0.0
                for i in xs
            ]
            for q, xs in zip(Q, G)
        ]

        norm_errors = np.reshape(norm_errors, -1)
        angular_errors = np.reshape(angular_errors, -1)

        angular_ip_errors = np.reshape(angular_ip_errors, -1)
        angular_l2_errors = np.reshape(angular_l2_errors, -1)

        norm_ip_errors = np.reshape(norm_ip_errors, -1)
        norm_l2_errors = np.reshape(norm_l2_errors, -1)

        norm_x, norm_y = linear_fit(norm_errors.reshape(-1, 1), norm_ip_errors)
        ag_x, ag_y = linear_fit(angular_errors.reshape(-1, 1), angular_ip_errors)

        norm_l2_x, norm_l2_y = linear_fit(norm_errors.reshape(-1, 1), norm_l2_errors)
        ag_l2_x, ag_l2_y = linear_fit(angular_errors.reshape(-1, 1), angular_l2_errors)

        norm_r = scipy.stats.pearsonr(norm_errors, norm_ip_errors)
        angl_r = scipy.stats.pearsonr(angular_errors, angular_ip_errors)
        norm_l2_r = scipy.stats.pearsonr(norm_errors, norm_l2_errors)
        angl_l2_r = scipy.stats.pearsonr(angular_errors, angular_l2_errors)

        print("Possion relation : norm {} angular {} l2 norm {} l2 angular {}".format(
            norm_r, angl_r, norm_l2_r, angl_l2_r))

        print("norm: ", (norm_y[1] - norm_y[0]) / (norm_x[1] - norm_x[0]))  # RQ: 0.42640913 PQ: 0.509835
        print("norm: ", (norm_y[2] - norm_y[1]) / (norm_x[2] - norm_x[1]))
        print("agle", (ag_y[1] - ag_y[0]) / (ag_x[1] - ag_x[0]))
        print("agle", (ag_y[2] - ag_y[1]) / (ag_x[2] - ag_x[1]))

        plt.plot(norm_x, norm_y, 'red', label='Norm error only')
        plt.plot(ag_x, ag_y, 'black', label='Angular error only')
        plt.scatter(norm_errors, norm_ip_errors, c='pink')
        plt.scatter(angular_errors, angular_ip_errors, c='gray')
        plt.legend(loc='upper left', fontsize=ticksize)

        plt.xlabel('Error', fontsize=fontsize)
        plt.xticks(fontsize=ticksize)
        plt.ylabel('Inner Product Error', fontsize=fontsize)
        plt.yticks(fontsize=ticksize)
        plt.show()

        plt.plot(norm_l2_x, norm_l2_y, 'red', label='Norm error only')
        plt.plot(ag_l2_x, ag_l2_y, 'black', label='Angular error only')

        indices = np.random.choice(len(norm_errors), 1000)
        plt.scatter(norm_errors[indices], norm_l2_errors[indices], c='red', marker='*')
        plt.scatter(angular_errors[indices], angular_l2_errors[indices], c='gray', alpha=0.2, marker='o')

        plt.legend(loc='upper left', fontsize=ticksize)

        plt.xlabel('Error', fontsize=fontsize)
        plt.xticks(fontsize=ticksize)
        plt.ylabel('Euclidean Distance Error', fontsize=fontsize)
        plt.yticks(fontsize=ticksize)
        plt.show()


if __name__ == '__main__':
    fit_error()
