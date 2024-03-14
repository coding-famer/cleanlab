# Copyright (C) 2017-2024  Cleanlab Inc.
# This file is part of cleanlab.
#
# cleanlab is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cleanlab is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with cleanlab.  If not, see <https://www.gnu.org/licenses/>.


from typing import Optional, cast

import numpy as np
from scipy.sparse import csr_matrix
from sklearn.neighbors import NearestNeighbors
from sklearn.exceptions import NotFittedError
from sklearn.utils.validation import check_is_fitted


def _knn_shapley_score(knn_graph: csr_matrix, labels: np.ndarray, k: int) -> np.ndarray:
    """Compute the Shapley values of data points based on a knn graph."""
    N = labels.shape[0]
    scores = np.zeros((N, N))
    dist = knn_graph.indices.reshape(N, -1)

    for y, s, dist_i in zip(labels, scores, dist):
        idx = dist_i[::-1]
        ans = labels[idx]
        s[idx[k - 1]] = float(ans[k - 1] == y)
        ans_matches = (ans == y).flatten()
        for j in range(k - 2, -1, -1):
            s[idx[j]] = s[idx[j + 1]] + float(int(ans_matches[j]) - int(ans_matches[j + 1]))
    return 0.5 * (np.mean(scores / k, axis=0) + 1)


def _process_knn_graph_from_features(
    features: np.ndarray, metric: Optional[str], k: int = 10
) -> csr_matrix:
    """Calculate the knn graph from the features if it is not provided in the kwargs."""
    if k > len(features):  # Ensure number of neighbors less than number of examples
        raise ValueError(
            f"Number of nearest neighbors k={k} cannot exceed the number of examples N={len(features)} passed into the estimator (knn)."
        )
    if metric == None:
        metric = "cosine" if features.shape[1] > 3 else "euclidean"
    knn = NearestNeighbors(n_neighbors=k, metric=metric).fit(features)
    knn_graph = knn.kneighbors_graph(mode="distance")
    try:
        check_is_fitted(knn)
    except NotFittedError:
        knn.fit(features)
    return knn_graph


def data_shapley_knn(
    labels: np.ndarray,
    knn_graph: Optional[csr_matrix] = None,
    features: Optional[np.ndarray] = None,
    metric: Optional[str] = None,
    k: int = 10,
) -> np.ndarray:
    """Compute the Shapley values of data points based on a knn graph.
    Based on KNN-Shapley value described in https://arxiv.org/abs/1911.07128
    The larger the score, the more valuable the data point is, the more contribution it will make to the model's training.

    Parameters
    ----------
    labels: np.ndarray
        The labels of the data points.
    features: np.ndarray
    knn_graph : csr_matrix
        A sparse matrix representing the knn graph.
    metric: str
        The metric to use when constructing knn.
    k: int
        The number of nearest neighbors to consider.
    """
    if knn_graph is None and features is None:
        raise ValueError("Either knn_graph or features must be provided.")

    if knn_graph is None:
        knn_graph = _process_knn_graph_from_features(cast(np.ndarray, features), metric, k)
    return _knn_shapley_score(knn_graph, labels, k)