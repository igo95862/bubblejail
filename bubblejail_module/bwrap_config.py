from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Set
from os import getuid, getgid


@dataclass
class BwrapConfigBase:
    arg_word: str = field(init=False)

    def to_args(self) -> Tuple[str, ...]:
        return (self.arg_word, )


@dataclass
class ReadOnlyBind(BwrapConfigBase):
    arg_word = '--ro-bind'
    source: str
    dest: Optional[str] = None

    def to_args(self) -> Tuple[str, str, str]:
        return (self.arg_word,
                self.source,
                self.dest if self.dest is not None else self.source)


@dataclass
class DirCreate(BwrapConfigBase):
    arg_word = '--dir'
    dest: str

    def to_args(self) -> Tuple[str, str]:
        return self.arg_word, self.dest


@dataclass
class Symlink(BwrapConfigBase):
    arg_word = '--symlink'
    source: str
    dest: str

    def to_args(self) -> Tuple[str, str, str]:
        return self.arg_word, self.source, self.dest


@dataclass
class FileTransfer:
    content: bytes
    dest: str


@dataclass
class EnvrimentalVar(BwrapConfigBase):
    arg_word = '--setenv'
    var_name: str
    var_value: str

    def to_args(self) -> Tuple[str, str, str]:
        return self.arg_word, self.var_name, self.var_value


@dataclass
class BwrapArgs:
    read_only_binds: List[ReadOnlyBind] = field(default_factory=list)
    dir_create: List[DirCreate] = field(default_factory=list)
    symlinks: List[Symlink] = field(default_factory=list)
    files: List[FileTransfer] = field(default_factory=list)
    enviromental_variables: List[EnvrimentalVar] = field(default_factory=list)
    share_network: bool = False
    env_no_unset: Set[str] = field(default_factory=set)


DEFAULT_CONFIG = BwrapArgs(
    read_only_binds=[
        ReadOnlyBind('/usr'),
        ReadOnlyBind('/etc/resolv.conf'),
        ReadOnlyBind('/etc/login.defs'),  # ???: is this file needed
    ],

    dir_create=[
        DirCreate('/tmp'),
        DirCreate('/var'),
        DirCreate('/home/user')],

    symlinks=[
        Symlink('usr/lib', '/lib'),
        Symlink('usr/lib64', '/lib64'),
        Symlink('usr/bin', '/bin'),
        Symlink('usr/sbin', '/sbin')],

    files=[
        FileTransfer(
            bytes(f'user:x:{getuid()}:{getuid()}::/home/user:/bin/sh',
                  encoding='utf-8'),
            '/etc/passwd'),

        FileTransfer(bytes(f'user:x:{getgid()}:', encoding='utf-8'),
                     '/etc/group'),
    ],

    enviromental_variables=[
        EnvrimentalVar('USER', 'user'),
        EnvrimentalVar('USERNAME', 'user'),
    ],

    env_no_unset={
        'LANG',
    },
)
