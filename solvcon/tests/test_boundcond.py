# -*- coding: UTF-8 -*-


import os
import pickle
from unittest import TestCase

import numpy as np

import solvcon as sc
 
from ..testing import loadfile
from ..io import gambit
from ..boundcond import BC

def test_load():
    from ..boundcond import BC

class TestBc(TestCase):
    #__test__ = False    # temporarily turned off.
    blk = gambit.GambitNeutral(loadfile('sample.neu')).toblock()

    def test_BFREL(self):
        from ..boundcond import BC
        self.assertEqual(3, BC.BFREL)

    def test_print_vanilla(self):
        from ..boundcond import BC
        obj = BC()
        self.assertEqual(str(obj), '[BC#None "None": 0 faces with 0 values]')

    def test_print_sern(self):
        from ..boundcond import BC
        obj = BC()
        obj.sern = 5
        self.assertEqual(str(obj), '[BC#5 "None": 0 faces with 0 values]')

    def test_name(self):
        from ..boundcond import BC
        obj = BC()
        self.assertTrue(obj.name is None)
        obj.name = "set_a_name"
        self.assertEqual(obj.name, "set_a_name")
        obj.name = None
        self.assertTrue(obj.name is None)
        obj.name = sc.march.BoundaryData.NONAME
        self.assertTrue(obj.name is None)

    def test_facn(self):
        from ..boundcond import BC
        obj = BC()
        self.assertEqual((0, BC.BFREL), obj.facn.shape)
        self.assertEqual(0, obj.facn.size)

    def test_facn_set(self):
        from ..boundcond import BC
        obj = BC()
        # fake input only to fit the shape
        obj.facn = np.array([[10, 0, -1], [23, 1, -1]], dtype='int32')
        self.assertEqual((2, BC.BFREL), obj.facn.shape)
        self.assertEqual([10, 0, -1, 23, 1, -1], obj.facn.ravel().tolist())
        # The second dimension must be BC.BFREL
        with self.assertRaisesRegex(
            IndexError, "BoundaryData.facn second axis mismatch"
        ):
            obj.facn = np.array([[10, 0], [23, 1]], dtype='int32')

    def test_value(self):
        from ..boundcond import BC
        obj = BC()
        self.assertEqual((0, 0), obj.value.shape)
        self.assertEqual(0, obj.value.size)

    def test_value_set(self):
        from ..boundcond import BC
        obj = BC()
        obj.value = np.array([[1, 2], [3, 4]], dtype='float64')
        self.assertEqual((2, 2), obj.value.shape)
        self.assertEqual([1, 2, 3, 4], obj.value.ravel().tolist())

    def test_certain_bct(self):
        from ..boundcond import bctregy
        # check that the existance of the most generic abstract BC types.
        for key in 'BC', 'unspecified':
            self.assertTrue(key in bctregy)

    def test_comprehension(self):
        from numpy import concatenate
        # copy data from block.
        allfcs = concatenate([bc.facn[:,0] for bc in self.blk.bclist])
        allfcs.sort()
        bndfcs = self.blk.bndfcs[:,0].copy()
        bndfcs.sort()
        # test for name.
        names = sorted([bc.__class__.__name__ for bc in self.blk.bclist])
        self.assertEqual(names[0], 'BC')
        self.assertEqual(names[1], 'unspecified')
        # loop test.
        nbound = self.blk.nbound
        ibnd = 0
        while ibnd < nbound:
            self.assertEqual(allfcs[ibnd], bndfcs[ibnd])
            ibnd += 1

    def test_bndfcs(self):
        for bc in self.blk.bclist:
            for bfc, idx, ridx in bc.facn:
                self.assertEqual(bfc, bc.blk.bndfcs[idx,0])

    def test_fp(self):
        from ..dependency import str_of
        from ..conf import env
        for bc in self.blk.bclist:
            self.assertEqual(bc.fpdtype, env.fpdtype)
            self.assertEqual(bc.fpdtypestr, str_of(env.fpdtype))


class PickleTC(TestCase):

    def setUp(self):
        self.bc = BC()
        self.bc.facn = np.array([[10, 0, -1], [23, 1, -1]], dtype='int32')
        self.bc.value = np.array([[1, 2], [3, 4]], dtype='float64')

    def _check_content(self, bc):
        self.assertEqual((2, BC.BFREL), bc.facn.shape)
        self.assertEqual([10, 0, -1, 23, 1, -1], bc.facn.ravel().tolist())
        self.assertEqual((2, 2), bc.value.shape)
        self.assertEqual([1, 2, 3, 4], bc.value.ravel().tolist())

    def test_dumps(self):
        pickle.dumps(self.bc, 2)

    def test_loads(self):
        data = pickle.dumps(self.bc, 2)
        bc = pickle.loads(data)
        self._check_content(bc)
