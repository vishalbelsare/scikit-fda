"""Functional Principal Component Analysis Module."""

import numpy as np
import skfda
from abc import ABC, abstractmethod
from skfda.representation.basis import FDataBasis
from skfda.representation.grid import FDataGrid
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.decomposition import PCA
from scipy.linalg import solve_triangular

__author__ = "Yujian Hong"
__email__ = "yujian.hong@estudiante.uam.es"


class FPCA(ABC, BaseEstimator, TransformerMixin):
    """Defines the common structure shared between classes that do functional
    principal component analysis

    Parameters:
        n_components (int): number of principal components to obtain from
            functional principal component analysis. Defaults to 3.
        centering (bool): if True then calculate the mean of the functional data
            object and center the data first
    """

    def __init__(self,
                 n_components=3,
                 centering=True,
                 regularization_parameter=0,
                 penalty=2):
        self.n_components = n_components
        self.centering = centering
        # lambda in the regularization / penalization process
        self.regularization_parameter = regularization_parameter
        self.penalty = penalty

    @abstractmethod
    def fit(self, X, y=None):
        """Computes the n_components first principal components and saves them
        inside the FPCA object.

        Args:
            X (FDataGrid or FDataBasis):
                the functional data object to be analysed
            y (None, not used):
                only present for convention of a fit function

        Returns:
            self (object)
        """
        pass

    @abstractmethod
    def transform(self, X, y=None):
        """Computes the n_components first principal components score and
        returns them.

        Args:
            X (FDataGrid or FDataBasis):
                the functional data object to be analysed
            y (None, not used):
                only present because of fit function convention

        Returns:
            (array_like): the scores of the data with reference to the
            principal components
        """
        pass

    def fit_transform(self, X, y=None, **fit_params):
        """Computes the n_components first principal components and their scores
        and returns them.
        Args:
            X (FDataGrid or FDataBasis):
                the functional data object to be analysed
            y (None, not used):
                only present for convention of a fit function

        Returns:
            (array_like): the scores of the data with reference to the
            principal components
        """
        self.fit(X, y)
        return self.transform(X, y)


