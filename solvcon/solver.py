# -*- coding: UTF-8 -*-
# Copyright (C) 2008-2010 by Yung-Yu Chen.  See LICENSE.txt for terms of usage.

"""
Definition of the structure of solvers.
"""

from ctypes import Structure
from .gendata import TypeWithBinder

class BaseSolverExedata(Structure):
    """
    Execution information for BaseSolver.
    """
    from ctypes import c_int, c_double
    _fields_ = [
        ('ncore', c_int), ('neq', c_int),
        ('time', c_double), ('time_increment', c_double),
    ]
    del c_int, c_double 
    def __init__(self, *args, **kw):
        svr = kw.pop('svr', None)
        if svr == None:
            return
        for key in ('ncore', 'neq', 'time', 'time_increment'):
            setattr(self, key, getattr(svr, key))

class BaseSolver(object):
    """
    Generic solver definition.  It is an abstract class and should not be used
    to any concrete simulation case.  The concrete solver sub-classes should
    override the empty init and final methods for initialization and 
    finalization, respectively.

    @cvar _clib_solve: the external dll (accessible through ctypes) which do
        the cell loop.  Subclass should override it.
    @ctype _clib_solve: ctypes.CDLL
    @cvar _exeinfotype_: the type of Exeinfo (solvcon.dependency.FortranType) 
        for the solver.
    @ctype _exeinfotype_: type

    @cvar MESG_FILENAME_DEFAULT = the default file name for serial solver
        object.

    @ivar _fpdtype: dtype for the floating point data in the block instance.
    @itype _fpdtype: numpy.dtype

    @ivar enable_mesg: flag if mesg device should be enabled.
    @itype enable_mesg: bool
    @ivar mesg: message printer attached to a certain solver object; designed
        and mainly used for parallel solver.
    @itype mesg: solvcon.helper.Printer

    @ivar runanchors: the list for the anchor objects to be run.
    @itype runanchors: solvcon.anchor.AnchorList

    @ivar exd: execution information for the solver.
    @itype exd: ctypes.Structure
    @ivar exds: a list of execution information for the solver.
    @itype exds: list
    @ivar tpool: thread pool for solver.
    @itype tpool: solvcon.mthread.ThreadPool
    """

    __metaclass__ = TypeWithBinder
    _pointers_ = ['exd', 'exds']

    _exedatatype_ = BaseSolverExedata
    _clib_solve = None  # subclass should override.

    MESG_FILENAME_DEFAULT = 'solvcon.solver.log'

    def __init__(self, **kw):
        """
        @keyword fpdtype: dtype for the floating point data.
        """
        from .conf import env
        from .anchor import AnchorList
        self._fpdtype = kw.pop('fpdtype', env.fpdtype)
        self._fpdtype = env.fpdtype if self._fpdtype==None else self._fpdtype
        self.enable_mesg = kw.pop('enable_mesg', False)
        self.mesg = None
        self.ncore = kw.pop('ncore', -1)
        self.neq = kw.pop('neq')
        self.time = kw.pop('time', 0.0)
        self.time_increment = kw.pop('time_increment', 0.0)
        # anchor list.
        self.runanchors = AnchorList(self)
        # data structure for C/FORTRAN.
        self.exd = None
        self.exds = list()

    @property
    def fpdtype(self):
        import numpy
        _fpdtype = self._fpdtype
        if isinstance(_fpdtype, str):
            return getattr(numpy, _fpdtype)
        else:
            return self._fpdtype
    @property
    def fpdtypestr(self):
        from .dependency import str_of
        return str_of(self.fpdtype)
    @property
    def fpptr(self):
        from .dependency import pointer_of
        return pointer_of(self.fpdtype)
    @property
    def _clib_solvcon(self):
        from .dependency import _clib_solvcon_of
        return _clib_solvcon_of(self.fpdtype)

    def __create_mesg(self, force=False):
        """
        Create the message outputing device, which is intended for debugging
        and outputing messages related to the solver.  The outputing device is
        most useful when running distributed solvers.  The created device will
        be attach to self.

        @keyword force: flag to force the creation.  Default False,
        @type force: bool

        @return: nothing
        """
        import os
        from .helper import Printer
        if force: self.enable_mesg = True
        if self.enable_mesg:
            if self.svrn != None:
                main, ext = os.path.splitext(self.MESG_FILENAME_DEFAULT)
                tmpl = main + '%d' + ext
                dfn = tmpl % self.svrn
                dprefix = 'SOLVER%d: ' % self.svrn
            else:
                dfn = self.MESG_FILENAME_DEFAULT
                dprefix = ''
        else:
            dfn = os.devnull
            dprefix = ''
        self.mesg = Printer(dfn, prefix=dprefix, override=True)

    @staticmethod
    def detect_ncore():
        f = open('/proc/stat')
        data = f.read()
        f.close()
        cpulist = [line for line in data.split('\n') if
            line.startswith('cpu')]
        cpulist = [line for line in cpulist if line.split()[0] != 'cpu']
        return len(cpulist)

    def bind(self):
        """
        Put everything that cannot be pickled, such as file objects, ctypes
        pointers, etc., into self.

        @return: nothing
        """
        import sys
        from solvcon.mthread import ThreadPool
        # create message device.
        if self.mesg == None: self.__create_mesg()
        # detect number of cores.
        if self.ncore == -1 and sys.platform.startswith('linux2'):
            self.ncore = self.detect_ncore()
        # create executional data.
        exdtype = self._exedatatype_
        self.exd = exdtype(svr=self)
        self.exds = list()
        for it in range(self.ncore):
            self.exds.append(exdtype(svr=self))
        # create thread pool.
        self.tpool = ThreadPool(nthread=self.ncore)

    def init(self, **kw):
        """
        An empty initializer for the solver object.

        @return: nothing.
        """
        pass

    def provide(self):
        self.runanchors('provide')
    def preloop(self):
        self.runanchors('preloop')

    def march(self, time, time_increment, steps_run):
        """
        An empty marcher for the solver object.

        @param time: starting time of marching.
        @type time: float
        @param time_increment: temporal interval for the time step.
        @type time_increment: float
        @param steps_run: the count of time steps to run.
        @type steps_run: int
        @return: maximum CFL number.
        @rtype: float
        """
        return -2.0

    def postloop(self):
        self.runanchors('postloop')
    def exhaust(self):
        self.runanchors('exhaust')

    def final(self):
        """
        An empty finalizer for the solver object.

        @return: nothing.
        """
        pass

    def dump(self, objfn):
        """
        Pickle self into the given filename.

        @parameter objfn: the output filename.
        @type objfn: str
        """
        import cPickle as pickle
        holds = dict()
        self.unbind()
        for key in ['mesg',]:
            holds[key] = getattr(self, key)
            setattr(self, key, None)
        pickle.dump(self, open(objfn, 'wb'), pickle.HIGHEST_PROTOCOL)
        for key in holds:
            setattr(self, key, holds[key])
        self.bind()

