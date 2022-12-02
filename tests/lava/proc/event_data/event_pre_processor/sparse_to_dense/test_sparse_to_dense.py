# Copyright (C) 2022 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
# See: https://spdx.org/licenses/
import unittest
from lava.proc.event_data.event_pre_processor.sparse_to_dense.sparse_to_dense import SparseToDense, SparseToDensePM

import numpy as np

from lava.magma.core.process.process import AbstractProcess
from lava.magma.core.process.ports.ports import InPort, OutPort
from lava.magma.core.process.variable import Var

from lava.magma.core.sync.protocols.loihi_protocol import LoihiProtocol
from lava.magma.core.model.py.ports import PyInPort, PyOutPort
from lava.magma.core.model.py.type import LavaPyType
from lava.magma.core.resources import CPU
from lava.magma.core.decorator import implements, requires
from lava.magma.core.model.py.model import PyLoihiProcessModel

from lava.magma.core.run_conditions import RunSteps
from lava.magma.core.run_configs import Loihi1SimCfg

import matplotlib.pyplot as plt


class RecvDense(AbstractProcess):
    def __init__(self,
                 shape: tuple) -> None:
        super().__init__(shape=shape)

        self.in_port = InPort(shape=shape)

        self.data = Var(shape=shape, init=np.zeros(shape, dtype=int))


@implements(proc=RecvDense, protocol=LoihiProtocol)
@requires(CPU)
class PyRecvDensePM(PyLoihiProcessModel):
    in_port: PyInPort = LavaPyType(PyInPort.VEC_DENSE, int)

    data: np.ndarray = LavaPyType(np.ndarray, int)

    def run_spk(self) -> None:
        data = self.in_port.recv()

        self.data = data


class SendSparse(AbstractProcess):
    def __init__(self,
                 shape: tuple,
                 data: np.ndarray,
                 indices: np.ndarray) -> None:
        super().__init__(shape=shape, data=data, indices=indices)

        self.out_port = OutPort(shape=shape)


@implements(proc=SendSparse, protocol=LoihiProtocol)
@requires(CPU)
class PySendSparsePM(PyLoihiProcessModel):
    out_port: PyOutPort = LavaPyType(PyOutPort.VEC_SPARSE, int)

    def __init__(self, proc_params):
        super().__init__(proc_params)
        self._data = proc_params["data"]
        self._indices = proc_params["indices"]

    def run_spk(self) -> None:
        data = self._data
        idx = self._indices

        self.out_port.send(data, idx)




class TestProcessSparseToDense(unittest.TestCase):
    def test_init_2d(self):
        """Tests instantiation of SparseToDense for a 2D output"""
        sparse_to_dense = SparseToDense(shape_in=(43200,),
                                        shape_out=(240, 180))

        self.assertIsInstance(sparse_to_dense, SparseToDense)
        self.assertEqual(sparse_to_dense.proc_params["shape_in"], (43200,))
        self.assertEqual(sparse_to_dense.proc_params["shape_out"], (240, 180))

    def test_init_3d(self):
        """Tests instantiation of SparseToDense for a 3D output"""
        sparse_to_dense = SparseToDense(shape_in=(43200,),
                                        shape_out=(240, 180, 2))

        self.assertIsInstance(sparse_to_dense, SparseToDense)
        self.assertEqual(sparse_to_dense.proc_params["shape_in"], (43200,))
        self.assertEqual(sparse_to_dense.proc_params["shape_out"], (240, 180, 2))

    def test_invalid_shape_out_dimension(self):
        """Check if an error is raised when shape_out is 1D or 4D"""
        # TODO: should it rather raise not implemented error?
        with(self.assertRaises(ValueError)):
            _ = SparseToDense(shape_in=(43200,),
                              shape_out=(240,))

        with(self.assertRaises(ValueError)):
            _ = SparseToDense(shape_in=(43200,),
                              shape_out=(240, 180, 2, 1))

    def test_invalid_shape_in_dimension(self):
        """Check if an error is raised when shape_in is 2D"""
        with(self.assertRaises(ValueError)):
            _ = SparseToDense(shape_in=(43200, 1),
                              shape_out=(240, 180))

    def test_invalid_shape_in_third_dimension_not_2(self):
        """Checks if an error is raised if the value of the 3rd dimension 
        for the shape_out parameter is not 2"""
        with(self.assertRaises(ValueError)):
            _ = SparseToDense(shape_in=(43200,),
                              shape_out=(240, 180, 1))

    def test_invalid_shape_in_negative_integer(self):
        """Checks if an error is raised when a negative integer for shape_in 
        is given"""
        with(self.assertRaises(ValueError)):
            _ = SparseToDense(shape_in=(-43200,),
                              shape_out=(240, 180))

    def test_invalid_shape_in_decimal(self):
        """Checks if an error is raised when a decimal integer for shape_in 
        is given"""
        with(self.assertRaises(ValueError)):
            _ = SparseToDense(shape_in=(43200.5,),
                              shape_out=(240, 180))

    def test_invalid_shape_out_negative_width_or_height(self):
        """Checks if an error is raised when a negative width or height for 
        shape_out is given"""
        with(self.assertRaises(ValueError)):
            _ = SparseToDense(shape_in=(43200,),
                              shape_out=(-240, 180))
            
        with(self.assertRaises(ValueError)):
            _ = SparseToDense(shape_in=(43200,),
                              shape_out=(240, -180))

    def test_invalid_shape_out_decimal_width_or_height(self):
        """Checks if an error is raised when a decimal width or height for 
        shape_out is given"""
        with(self.assertRaises(ValueError)):
            _ = SparseToDense(shape_in=(43200,),
                              shape_out=(240.5, 180))
            
        with(self.assertRaises(ValueError)):
            _ = SparseToDense(shape_in=(43200,),
                              shape_out=(240, 180.5))