class FPCABasis(FPCA):
    """Functional principal component analysis for functional data represented
    in basis form.

    Parameters:
        n_components (int): number of principal components to obtain from
            functional principal component analysis. Defaults to 3.
        centering (bool): if True then calculate the mean of the functional data
            object and center the data first. Defaults to True. If True the
            passed FDataBasis object is modified.
        components_basis (Basis): the basis in which we want the principal
            components. We can use a different basis than the basis contained in
            the passed FDataBasis object.
        regularization_parameter (float): this parameter determines the amount
            of smoothing applied. Defaults to 0
        penalty (Union[int, Iterable[float],'LinearDifferentialOperator']):
            Linear differential operator. If it is not a
            LinearDifferentialOperator object, it will be converted to one.
            If you input an integerthen the derivative of that degree will be
            used to regularize the principal components.

    Attributes:
        components_ (FDataBasis): this contains the principal components in a
            basis representation.
        component_values_ (array_like): this contains the values (eigenvalues)
            associated with the principal components.
        explained_variance_ratio_ (array_like): this contains the percentage of
            variance explained by each principal component.

    Examples:
        Construct an artificial FDataBasis object and run FPCA with this object.
        The resulting principal components are not compared because there are
        several equivalent possibilities.

        >>> data_matrix = np.array([[1.0, 0.0], [0.0, 2.0]])
        >>> sample_points = [0, 1]
        >>> fd = FDataGrid(data_matrix, sample_points)
        >>> basis = skfda.representation.basis.Monomial((0,1), n_basis=2)
        >>> basis_fd = fd.to_basis(basis)
        >>> fpca_basis = FPCABasis(2)
        >>> fpca_basis = fpca_basis.fit(basis_fd)

    """

    def __init__(self,
                 n_components=3,
                 components_basis=None,
                 centering=True,
                 regularization_parameter=0,
                 penalty=2):
        super().__init__(n_components, centering,
                         regularization_parameter, penalty)
        # basis that we want to use for the principal components
        self.components_basis = components_basis

    def fit(self, X: FDataBasis, y=None):
        """Computes the first n_components principal components and saves them.
        The eigenvalues associated with these principal components are also
        saved. For more details about how it is implemented please view the
        referenced book.

        Args:
            X (FDataBasis):
                the functional data object to be analysed in basis
                representation
            y (None, not used):
                only present for convention of a fit function

        Returns:
            self (object)

        References:
            .. [RS05-8-4-2] Ramsay, J., Silverman, B. W. (2005). Basis function
                expansion of the functions. In *Functional Data Analysis*
                (pp. 161-164). Springer.

        """

        # the maximum number of components is established by the target basis
        # if the target basis is available.
        n_basis = (self.components_basis.n_basis if self.components_basis
                   else X.basis.n_basis)
        n_samples = X.n_samples

        # check that the number of components is smaller than the sample size
        if self.n_components > X.n_samples:
            raise AttributeError("The sample size must be bigger than the "
                                 "number of components")

        # check that we do not exceed limits for n_components as it should
        # be smaller than the number of attributes of the basis
        if self.n_components > n_basis:
            raise AttributeError("The number of components should be "
                                 "smaller than the number of attributes of "
                                 "target principal components' basis.")

        # if centering is True then subtract the mean function to each function
        # in FDataBasis
        if self.centering:
            meanfd = X.mean()
            # consider moving these lines to FDataBasis as a centering function
            # subtract from each row the mean coefficient matrix
            X.coefficients -= meanfd.coefficients

        # setup principal component basis if not given
        if self.components_basis:
            # First fix domain range if not already done
            self.components_basis.domain_range = X.basis.domain_range
            g_matrix = self.components_basis.gram_matrix()
            # the matrix that are in charge of changing the computed principal
            # components to target matrix is essentially the inner product
            # of both basis.
            j_matrix = X.basis.inner_product(self.components_basis)
        else:
            # if no other basis is specified we use the same basis as the passed
            # FDataBasis Object
            self.components_basis = X.basis.copy()
            g_matrix = self.components_basis.gram_matrix()
            j_matrix = g_matrix

        # make g matrix symmetric, referring to Ramsay's implementation
        g_matrix = (g_matrix + np.transpose(g_matrix)) / 2

        # Apply regularization / penalty if applicable
        if self.regularization_parameter > 0:
            # obtain regularization matrix
            regularization_matrix = self.components_basis.penalty(
                self.penalty
            )
            # apply regularization
            g_matrix = (g_matrix + self.regularization_parameter *
                        regularization_matrix)

        # obtain triangulation using cholesky
        l_matrix = np.linalg.cholesky(g_matrix)

        # we need L^{-1} for a multiplication, there are two possible ways:
        # using solve to get the multiplication result directly or just invert
        # the matrix. We choose solve because it is faster and more stable.
        # The following matrix is needed: L^{-1}*J^T
        l_inv_j_t = solve_triangular(l_matrix, np.transpose(j_matrix),
                                     lower=True)

        # the final matrix, C(L-1Jt)t for svd or (L-1Jt)-1CtC(L-1Jt)t for PCA
        final_matrix = (X.coefficients @ np.transpose(l_inv_j_t) /
                        np.sqrt(n_samples))

        # initialize the pca module provided by scikit-learn
        pca = PCA(n_components=self.n_components)
        pca.fit(final_matrix)

        # we choose solve to obtain the component coefficients for the
        # same reason: it is faster and more efficient
        component_coefficients = solve_triangular(np.transpose(l_matrix),
                                                  np.transpose(pca.components_),
                                                  lower=False)

        component_coefficients = np.transpose(component_coefficients)

        # the singular values obtained using SVD are the squares of eigenvalues
        self.component_values_ = pca.singular_values_ ** 2
        self.explained_variance_ratio_ = pca.explained_variance_ratio_
        self.components_ = X.copy(basis=self.components_basis,
                                  coefficients=component_coefficients)

        return self

    def transform(self, X, y=None):
        """Computes the n_components first principal components score and
        returns them.

        Args:
            X (FDataBasis):
                the functional data object to be analysed
            y (None, not used):
                only present because of fit function convention

        Returns:
            (array_like): the scores of the data with reference to the
            principal components
        """

        # in this case it is the inner product of our data with the components
        return X.inner_product(self.components_)


def _auxiliary_penalty_matrix(sample_points):
    """ Computes the auxiliary matrix needed for the computation of the penalty
    matrix. For more details please view the module fdata2pc of the library
    fda.usc in R, and the referenced paper.

    Args:
        sample_points: the points of discretization of the data matrix.
    Returns:
        (array_like): the auxiliary matrix used to compute the penalty matrix

    References.
        [1] Nicole Krämer, Anne-Laure Boulesteix, and Gerhard Tutz. Penalized
        partial least squares with applications to b-spline transformations
        and functional data. Chemometrics and Intelligent Laboratory Systems,
        94:60–69, 11 2008.

    """
    diff_values = np.diff(sample_points)
    hh = -(1 / np.mean(1 / diff_values)) / diff_values
    aux_diff_matrix = np.diag(hh)

    n_points = len(sample_points)

    aux_matrix_1 = np.zeros((n_points - 1, n_points))
    aux_matrix_1[:, :-1] = aux_diff_matrix
    aux_matrix_2 = np.zeros((n_points - 1, n_points))
    aux_matrix_2[:, 1:] = -aux_diff_matrix

    diff_matrix = aux_matrix_1 + aux_matrix_2

    return diff_matrix


