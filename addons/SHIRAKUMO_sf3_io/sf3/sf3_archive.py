# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

from . import kaitaistruct
from .kaitaistruct import ReadWriteKaitaiStruct, KaitaiStream, BytesIO


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class Sf3Archive(ReadWriteKaitaiStruct):
    """
    .. seealso::
       Source - https://shirakumo.org/docs/sf3
    """
    def __init__(self, _io=None, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self

    def _read(self):
        self.magic = self._io.read_bytes(10)
        if not (self.magic == b"\x81\x53\x46\x33\x00\xE0\xD0\x0D\x0A\x0A"):
            raise kaitaistruct.ValidationNotEqualError(b"\x81\x53\x46\x33\x00\xE0\xD0\x0D\x0A\x0A", self.magic, self._io, u"/seq/0")
        self.format_id = self._io.read_bytes(1)
        if not (self.format_id == b"\x01"):
            raise kaitaistruct.ValidationNotEqualError(b"\x01", self.format_id, self._io, u"/seq/1")
        self.checksum = self._io.read_u4le()
        self.null_terminator = self._io.read_bytes(1)
        if not (self.null_terminator == b"\x00"):
            raise kaitaistruct.ValidationNotEqualError(b"\x00", self.null_terminator, self._io, u"/seq/3")
        self.archive = Sf3Archive.Archive(self._io, self, self._root)
        self.archive._read()


    def _fetch_instances(self):
        pass
        self.archive._fetch_instances()


    def _write__seq(self, io=None):
        super(Sf3Archive, self)._write__seq(io)
        self._io.write_bytes(self.magic)
        self._io.write_bytes(self.format_id)
        self._io.write_u4le(self.checksum)
        self._io.write_bytes(self.null_terminator)
        self.archive._write__seq(self._io)


    def _check(self):
        pass
        if (len(self.magic) != 10):
            raise kaitaistruct.ConsistencyError(u"magic", len(self.magic), 10)
        if not (self.magic == b"\x81\x53\x46\x33\x00\xE0\xD0\x0D\x0A\x0A"):
            raise kaitaistruct.ValidationNotEqualError(b"\x81\x53\x46\x33\x00\xE0\xD0\x0D\x0A\x0A", self.magic, None, u"/seq/0")
        if (len(self.format_id) != 1):
            raise kaitaistruct.ConsistencyError(u"format_id", len(self.format_id), 1)
        if not (self.format_id == b"\x01"):
            raise kaitaistruct.ValidationNotEqualError(b"\x01", self.format_id, None, u"/seq/1")
        if (len(self.null_terminator) != 1):
            raise kaitaistruct.ConsistencyError(u"null_terminator", len(self.null_terminator), 1)
        if not (self.null_terminator == b"\x00"):
            raise kaitaistruct.ValidationNotEqualError(b"\x00", self.null_terminator, None, u"/seq/3")
        if self.archive._root != self._root:
            raise kaitaistruct.ConsistencyError(u"archive", self.archive._root, self._root)
        if self.archive._parent != self:
            raise kaitaistruct.ConsistencyError(u"archive", self.archive._parent, self)

    class MetaEntry(ReadWriteKaitaiStruct):
        def __init__(self, _io=None, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root

        def _read(self):
            self.mod_time = self._io.read_s8le()
            self.checksum = self._io.read_u4le()
            self.mime = Sf3Archive.String1(self._io, self, self._root)
            self.mime._read()
            self.path = Sf3Archive.String2(self._io, self, self._root)
            self.path._read()


        def _fetch_instances(self):
            pass
            self.mime._fetch_instances()
            self.path._fetch_instances()


        def _write__seq(self, io=None):
            super(Sf3Archive.MetaEntry, self)._write__seq(io)
            self._io.write_s8le(self.mod_time)
            self._io.write_u4le(self.checksum)
            self.mime._write__seq(self._io)
            self.path._write__seq(self._io)


        def _check(self):
            pass
            if self.mime._root != self._root:
                raise kaitaistruct.ConsistencyError(u"mime", self.mime._root, self._root)
            if self.mime._parent != self:
                raise kaitaistruct.ConsistencyError(u"mime", self.mime._parent, self)
            if self.path._root != self._root:
                raise kaitaistruct.ConsistencyError(u"path", self.path._root, self._root)
            if self.path._parent != self:
                raise kaitaistruct.ConsistencyError(u"path", self.path._parent, self)


    class String1(ReadWriteKaitaiStruct):
        def __init__(self, _io=None, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root

        def _read(self):
            self.len = self._io.read_u1()
            self.value = (self._io.read_bytes(self.len)).decode("UTF-8")


        def _fetch_instances(self):
            pass


        def _write__seq(self, io=None):
            super(Sf3Archive.String1, self)._write__seq(io)
            self._io.write_u1(self.len)
            self._io.write_bytes((self.value).encode(u"UTF-8"))


        def _check(self):
            pass
            if (len((self.value).encode(u"UTF-8")) != self.len):
                raise kaitaistruct.ConsistencyError(u"value", len((self.value).encode(u"UTF-8")), self.len)


    class File(ReadWriteKaitaiStruct):
        def __init__(self, _io=None, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root

        def _read(self):
            self.length = self._io.read_u8le()
            self.payload = self._io.read_bytes(self.length)


        def _fetch_instances(self):
            pass


        def _write__seq(self, io=None):
            super(Sf3Archive.File, self)._write__seq(io)
            self._io.write_u8le(self.length)
            self._io.write_bytes(self.payload)


        def _check(self):
            pass
            if (len(self.payload) != self.length):
                raise kaitaistruct.ConsistencyError(u"payload", len(self.payload), self.length)


    class String2(ReadWriteKaitaiStruct):
        def __init__(self, _io=None, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root

        def _read(self):
            self.len = self._io.read_u2le()
            self.value = (self._io.read_bytes(self.len)).decode("UTF-8")


        def _fetch_instances(self):
            pass


        def _write__seq(self, io=None):
            super(Sf3Archive.String2, self)._write__seq(io)
            self._io.write_u2le(self.len)
            self._io.write_bytes((self.value).encode(u"UTF-8"))


        def _check(self):
            pass
            if (len((self.value).encode(u"UTF-8")) != self.len):
                raise kaitaistruct.ConsistencyError(u"value", len((self.value).encode(u"UTF-8")), self.len)


    class Archive(ReadWriteKaitaiStruct):
        def __init__(self, _io=None, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root

        def _read(self):
            self.entry_count = self._io.read_u8le()
            self.meta_size = self._io.read_u8le()
            self.meta_entry_offsets = []
            for i in range(self.entry_count):
                self.meta_entry_offsets.append(self._io.read_u8le())

            self.meta_entries = []
            for i in range(self.entry_count):
                _t_meta_entries = Sf3Archive.MetaEntry(self._io, self, self._root)
                _t_meta_entries._read()
                self.meta_entries.append(_t_meta_entries)

            self.file_offsets = []
            for i in range(self.entry_count):
                self.file_offsets.append(self._io.read_u8le())

            self.file_payloads = []
            for i in range(self.entry_count):
                _t_file_payloads = Sf3Archive.File(self._io, self, self._root)
                _t_file_payloads._read()
                self.file_payloads.append(_t_file_payloads)



        def _fetch_instances(self):
            pass
            for i in range(len(self.meta_entry_offsets)):
                pass

            for i in range(len(self.meta_entries)):
                pass
                self.meta_entries[i]._fetch_instances()

            for i in range(len(self.file_offsets)):
                pass

            for i in range(len(self.file_payloads)):
                pass
                self.file_payloads[i]._fetch_instances()



        def _write__seq(self, io=None):
            super(Sf3Archive.Archive, self)._write__seq(io)
            self._io.write_u8le(self.entry_count)
            self._io.write_u8le(self.meta_size)
            for i in range(len(self.meta_entry_offsets)):
                pass
                self._io.write_u8le(self.meta_entry_offsets[i])

            for i in range(len(self.meta_entries)):
                pass
                self.meta_entries[i]._write__seq(self._io)

            for i in range(len(self.file_offsets)):
                pass
                self._io.write_u8le(self.file_offsets[i])

            for i in range(len(self.file_payloads)):
                pass
                self.file_payloads[i]._write__seq(self._io)



        def _check(self):
            pass
            if (len(self.meta_entry_offsets) != self.entry_count):
                raise kaitaistruct.ConsistencyError(u"meta_entry_offsets", len(self.meta_entry_offsets), self.entry_count)
            for i in range(len(self.meta_entry_offsets)):
                pass

            if (len(self.meta_entries) != self.entry_count):
                raise kaitaistruct.ConsistencyError(u"meta_entries", len(self.meta_entries), self.entry_count)
            for i in range(len(self.meta_entries)):
                pass
                if self.meta_entries[i]._root != self._root:
                    raise kaitaistruct.ConsistencyError(u"meta_entries", self.meta_entries[i]._root, self._root)
                if self.meta_entries[i]._parent != self:
                    raise kaitaistruct.ConsistencyError(u"meta_entries", self.meta_entries[i]._parent, self)

            if (len(self.file_offsets) != self.entry_count):
                raise kaitaistruct.ConsistencyError(u"file_offsets", len(self.file_offsets), self.entry_count)
            for i in range(len(self.file_offsets)):
                pass

            if (len(self.file_payloads) != self.entry_count):
                raise kaitaistruct.ConsistencyError(u"file_payloads", len(self.file_payloads), self.entry_count)
            for i in range(len(self.file_payloads)):
                pass
                if self.file_payloads[i]._root != self._root:
                    raise kaitaistruct.ConsistencyError(u"file_payloads", self.file_payloads[i]._root, self._root)
                if self.file_payloads[i]._parent != self:
                    raise kaitaistruct.ConsistencyError(u"file_payloads", self.file_payloads[i]._parent, self)




