// Copyright (C) 2021 Intel Corporation
// SPDX-License-Identifier: BSD-3-Clause
// See: https://spdx.org/licenses/

#ifndef PY_MIDDLE_LAYER_H_
#define PY_MIDDLE_LAYER_H_

#include <Python.h>
#include <pybind11/pybind11.h>
#include <numpy/arrayobject.h>

#include <cstring>
#include <vector>

#include "utils.h"
#include "message_infrastructure_logging.h"

namespace message_infrastructure {

namespace py = pybind11;

int trick() {
    import_array();
    return 0;
}

const int tricky_var = trick();

class MetaDataTransfer {
 public:
  int CopyMDataToMem(MetaData* metadata, char* mem) {
    char *ptr = mem;
    std::memcpy(ptr, metadata, offsetof(MetaData, dims));
    ptr+=offsetof(MetaData, dims);

    std::memcpy(ptr, metadata->dims.data(), sizeof(int64_t) * metadata->nd);
    ptr+=sizeof(int64_t)*metadata->nd;

    std::memcpy(ptr, metadata->strides.data(), sizeof(int64_t) * metadata->nd);
    ptr+=sizeof(int64_t)*metadata->nd;

    std::memcpy(ptr, metadata->mdata, metadata->elsize * metadata->total_size);

    return 0;
  }

  int CopyMDataFromMem(MetaData* metadata, char *mem) {
    char *ptr = mem;
    std::memcpy(metadata, ptr, offsetof(MetaData, dims));
    ptr+=offsetof(MetaData, dims);

    auto *iptr = reinterpret_cast<int64_t*> (ptr);
    for (int i=0; i < metadata->nd; i++) {
      metadata->dims.push_back((*iptr++));
    }
    for (int i=0; i < metadata->nd; i++) {
      metadata->strides.push_back((*iptr++));
    }

    std::memcpy(iptr, metadata->mdata, metadata->elsize * metadata->total_size);

    return 0;
  }
};

class PyDataTransfer {
 public:
  py::object MDataToObject(MetaData* metadata) {
    std::vector<npy_intp> dims(metadata->nd);
    std::vector<npy_intp> strides(metadata->nd);

    for (int i = 0; i < metadata->nd; i++) {
      dims[i] = metadata->dims[i];
      strides[i] = metadata->strides[i] * metadata->elsize;
    }

    PyObject *array = PyArray_New(
      &PyArray_Type,
      metadata->nd,
      dims.data(),
      metadata->type,
      strides.data(),
      metadata->mdata,
      metadata->elsize,
      NPY_ARRAY_ALIGNED | NPY_ARRAY_WRITEABLE,
      nullptr);

    if (!array)
      return py::cast(0);

    return py::reinterpret_borrow<py::object>(array);
  }
  MetaData* MDataFromObject(py::object* object) {
    PyObject *obj = object->ptr();
    LAVA_LOG(LOG_LAYER, "start MDataFromObject\n");
    if (!PyArray_Check(obj)) {
      LAVA_LOG_ERR("The Object is not array tp is %s\n", Py_TYPE(obj)->tp_name);
      exit(-1);
    }

    LAVA_LOG(LOG_LAYER, "check obj achieved\n");

    auto array = reinterpret_cast<PyArrayObject*> (obj);
    if (!PyArray_ISWRITEABLE(array)) {
      LAVA_LOG(LOG_MP, "The array is not writeable\n");
    }

    // var from numpy
    int32_t ndim = PyArray_NDIM(array);
    auto dims = PyArray_DIMS(array);
    auto strides = PyArray_STRIDES(array);
    void* data_ptr = PyArray_DATA(array);
    // auto dtype = PyArray_Type(array);  // no work
    auto dtype = array->descr->type_num;
    auto element_size_in_bytes = PyArray_ITEMSIZE(array);
    auto tsize = PyArray_SIZE(array);

    // set metadata
    MetaData* metadata = new MetaData();
    metadata->nd = ndim;
    for (int i = 0; i < ndim; i++) {
      metadata->dims.push_back(dims[i]);
      metadata->strides.push_back(strides[i]/element_size_in_bytes);
      if (strides[i] % element_size_in_bytes != 0) {
        LAVA_LOG_ERR("numpy array stride not a multiple of element bytes\n");
      }
    }
    metadata->type = dtype;
    metadata->mdata = data_ptr;
    metadata->elsize = element_size_in_bytes;
    metadata->total_size = tsize;

    return metadata;
  }
  py::object GetObj() {
    return MDataToObject(this->metadata_);
  }
  int SetObj(py::object *obj) {
    this->metadata_ = MDataFromObject(obj);
    return 0;
  }
  void TestDataChange() {
    int32_t* ptr = reinterpret_cast<int32_t*> (this->metadata_->mdata);
    ptr[2] = 99;
  }

 private:
  MetaData *metadata_ = nullptr;
};

}  // namespace message_infrastructure

#endif  // PY_MIDDLE_LAYER_H_