class BlockSolver(BaseSolver):
    """
    Generic class for multi-dimensional (implemented with Block)
    sequential/parallel solvers.

    Before the invocation of init() method, bind() method must be called.

    @note: When subclass BlockSolver, in the init() method in the subclass must
    be initilized first, and the super().init() can then be called.  Otherwise
    the BCs can't set correct information to the solver.

    @cvar _interface_init_: list of attributes (arrays) to be exchanged on
        interface when initialized.
    @ctype _interface_init_: list
    @cvar IBCSLEEP: the sleep time in seconds while not using thread for
        exchange interfaces.
    @ctype IBCSLEEP: float

    @ivar ibcthread: flag if using threads.
    @itype ibcthread: bool

    @ivar svrn: serial number of block.
    @itype svrn: int
    @ivar msh: shape information of the Block.
    @itype msh: solvecon.block.BlockShape

    @ivar cecnd: coordinates of center of CCE/BCEs.
    @itype cecnd: numpy.ndarray
    @ivar cevol: volumes of CCE/BCEs.
    @itype cevol: numpy.ndarray

    @ivar sol: solution variables (for last time-step).
    @itype sol: numpy.ndarray
    @ivar soln: solution variables (to be updated for the marching time-step).
    @itype soln: numpy.ndarray
    @ivar dsol: gradient of solution variables (for last time-step).
    @itype dsol: numpy.ndarray
    @ivar dsoln: gradient of solution variables (to be updated for the marching
        time-step).
    @itype dsoln: numpy.ndarray

    @ivar der: the dictionary to put derived data arrays.  Mostly used by
        Anchors.
    @itype der: dict

    @ivar _calc_soln_args: a list of ctypes entities for marchsol() method.
    @itype _calc_soln_args: list
    @ivar _calc_dsoln_args: a list of ctypes entities for dmarchsol() method.
    @itype _calc_dsoln_args: list
    """

    _pointers_ = ['msh']

    _interface_init_ = ['cecnd', 'cevol']

    from .block import Block
    FCMND = Block.FCMND
    CLMND = Block.CLMND
    CLMFC = Block.CLMFC
    del Block

    IBCSLEEP = None

    def __init__(self, blk, *args, **kw):
        """
        @keyword neq: number of equations (variables).
        @type neq: int
        """
        from numpy import empty
        super(BlockSolver, self).__init__(*args, **kw)
        assert self.fpdtype == blk.fpdtype
        self.ibcthread = kw.pop('ibcthread', False)
        # absorb block.
        ## meta-data.
        self.svrn = blk.blkn
        self.nsvr = None
        ### shape.
        self.ndim = blk.ndim
        self.nnode = blk.nnode
        self.nface = blk.nface
        self.ncell = blk.ncell
        self.nbound = blk.nbound
        self.ngstnode = blk.ngstnode
        self.ngstface = blk.ngstface
        self.ngstcell = blk.ngstcell
        ### cell grouping and BCs.
        self.grpnames = blk.grpnames
        self.clgrp = blk.shclgrp
        self.bclist = blk.bclist
        for bc in self.bclist:
            bc.blk = None
            bc.svr = self
        ## connectivity.
        self.clnds = blk.shclnds
        self.clfcs = blk.shclfcs
        self.fcnds = blk.shfcnds
        self.fccls = blk.shfccls
        ## metrics.
        self.ndcrd = blk.shndcrd
        self.fccnd = blk.shfccnd
        self.fcnml = blk.shfcnml
        self.clcnd = blk.shclcnd
        self.clvol = blk.shclvol
        # data structure for C/FORTRAN.
        self.msh = None
        # create arrays.
        ndim = self.ndim
        ncell = self.ncell
        ngstcell = self.ngstcell
        ## metrics.
        self.cecnd = empty(
            (ngstcell+ncell, blk.CLMFC+1, ndim), dtype=self.fpdtype)
        self.cevol = empty((ngstcell+ncell, blk.CLMFC+1), dtype=self.fpdtype)
        ## solutions.
        neq = self.neq
        self.sol = empty((ngstcell+ncell, neq), dtype=self.fpdtype)
        self.soln = empty((ngstcell+ncell, neq), dtype=self.fpdtype)
        self.dsol = empty((ngstcell+ncell, neq, ndim), dtype=self.fpdtype)
        self.dsoln = empty((ngstcell+ncell, neq, ndim), dtype=self.fpdtype)
        ## derived data.
        self.der = dict()
        # interface BC information list.
        self.ibclist = None
        # pointers for solutions.
        self.solptr = None
        self.solnptr = None
        self.dsolptr = None
        self.dsolnptr = None
        # calculator arguments.
        self._calc_soln_args = None
        self._calc_dsoln_args = None
        # timer.
        self.timer = {
            'update': 0.0,
            'march': 0.0,
            'msol': 0.0,
            'ibcsol': 0.0,
            'bcsol': 0.0,
            'cfl': 0.0,
            'mdsol': 0.0,
            'ibcdsol': 0.0,
            'bcdsol': 0.0,
        }
        self.cputime = {
        }

    def remote_setattr(self, name, var):
        """
        Remotely set attribute of worker.
        """
        return setattr(self, name, var)

    def bind(self):
        """
        Bind all the boundary condition objects.

        @note: BC must be bound AFTER solver "pointers".  Overridders to the
            method should firstly bind all pointers, secondly super binder, and 
            then methods/subroutines.
        """
        from .block import BlockShape
        super(BlockSolver, self).bind()
        # structures.
        self.msh = BlockShape(
            ndim=self.ndim,
            fcmnd=self.FCMND, clmnd=self.CLMND, clmfc=self.CLMFC,
            nnode=self.nnode, nface=self.nface, ncell=self.ncell,
            nbound=self.nbound,
            ngstnode=self.ngstnode, ngstface=self.ngstface,
            ngstcell=self.ngstcell,
        )
        # boundary conditions.
        for bc in self.bclist:
            bc.bind()

    def unbind(self):
        """
        Unbind all the boundary condition objects.
        """
        super(BlockSolver, self).unbind()
        for bc in self.bclist:
            bc.unbind()

    @property
    def is_bound(self):
        """
        Check boundness for solver as well as BC objects.
        """
        if not super(BlockSolver, self).is_bound:
            return False
        else:
            for bc in self.bclist:
                if not bc.is_bound:
                    return False
            return True

    @property
    def is_unbound(self):
        """
        Check unboundness for solver as well as BC objects.
        """
        if not super(BlockSolver, self).is_unbound:
            return False
        else:
            for bc in self.bclist:
                if not bc.is_unbound:
                    return False
                return True

    def init(self, **kw):
        """
        Check and initialize BCs.
        """
        for bc in self.bclist:
            bc.init(**kw)
        super(BlockSolver, self).init(**kw)

    ##################################################
    # CESE solving algorithm.
    ##################################################
    def calc_soln(self):
        from ctypes import byref
        fpptr = self.fpptr
        self._clib_solvcon.calc_soln_(
            byref(self.msh),
            byref(self.exd),
            self.clvol.ctypes.data_as(fpptr),
            self.sol.ctypes.data_as(fpptr),
            self.soln.ctypes.data_as(fpptr),
        )
    def calc_dsoln(self):
        from ctypes import byref
        fpptr = self.fpptr
        self._clib_solvcon.calc_dsoln_(
            byref(self.msh),
            byref(self.exd),
            self.clcnd.ctypes.data_as(fpptr),
            self.dsol.ctypes.data_as(fpptr),
            self.dsoln.ctypes.data_as(fpptr),
        )

    def boundcond(self):
        """
        Update the boundary conditions.

        @return: nothing.
        """
        for bc in self.bclist: bc.sol()
        for bc in self.bclist: bc.dsol() 
    def update(self):
        """
        Copy from old solution arrays to new solution arrays.

        @return: nothing.
        """
        self.sol[:,:] = self.soln[:,:]
        self.dsol[:,:,:] = self.dsoln[:,:,:]

    def _set_time(self, time, time_increment):
        """
        Set the time for self and structures.
        """
        self.exd.time = self.time = time
        for exd in self.exds:
            exd.time = time
        self.exd.time_increment = self.time_increment = time_increment
        for exd in self.exds:
            exd.time_increment = time_increment
    def marchsol(self, time, time_increment):
        """
        March the solution U vector in the solver and BCs.

        @return: nothing.
        """
        self._set_time(time, time_increment)
        self.calc_soln()
    def estimatecfl(self):
        return -2.0
    def marchdsol(self, time, time_increment):
        """
        March the gradient of solution dU vector in the solver and BCs.

        @return: nothing.
        """
        self._set_time(time, time_increment)
        self.calc_dsoln()

    def boundsol(self):
        for bc in self.bclist: bc.sol()
    def bounddsol(self):
        for bc in self.bclist: bc.dsol()

    def march(self, time, time_increment, steps_run, worker=None):
        from time import time as _time
        maxCFL = -2.0
        istep = 0
        while istep < steps_run:
            self.runanchors('prefull')
            t0 = _time()
            for ihalf in range(2):
                self.runanchors('prehalf')
                t1 = _time()
                self.update()
                self.timer['update'] += _time() - t1
                # solutions.
                self.runanchors('premarchsol')
                t1 = _time()
                self.marchsol(time, time_increment)
                self.timer['msol'] += _time() - t1
                self.runanchors('preexsoln')
                t1 = _time()
                if worker: self.exchangeibc('soln', worker=worker)
                self.timer['ibcsol'] += _time() - t1
                self.runanchors('prebcsoln')
                t1 = _time()
                for bc in self.bclist: bc.sol()
                self.timer['bcsol'] += _time() - t1
                self.runanchors('precfl')
                t1 = _time()
                cCFL = self.estimatecfl()
                maxCFL = cCFL if cCFL > maxCFL else maxCFL
                self.timer['cfl'] += _time() - t1
                # solution gradients.
                self.runanchors('premarchdsol')
                t1 = _time()
                self.marchdsol(time, time_increment)
                self.timer['mdsol'] += _time() - t1
                self.runanchors('preexdsoln')
                t1 = _time()
                if worker: self.exchangeibc('dsoln', worker=worker)
                self.timer['ibcdsol'] += _time() - t1
                self.runanchors('prebcdsoln')
                t1 = _time()
                for bc in self.bclist: bc.dsol()
                self.timer['bcdsol'] += _time() - t1
                # increment time.
                time += time_increment/2
                self.runanchors('posthalf')
            self.timer['march'] += _time() - t0
            istep += 1
            self.runanchors('postfull')
        if worker:
            worker.conn.send(maxCFL)
        return maxCFL

    ##################################################
    # below are for parallelization.
    ##################################################
    def pull(self, arrname, inder=False, worker=None):
        """
        Pull data array to dealer (rpc) through worker object.

        @param arrname: the array to pull to master.
        @type arrname: str
        @param inder: the data array is derived data array.
        @type inder: bool
        @keyword worker: the worker object for communication.
        @type worker: solvcon.rpc.Worker
        @return: nothing.
        """
        conn = worker.conn
        if inder:
            arr = self.der[arrname]
        else:
            arr = getattr(self, arrname)
        conn.send(arr)

    def push(self, marr, arrname, start=0, inder=False):
        """
        Push data array received from dealer (rpc) into self.

        @param marr: the array passed in.
        @type marr: numpy.ndarray
        @param arrname: the array to pull to master.
        @type arrname: str
        @param start: the starting index of pushing.
        @type start: int
        @param inder: the data array is derived data array.
        @type inder: bool
        @return: nothing.
        """
        if inder:
            arr = self.der[arrname]
        else:
            arr = getattr(self, arrname)
        arr[start:] = marr[start:]

    def pullank(self, ankname, objname, worker=None):
        """
        Pull data array to dealer (rpc) through worker object.

        @param ankname: the name of related anchor.
        @type ankname: str
        @param objname: the object to pull to master.
        @type objname: str
        @keyword worker: the worker object for communication.
        @type worker: solvcon.rpc.Worker
        @return: nothing.
        """
        conn = worker.conn
        obj = getattr(self.runanchors[ankname], objname)
        conn.send(obj)

    def init_exchange(self, ifacelist):
        from .boundcond import interface
        # grab peer index.
        ibclist = list()
        for pair in ifacelist:
            if pair < 0:
                ibclist.append(pair)
            else:
                assert len(pair) == 2
                assert self.svrn in pair
                ibclist.append(sum(pair)-self.svrn)
        # replace with BC object, sendn and recvn.
        for bc in self.bclist:
            if not isinstance(bc, interface):
                continue
            it = ibclist.index(bc.rblkn)
            sendn, recvn = ifacelist[it]
            ibclist[it] = bc, sendn, recvn
        self.ibclist = ibclist

    def exchangeibc(self, arrname, worker=None):
        from time import sleep
        from threading import Thread
        threads = list()
        for ibc in self.ibclist:
            # check if sleep or not.
            if ibc < 0:
                if not self.ibcthread:
                    tosleep = abs(
                        self.IBCSLEEP if self.IBCSLEEP != None else ibc
                    )
                    sleep(tosleep)
                continue 
            bc, sendn, recvn = ibc
            # determine callable and arguments.
            if self.svrn == sendn:
                target = self.pushibc
                args = arrname, bc, recvn
            elif self.svrn == recvn:
                target = self.pullibc
                args = arrname, bc, sendn
            else:
                raise ValueError, 'bc.rblkn = %d != %d or %d' % (
                    bc.rblkn, sendn, recvn) 
            kwargs = {'worker': worker}
            # call to data transfer.
            if self.ibcthread:
                threads.append(Thread(
                    target=target,
                    args=args,
                    kwargs=kwargs,
                ))
                threads[-1].start()
            else:
                target(*args, **kwargs)
        if self.ibcthread:
            for thread in threads:
                thread.join()

    def pushibc(self, arrname, bc, recvn, worker=None):
        """
        Push data toward selected interface which connect to blocks with larger
        serial number than myself.

        @param arrname: name of the array in the object to exchange.
        @type arrname: str
        @param bc: the interface BC to push.
        @type bc: solvcon.boundcond.interface
        @param recvn: serial number of the peer to exchange data with.
        @type recvn: int
        @keyword worker: the wrapping worker object for parallel processing.
        @type worker: solvcon.rpc.Worker
        """
        ngstcell = self.ngstcell
        conn = worker.pconns[bc.rblkn]
        arr = getattr(self, arrname)
        # ask the receiver for data.
        rarr = conn.recv()  # comm.
        slct = bc.rclp[:,0] + ngstcell
        arr[slct] = rarr[:]
        # provide the receiver with data.
        slct = bc.rclp[:,2] + ngstcell
        conn.send(arr[slct])    # comm.

    def pullibc(self, arrname, bc, sendn, worker=None):
        """
        Pull data from the interface determined by the serial of peer.

        @param arrname: name of the array in the object to exchange.
        @type arrname: str
        @param bc: the interface BC to pull.
        @type bc: solvcon.boundcond.interface
        @param sendn: serial number of the peer to exchange data with.
        @type sendn: int
        @keyword worker: the wrapping worker object for parallel processing.
        @type worker: solvcon.rpc.Worker
        """
        ngstcell = self.ngstcell
        conn = worker.pconns[bc.rblkn]
        arr = getattr(self, arrname)
        # provide sender the data.
        slct = bc.rclp[:,2] + ngstcell
        conn.send(arr[slct])    # comm.
        # ask data from sender.
        rarr = conn.recv()  # comm.
        slct = bc.rclp[:,0] + ngstcell
        arr[slct] = rarr[:]