def regularization_penalty_matrix(sample_points, penalty):
    """ Computes the penalty matrix for regularization of the principal
    components in a grid representation. For more details please view the module
    fdata2pc of the library fda.usc in R, and the referenced paper.

    Args:
        sample_points: the points of discretization of the data matrix.
        penalty (array_like): coefficients representing the differential
            operator used in the computation of the penalty matrix. For example,
            the array (1, 0, 1) means :math:`1 + D^{2}`
    Returns:
        (array_like): the penalty matrix used to regularize the components

    References.
        [1] Nicole Krämer, Anne-Laure Boulesteix, and Gerhard Tutz. Penalized
        partial least squares with applications to b-spline transformations
        and functional data. Chemometrics and Intelligent Laboratory Systems,
        94:60–69, 11 2008.

    """
    penalty = np.array(penalty)
    n_points = len(sample_points)
    penalty_matrix = np.zeros((n_points, n_points))
    if np.sum(penalty) != 0:
        # independent term
        penalty_matrix = penalty_matrix + penalty[0] * np.diag(
            np.ones(n_points))
        if len(penalty) > 1:
            # for each term of the differential operator, we compute the penalty
            # matrix of that order and then add it to the final penalty matrix
            aux_penalty_1 = _auxiliary_penalty_matrix(sample_points)
            aux_penalty_2 = _auxiliary_penalty_matrix(sample_points)
            for i in range(1, len(penalty)):
                if i > 1:
                    aux_penalty_1 = (aux_penalty_2[:(n_points - i),
                                     :(n_points - i + 1)]
                                     @ aux_penalty_1)
                # applying the differential operator, as in each step the
                # derivative degree increases by 1.
                penalty_matrix = (penalty_matrix +
                                  penalty[i] * (np.transpose(
                                    aux_penalty_1) @ aux_penalty_1))
    return penalty_matrix


