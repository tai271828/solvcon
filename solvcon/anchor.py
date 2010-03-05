# -*- coding: UTF-8 -*-
# Copyright (C) 2008-2009 by Yung-Yu Chen.  See LICENSE.txt for terms of usage.

"""
Anchors attached to the solvers.
"""

class Anchor(object):
    """
    Anchor that called by solver objects at various stages.

    @ivar svr: the solver object to be attached to.
    @itype svr: solvcon.solver.Solver
    """

    def __init__(self, svr, **kw):
        from .solver import BaseSolver
        assert isinstance(svr, BaseSolver)
        self.svr = svr

    def provide(self):
        pass
    def preloop(self):
        pass
    def prefull(self):
        pass
    def postfull(self):
        pass
    def prehalf(self):
        pass
    def posthalf(self):
        pass
    def postloop(self):
        pass
    def exhaust(self):
        pass