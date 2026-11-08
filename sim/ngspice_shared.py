"""Minimal synchronous shared-ngspice adapter (Windows KiCad default).

API reference: https://ngspice.sourceforge.io/shared.html
No background analysis or GUI automation; returned vectors are copied.
"""
import ctypes as C
import os
from pathlib import Path
import numpy as np


class VectorInfo(C.Structure):
    _fields_ = [('name', C.c_char_p), ('type', C.c_int), ('flags', C.c_short),
                ('real', C.POINTER(C.c_double)), ('complex', C.c_void_p),
                ('length', C.c_int)]


class NgSpice:
    def __init__(self):
        path = Path(os.environ.get('NGSPICE_DLL', r'C:\Program Files\KiCad\10.0\bin\ngspice.dll'))
        self.dll_directory = os.add_dll_directory(str(path.parent))
        self.lib = C.CDLL(str(path))
        self.log = []
        self.exited = False
        send = C.CFUNCTYPE(C.c_int, C.c_char_p, C.c_int, C.c_void_p)
        exit_type = C.CFUNCTYPE(C.c_int, C.c_int, C.c_bool, C.c_bool, C.c_int, C.c_void_p)
        def receive(message, ident, user):
            self.log.append(message.decode(errors='replace'))
            return 0
        def controlled_exit(status, immediate, quit_exit, ident, user):
            self.exited = True
            return 0
        self.callbacks = [send(receive), send(lambda *_: 0), exit_type(controlled_exit)]
        self.lib.ngSpice_Init.argtypes = [C.c_void_p]*7
        self.lib.ngSpice_Init.restype = C.c_int
        self.lib.ngSpice_Command.argtypes = [C.c_char_p]
        self.lib.ngSpice_Command.restype = C.c_int
        self.lib.ngSpice_Circ.argtypes = [C.POINTER(C.c_char_p)]
        self.lib.ngSpice_Circ.restype = C.c_int
        self.lib.ngGet_Vec_Info.argtypes = [C.c_char_p]
        self.lib.ngGet_Vec_Info.restype = C.POINTER(VectorInfo)
        if self.lib.ngSpice_Init(*self.callbacks, None, None, None, None):
            raise RuntimeError('ngSpice_Init failed')
        self.command('version')

    def command(self, command):
        if self.lib.ngSpice_Command(command.encode()) or self.exited:
            raise RuntimeError('\n'.join(self.log[-30:]))

    def run(self, netlist):
        self.command('destroy all')
        lines = [line.encode() for line in netlist.splitlines()]
        deck = (C.c_char_p*(len(lines)+1))(*lines, None)
        start = len(self.log)
        if self.lib.ngSpice_Circ(deck):
            raise RuntimeError('\n'.join(self.log[start:]))
        self.command('run')
        messages = '\n'.join(self.log[start:])
        if 'error' in messages.lower() or 'aborted' in messages.lower():
            raise RuntimeError(messages)

    def vector(self, name):
        ptr = self.lib.ngGet_Vec_Info(name.encode())
        if not ptr or not ptr.contents.real or ptr.contents.length < 1:
            raise RuntimeError(f'Missing real vector: {name}\n'+'\n'.join(self.log[-20:]))
        return np.ctypeslib.as_array(ptr.contents.real, shape=(ptr.contents.length,)).copy()