class FPCAGrid(FPCA):
    """Funcional principal component analysis for functional data represented
    in discretized form.

    Parameters:
        n_components (int): number of principal components to obtain from
            functional principal component analysis. Defaults to 3.
        centering (bool): if True then calculate the mean of the functional data
            object and center the data first. Defaults to True. If True the
            passed FDataBasis object is modified.
        weights (numpy.array Union callable): the weights vector used for
            discrete integration. If none then the trapezoidal rule is used for
            computing the weights. If a callable object is passed, then the
            weight vector will be obtained by evaluating the object at the
            sample points of the passed FDataGrid object in the fit method.
        regularization_parameter (float): this parameter determines the amount
            of smoothing applied. Defaults to 0
        penalty (Union[int, Iterable[float]]): the coefficients that will be
            used to calculate the penalty matrix for regularization.
            If you input an integer then the derivative of that degree will be
            used to regularize the principal components. If you input a vector
            then it is considered as a differential operator. For example,
            [0,1,2] penalizes first derivative and two times the second
            derivative.

    Attributes:
        components_ (FDataBasis): this contains the principal components either
            in a basis form.
        component_values_ (array_like): this contains the values (eigenvalues)
            associated with the principal components.
        explained_variance_ratio_ (array_like): this contains the percentage of
            variance explained by each principal component.

    Examples:
        In this example we apply discretized functional PCA with some simple
        data to illustrate the usage of this class. We initialize the
        FPCADiscretized object, fit the artificial data and obtain the scores.
        The results are not tested because there are several equivalent
        possibilities.

        >>> data_matrix = np.array([[1.0, 0.0], [0.0, 2.0]])
        >>> sample_points = [0, 1]
        >>> fd = FDataGrid(data_matrix, sample_points)
        >>> fpca_grid = FPCAGrid(2)
        >>> fpca_grid = fpca_grid.fit(fd)
    """

    def __init__(self,
                 n_components=3,
                 weights=None,
                 centering=True,
                 regularization_parameter=0,
                 penalty=2):
        super().__init__(n_components, centering,
                         regularization_parameter, penalty)
        self.weights = weights

    def fit(self, X: FDataGrid, y=None):
        """Computes the n_components first principal components and saves them.

        The eigenvalues associated with these principal
        components are also saved. For more details about how it is implemented
        please view the referenced book, chapter 8.

        In summary, we are performing standard multivariate PCA over
        :math:`\\frac{1}{\sqrt{N}} \mathbf{X} \mathbf{W}^{1/2}` where :math:`N`
        is the number of samples in the dataset, :math:`\\mathbf{X}` is the data
        matrix and :math:`\\mathbf{W}` is the weight matrix (this matrix
        defines the numerical integration). By default the weight matrix is
        obtained using the trapezoidal rule.

        Args:
            X (FDataGrid):
                the functional data object to be analysed in basis
                representation
            y (None, not used):
                only present for convention of a fit function

        Returns:
            self (object)

        References:
            .. [RS05-8-4-1] Ramsay, J., Silverman, B. W. (2005). Discretizing
            the functions. In *Functional Data Analysis* (p. 161). Springer.
        """

        # check that the number of components is smaller than the sample size
        if self.n_components > X.n_samples:
            raise AttributeError("The sample size must be bigger than the "
                                 "number of components")

        # check that we do not exceed limits for n_components as it should
        # be smaller than the number of attributes of the funcional data object
        if self.n_components > X.data_matrix.shape[1]:
            raise AttributeError("The number of components should be "
                                 "smaller than the number of discretization "
                                 "points of the functional data object.")

        # data matrix initialization
        fd_data = X.data_matrix.reshape(X.data_matrix.shape[:-1])

        # get the number of samples and the number of points of descretization
        n_samples, n_points_discretization = fd_data.shape

        # if centering is True then subtract the mean function to each function
        # in FDataBasis
        if self.centering:
            meanfd = X.mean()
            # consider moving these lines to FDataGrid as a centering function
            # subtract from each row the mean coefficient matrix
            fd_data -= meanfd.data_matrix.reshape(meanfd.data_matrix.shape[:-1])

        # establish weights for each point of discretization
        if not self.weights:
            # sample_points is a list with one array in the 1D case
            # in trapezoidal rule, suppose \deltax_k = x_k - x_{k-1}, the weight
            # vector is as follows: [\deltax_1/2, \deltax_1/2 + \deltax_2/2,
            # \deltax_2/2 + \deltax_3/2, ... , \deltax_n/2]
            differences = np.diff(X.sample_points[0])
            differences = np.concatenate(((0,), differences, (0,)))
            self.weights = (differences[:-1] + differences[1:]) / 2
        elif callable(self.weights):
            self.weights = self.weights(X.sample_points[0])
            # if its a FDataGrid then we need to reduce the dimension to 1-D
            # array
            if isinstance(self.weights, FDataGrid):
                self.weights = np.squeeze(self.weights.data_matrix)

        weights_matrix = np.diag(self.weights)

        if self.regularization_parameter > 0:
            # if its an integer, we transform it to an array representing the
            # linear differential operator of that order
            if isinstance(self.penalty, int):
                self.penalty = np.append(np.zeros(self.penalty), 1)
            penalty_matrix = regularization_penalty_matrix(X.sample_points[0],
                                                           self.penalty)

            # we need to invert aux matrix and multiply it to the data matrix
            aux_matrix = (np.diag(np.ones(n_points_discretization)) +
                          self.regularization_parameter * penalty_matrix)
            # we use solve for better stability, P=aux matrix, X=data_matrix
            # we need X*P^-1 = ((P^T)^-1*X^T)^T, and np.solve gives (P^T)^-1*X^T
            fd_data = np.transpose(np.linalg.solve(np.transpose(aux_matrix),
                                                   np.transpose(fd_data)))


        # see docstring for more information
        final_matrix = fd_data @ np.sqrt(weights_matrix) / np.sqrt(n_samples)

        pca = PCA(n_components=self.n_components)
        pca.fit(final_matrix)
        self.components_ = X.copy(data_matrix=np.transpose(
            np.linalg.solve(np.sqrt(weights_matrix),
                            np.transpose(pca.components_))))
        self.component_values_ = pca.singular_values_ ** 2
        self.explained_variance_ratio_ = pca.explained_variance_ratio_

        return self

    def transform(self, X, y=None):
        """Computes the n_components first principal components score and
        returns them.

        Args:
            X (FDataGrid):
                the functional data object to be analysed
            y (None, not used):
                only present because of fit function convention

        Returns:
            (array_like): the scores of the data with reference to the
            principal components
        """

        # in this case its the coefficient matrix multiplied by the principal
        # components as column vectors
        return FDataGrid(data_matrix=X.data_matrix.reshape(
            X.data_matrix.shape[:-1]) @ np.transpose(
            self.components_.data_matrix.reshape(
                self.components_.data_matrix.shape[:-1])))
