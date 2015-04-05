# -*- coding: utf-8 -*-
"""
Helper functions

"""
from __future__ import print_function, division

import matplotlib.pylab as plt
import seaborn as sns
import numpy as np
import numba as nb
import scipy.sparse as scs

__all__ = ['_bekk_recursion', 'filter_var', 'estimate_h0', 'plot_data']


def _bekk_recursion(param, hzero, hone, htwo):
    """BEKK recursion.

    Parameters
    ----------
    param : BEKKParams instance
        Model parameters
    hzero : (nstocks, nstocks) array
        Initial matrix
    hone : (nstocks, nstocks) array
        Squared innovations matrix
    htwo : (nstocks, nstocks) array
        Old matrix

    Returns
    -------
    hnew : (nstocks, nstocks) array
        Updated variance matrix

    """
    return hzero + param.a_mat.dot(hone).dot(param.a_mat.T) \
        + param.b_mat.dot(htwo).dot(param.b_mat.T)


@nb.jit("float32[:,:,:](float32[:,:], float32[:,:],\
        float32[:,:], float32[:,:], float32[:,:])", nogil=True)
def filter_var(hvar, innov, c_mat, a_mat, b_mat):
    """Filter out variances and covariances of innovations.

    Parameters
    ----------
    innov : (nobs, nstocks) array
        Return innovations
    param : instance of BEKKParams class
        Attributes of this class hold parameter matrices

    Returns
    -------
    hvar : (nobs, nstocks, nstocks) array
        Variances and covariances of innovations

    """
    nobs, nstocks = innov.shape
    cc_mat = c_mat.dot(c_mat.T)
    innov2 = innov[:, np.newaxis, :] * innov[:, :, np.newaxis]
    for i in range(1, nobs):
        idx1 = slice((i-1)*nstocks, i*nstocks)
        idx2 = slice(i*nstocks, (i+1)*nstocks)
        hvar[idx2, idx2] = cc_mat + a_mat.dot(innov2[i-1]).dot(a_mat.T) \
            + b_mat.dot(hvar[idx1, idx1]).dot(b_mat.T)

    return hvar


def likelihood(hvar, innov):
    """Likelihood function.

    Parameters
    ----------
    innov : (nstocks,) array
        inovations
    hvar : (nstocks, nstocks) array
        variance/covariances
    parallel : bool
        Whether to use multiprocessing

    Returns
    -------
    fvalue : float
        log-likelihood contribution
    bad : bool
        True if something is wrong

    """
    factor = scs.linalg.splu(hvar)
    diag_factor = np.diag(factor.U.toarray())
    innov = innov.flatten()
    det = np.log(np.abs(diag_factor[~np.isnan(diag_factor)])).sum()
    return det + (factor.solve(innov) * innov).sum()


def estimate_h0(innov):
    """Estimate unconditional realized covariance matrix.

    Parameters
    ----------
    innov: (nobs, nstocks) array
        inovations

    Returns
    -------
    (nstocks, nstocks) array
        E[innov' * innov]

    """
    return innov.T.dot(innov) / innov.shape[0]


def plot_data(innov, hvar):
    """Plot time series of hvar and u elements.

    Parameters
    ----------
    innov: (nobs, nstocks) array
        innovations
    hvar: (nobs, nstocks, nstocks) array
        variance/covariances

    """
    sns.set_context('paper')
    nobs, nstocks = innov.shape
    axes = plt.subplots(nrows=nstocks**2, ncols=1)[1]
    for axi, i in zip(axes, range(nstocks**2)):
        axi.plot(range(nobs), hvar.reshape([nobs, nstocks**2])[:, i])
    plt.plot()

    axes = plt.subplots(nrows=nstocks, ncols=1)[1]
    for axi, i in zip(axes, range(nstocks)):
        axi.plot(range(nobs), innov[:, i])
    plt.plot()