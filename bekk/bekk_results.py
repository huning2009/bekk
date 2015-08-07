#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
BEKK results
============

"""
from __future__ import print_function, division

import numpy as np

from .utils import format_time

__all__ = ['BEKKResults']


class BEKKResults(object):

    """Estimation results.

    Attributes
    ----------
    innov
        Return innovations
    hvar
        Filtered variance matrices
    var_target
        Estimated varinace target
    param_start
        Starting parameters
    param_final
        Estimated parameters
    model
        Specific model to estimate
    restriction
        Restriction on parameters
    use_target
        Variance targeting flag
    weights
        Weight matrices for spatial model only
    method
        Optimization method. See scipy.optimize.minimize
    cython
        Whether to use Cython optimizations (True) or not (False)

    Methods
    -------


    """

    def __init__(self, innov=None, hvar=None, var_target=None, model=None,
                 use_target=None, restriction=None, cfree=None,
                 method=None, cython=None,
                 param_start=None, param_final=None, time_delta=None,
                 opt_out=None):
        """Initialize the class.

        Parameters
        ----------
        innov : (nobs, nstocks) array
            Return innovations
        hvar : (nobs, nstocks, nstocks) array
            Filtered variance matrices
        var_target : (nstocks, nstocks) array
            Estimated varinace target
        param_start : BEKKParams instance
            Starting parameters
        param_final : BEKKParams instance
            Estimated parameters
        model : str
            Specific model to estimate. Must be

                - 'standard'
                - 'spatial'
        restriction : str
            Restriction on parameters. Must be

                - 'full'
                - 'diagonal'
                - 'scalar'
        use_target : bool
            Whether to use variance targeting (True) or not (False)
        cfree : bool
            Whether to leave C matrix free (True) or not (False)
        weights : (ncat, nstocks, nstocks) array
            Weight matrices for spatial model only
        method : str
            Optimization method. See scipy.optimize.minimize
        cython : bool
            Whether to use Cython optimizations (True) or not (False)

        """
        self.param_start = param_start
        self.param_final = param_final
        self.time_delta = time_delta
        self.opt_out = opt_out
        self.var_target = var_target
        self.model = model
        self.restriction = restriction
        self.use_target = use_target
        self.cfree = cfree

    def __str__(self):
        """String representation.

        """
        width = 60
        show = '=' * width
        show += '\nModel: ' + self.model
        show += '\nRestriction: ' + self.restriction
        show += '\nUse target: ' + str(self.use_target)
        show += '\nMatrix C is free: ' + str(self.cfree)
        show += '\nIterations = ' + str(self.opt_out.nit)
        show += '\nOptimization time = %s' % format_time(self.time_delta)
        show += '\n\nFinal parameters:'
        show += str(self.param_final)
        show += '\nVariance target:\n'
        show += str(self.var_target) + '\n'
        show += '\nFinal log-likelihood = %.2f' % (-self.opt_out.fun) + '\n'
        show += '=' * width
        return show