class TestProcessModelSparseToDense(unittest.TestCase):
    def test_init(self):
        proc_params = {
            "shape_out": (240, 180)
        }

        pm = SparseToDensePM(proc_params)

        self.assertIsInstance(pm, SparseToDensePM)
        self.assertEqual(pm._shape_out, proc_params["shape_out"])

    def test_run(self):
        data = np.array([1, 1, 1, 1, 1, 1])
        xs = [0, 1, 2, 1, 2, 4]
        ys = [0, 2, 1, 5, 7, 4]
        indices = np.ravel_multi_index((xs, ys), (8, 8))

        send_sparse = SendSparse(shape=(10, ), data=data, indices=indices)
        sparse_to_dense = SparseToDense(shape_in=(10, ),
                                        shape_out=(8, 8))

        send_sparse.out_port.connect(sparse_to_dense.in_port)

        # Run parameters
        num_steps = 1
        run_cfg = Loihi1SimCfg()
        run_cnd = RunSteps(num_steps=num_steps)

        # Running
        sparse_to_dense.run(condition=run_cnd, run_cfg=run_cfg)

        # Stopping
        sparse_to_dense.stop()

        self.assertFalse(sparse_to_dense.runtime._is_running)
        
    def test_2d(self):
        data = np.array([1, 1, 1, 1, 1, 1])
        xs = [0, 1, 2, 1, 2, 4]
        ys = [0, 2, 1, 5, 7, 4]
        indices = np.ravel_multi_index((xs, ys), (8, 8))

        expected_data = np.zeros((8, 8))
        expected_data[0, 0] = 1
        expected_data[1, 2] = 1
        expected_data[2, 1] = 1

        expected_data[1, 5] = 1
        expected_data[2, 7] = 1

        expected_data[4, 4] = 1

        send_sparse = SendSparse(shape=(10, ), data=data, indices=indices)
        sparse_to_dense = SparseToDense(shape_in=(10, ),
                                        shape_out=(8, 8))
        recv_dense = RecvDense(shape=(8, 8))

        send_sparse.out_port.connect(sparse_to_dense.in_port)
        sparse_to_dense.out_port.connect(recv_dense.in_port)

        # Run parameters
        num_steps = 1
        run_cfg = Loihi1SimCfg()
        run_cnd = RunSteps(num_steps=num_steps)

        # Running
        sparse_to_dense.run(condition=run_cnd, run_cfg=run_cfg)
        
        sent_and_received_data = \
            recv_dense.data.get()

        # Stopping
        sparse_to_dense.stop()

        np.testing.assert_equal(sent_and_received_data,
                                expected_data)

    def test_3d(self):
        data = np.array([1, 0, 1, 0, 1, 0])
        xs = [0, 1, 2, 1, 2, 4]
        ys = [0, 2, 1, 5, 7, 4]
        indices = np.ravel_multi_index((xs, ys), (8, 8))

        expected_data = np.zeros((8, 8, 2))
        expected_data[0, 0, 1] = 1
        expected_data[1, 2, 0] = 1
        expected_data[2, 1, 1] = 1

        expected_data[1, 5, 0] = 1
        expected_data[2, 7, 1] = 1

        expected_data[4, 4, 0] = 1

        send_sparse = SendSparse(shape=(10,), data=data, indices=indices)
        sparse_to_dense = SparseToDense(shape_in=(10,),
                                        shape_out=(8, 8, 2))
        recv_dense = RecvDense(shape=(8, 8, 2))

        send_sparse.out_port.connect(sparse_to_dense.in_port)
        sparse_to_dense.out_port.connect(recv_dense.in_port)

        # Run parameters
        num_steps = 1
        run_cfg = Loihi1SimCfg()
        run_cnd = RunSteps(num_steps=num_steps)

        # Running
        sparse_to_dense.run(condition=run_cnd, run_cfg=run_cfg)

        sent_and_received_data = \
            recv_dense.data.get()

        # Stopping
        sparse_to_dense.stop()

        # # TODO : REMOVE THIS AFTER DEBUG
        # expected_data_im = np.zeros((8, 8))
        # expected_data_im[expected_data[:, :, 0] == 1] = -1
        # expected_data_im[expected_data[:, :, 1] == 1] = 1
        # actual_data_im = np.zeros((8, 8))
        # actual_data_im[sent_and_received_data[:, :, 0] == 1] = -1
        # actual_data_im[sent_and_received_data[:, :, 1] == 1] = 1
        #
        # fig, (ax1, ax2) = plt.subplots(1, 2)
        # fig.suptitle('3D')
        # ax1.imshow(expected_data_im)
        # ax1.set_title("Expected data")
        # ax2.imshow(actual_data_im)
        # ax2.set_title("Actual data")
        #
        # fig.show()

        np.testing.assert_equal(sent_and_received_data,
                                expected_data)


if __name__ == '__main__':
    unittest.main()