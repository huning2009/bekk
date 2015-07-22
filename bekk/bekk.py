#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
BEKK simulation and estimation class
====================================

"""
from __future__ import print_function, division

import time
import matplotlib.pylab as plt
import seaborn as sns

import numpy as np
from scipy.optimize import minimize

from .bekkparams import BEKKParams
from .recursion import recursion
from .likelihood import likelihood
from .utils import estimate_h0, likelihood_python, filter_var_python

__all__ = ['BEKK']


class BEKK(object):
    r"""BEKK model. Estimation class.

    .. math::
        u_t|H_t &\sim N(0,H_t) \\
        u_t     &= e_t H_t^{1/2}, e_t \sim N(0,I) \\
        H_t     &= E_{t-1}[u_tu_t^\prime]

    One lag, no asymmetries

    .. math::
        H_t = CC^\prime + Au_{t-1}u_{t-1}^\prime A^\prime + BH_{t-1}B^\prime

    Parameters
    ----------
    innov : (nobs, nstocks) array
        Return innovations

    Attributes
    ----------
    innov : (nobs, nstocks) array
        Return innovations
    log_file : str
        File name to write the results of estimation
    param_start : BEKKParams instance
        Initial values of model parameters
    param_final : BEKKParams instance
        Final values of model parameters
    opt_out : scipy.minimize.OptimizeResult instance
        Optimization results

    Methods
    -------
    print_results
        Print results after estimation was completed
    estimate
        Estimate model parameters

    """

    def __init__(self, innov):
        """Initialize the class.

        Parameters
        ----------
        innov : (nobs, nstocks) array
            Return innovations

        """
        self.innov = innov
        self.log_file = None
        self.param_start = None
        self.param_final = None
        self.method = 'SLSQP'
        self.time_delta = None
        self.opt_out = None
        self.cython = True
        self.hvar = None

    def likelihood(self, theta, target):
        """Compute the conditional log-likelihood function.

        Parameters
        ----------
        theta : 1dim array
            Dimension depends on the model restriction
        kwargs : dict
            Any additional parameters

        Returns
        -------
        float
            The value of the minus log-likelihood function.
            If some regularity conditions are violated, then it returns
            some obscene number.

        """
        nstocks = self.innov.shape[1]
        param = BEKKParams(theta=theta, target=target, nstocks=nstocks,
                           restriction=self.param_start.restriction)

        if param.constraint() >= 1 or param.cmat is None:
            return 1e10

        nobs, nstocks = self.innov.shape
        self.hvar = np.zeros((nobs, nstocks, nstocks), dtype=float)
        self.hvar[0] = param.unconditional_var()

        args = [self.hvar, self.innov, param.amat, param.bmat, param.cmat]

        if self.cython:
            recursion(*args)
            return likelihood(self.hvar, self.innov)
        else:
            filter_var_python(*args)
            return likelihood_python(self.hvar, self.innov)

    def callback(self, theta):
        """Empty callback function.

        Parameters
        ----------
        theta : 1dim array
            Parameter vector

        """
        pass

    def print_results(self, **kwargs):
        """Print stuff after estimation.

        Parameters
        ----------
        kwargs : dict, optional
            Keyword arguments

        """
        if 'param_true' in kwargs:
            like_true = self.likelihood(kwargs['param_true'].theta, kwargs)
        like_start = self.likelihood(self.param_start.theta, kwargs)
        like_final = self.likelihood(self.param_final.theta, kwargs)
        # Form the string
        string = ['\n']
        string.append('Method = ' + self.method)
        string.append('Total time (minutes) = %.2f' % self.time_delta)
        if 'theta_true' in kwargs:
            string.append('True likelihood = %.2f' % like_true)
        string.append('Initial likelihood = %.2f' % like_start)
        string.append('Final likelihood = %.2f' % like_final)
        string.append('Likelihood difference = %.2f' %
                      (like_start - like_final))
        string.append('Success = ' + str(self.opt_out.success))
        string.append('Message = ' + str(self.opt_out.message))
        string.append('Iterations = ' + str(self.opt_out.nit))
        string.extend(self.param_final.log_string())
        string.append('\nH0 target =\n'
                      + np.array_str(estimate_h0(self.innov)))
        # Save results to the log file
        with open(self.log_file, 'a') as texfile:
            for istring in string:
                texfile.write(istring + '\n')

    def estimate(self, restriction='scalar', var_target=True, param_start=None,
                 **kwargs):
        """Estimate parameters of the BEKK model.

        Updates several attributes of the class.

        Parameters
        ----------
        restriction : str
            Can be
                - 'full'
                - 'diagonal'
                - 'scalar'
        var_target : bool
            Variance targeting flag. If True, then cmat is not returned.
        kwargs : keyword arguments, optional

        """
        # Update default settings
        self.__dict__.update(kwargs)
        nstocks = self.innov.shape[1]
        if var_target:
            target = self.innov.T.dot(self.innov) / nstocks
        else:
            target = None
        # Optimization options
        options = {'disp': False, 'maxiter': int(1e6)}
        # Check for existence of initial guess among arguments.
        # Otherwise, initialize.
        if param_start is not None:
            self.param_start = param_start
        # Start timer for the whole optimization
        time_start = time.time()
        # Run optimization
        self.opt_out = minimize(self.likelihood, self.param_start.theta,
                                args=(target,), method=self.method,
                                options=options)
        # How much time did it take in minutes?
        self.time_delta = (time.time() - time_start) / 60
        # Store optimal parameters in the corresponding class
        self.param_final = BEKKParams(theta=self.opt_out.x,
                                      restriction=restriction,
                                      target=target, nstocks=nstocks)
        if self.log_file is not None:
            self.print_results(**kwargs)

    def estimate_error(self, param):
        """Filter out the error given parameters.

        Parameters
        ----------
        param : BEKKParams instance
            Model parameters

        Returns
        -------
        error : (nobs, nstocks, nstocks) array
            Estimation errors

        """
        nobs, nstocks = self.innov.shape
        error = np.empty_like(self.hvar)
        uvar = param.unconditional_var()
        error[0] = self.innov[0].dot(self.innov[0].T) - uvar
        for i in range(1, nobs):
            error[i] = self.innov[i].dot(self.innov[i].T) - uvar
            temp = self.innov[i-1].dot(self.innov[i-1].T) - uvar
            error[i] -= param.amat.dot(temp).dot(param.amat.T)
            error[i] -= param.bmat.dot(self.hvar[i-1] - uvar).dot(param.bmat.T)
        return error

    def print_error(self):

        error = self.estimate_error(self.param_final).squeeze()
#        plt.plot(error)
#        plt.axhline(error.mean())
#        plt.show()
        print('Mean error: %.4f' % error.mean())
        print('Estimated H0:\n', self.param_final.unconditional_var())
        print('Target H0:\n', estimate_h0(self.innov))


if __name__ == '__main__':
    pass
    #from usage_example import test_bekk
    #test_bekk(nstocks=1, nobs=500, var_target=False)
