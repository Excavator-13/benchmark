"""Dependency-free reader for these torch.save'd .pt tensor files.

Only used because torch is not installed on this machine; correctness is
validated by recomputing MAE/RMSE and comparing to the archived metrics.json,
plus comparing gold tensors against the raw Parquet labels.
"""
import io
import pickle
import zipfile

import numpy as np

DTYPES = {
    "FloatStorage": np.float32, "DoubleStorage": np.float64,
    "HalfStorage": np.float16, "LongStorage": np.int64,
    "IntStorage": np.int32, "ByteStorage": np.uint8,
    "BoolStorage": np.bool_, "CharStorage": np.int8,
    "ShortStorage": np.int16, "BFloat16Storage": None,
}


class _StorageType:
    def __init__(self, name):
        self._name = name

    def __name__(self):
        return self._name


class _Tensor:
    """Wraps the single (storage, offset, size, stride, ...) rebuild call."""

    def __new__(cls, *args, **kwargs):
        obj = super().__new__(cls)
        obj.args = args
        return obj

    def __init__(self, *args, **kwargs):
        pass

    @property
    def value(self):
        storage, offset = self.args[0], self.args[1]
        size, stride = tuple(self.args[2]), tuple(self.args[3])
        if offset:
            raise NotImplementedError("non-zero storage offset")
        arr = np.frombuffer(storage.buffer, dtype=storage.dtype)
        if stride == _packed(size):
            return arr.reshape(size).copy()
        out = np.lib.stride_tricks.as_strided(
            arr, shape=size, strides=tuple(s * arr.itemsize for s in stride))
        return np.ascontiguousarray(out)


def _packed(shape):
    stride, out = 1, []
    for dim in reversed(shape):
        out.append(stride)
        stride *= dim
    return tuple(reversed(out))


class _Storage:
    def __init__(self):
        self.buffer = b""
        self.dtype = None


class _Unpickler(pickle.Unpickler):
    def __init__(self, file, zipf):
        super().__init__(file)
        self.zipf = zipf

    def find_class(self, module, name):
        if module == "torch._utils" and name in ("_rebuild_tensor_v2",
                                                "_rebuild_tensor"):
            return _Tensor
        if module in ("torch", "torch.storage") and name.endswith("Storage"):
            return _StorageType(name)
        if module == "collections" and name == "OrderedDict":
            return dict
        return super().find_class(module, name)

    def persistent_load(self, pid):
        kind, stype, key, location, numel = pid
        raw = self.zipf.read(f"archive/data/{key}")
        dtype = DTYPES[stype.__name__()]
        assert dtype is not None, f"unsupported storage {stype.__name__()}"
        storage = _Storage()
        storage.buffer = raw
        storage.dtype = dtype
        assert len(raw) == numel * np.dtype(dtype).itemsize, (len(raw), numel)
        return storage


def load_tensor(path):
    with zipfile.ZipFile(path) as zipf:
        pkl = [n for n in zipf.namelist() if n.endswith("data.pkl")][0]
        with zipf.open(pkl) as handle:
            value = _Unpickler(io.BytesIO(handle.read()), zipf).load()
    return value.value
