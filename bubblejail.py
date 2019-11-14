from subprocess import Popen
from typing import List, Tuple, IO, Optional, Set
from os import getuid, getgid, environ
from dataclasses import dataclass, field
from sys import argv
from tempfile import TemporaryFile


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
        ReadOnlyBind('/etc/login.defs'),
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


def copy_data_to_temp_file(data: bytes) -> IO[bytes]:
    temp_file = TemporaryFile()
    temp_file.write(data)
    temp_file.seek(0)
    return temp_file


def run_bwrap(args_to_target: List[str],
              bwrap_config: BwrapArgs = DEFAULT_CONFIG) -> 'Popen[bytes]':
    bwrap_args: List[str] = ['bwrap']

    for ro_entity in bwrap_config.read_only_binds:
        bwrap_args.extend(ro_entity.to_args())

    for dir_entity in bwrap_config.dir_create:
        bwrap_args.extend(dir_entity.to_args())

    for symlink in bwrap_config.symlinks:
        bwrap_args.extend(symlink.to_args())

    # Proc
    bwrap_args.extend(('--proc', '/proc'))
    # Devtmpfs
    bwrap_args.extend(('--dev', '/dev'))
    # Unshare all
    bwrap_args.append('--unshare-all')
    # Die with parent
    bwrap_args.append('--die-with-parent')

    if bwrap_config.share_network:
        bwrap_args.append('--share-net')

    # Copy files
    # Prevent our temporary file from being garbage collected
    temp_files: List[IO[bytes]] = []
    file_descriptors_to_pass: List[int] = []
    for f in bwrap_config.files:
        temp_f = copy_data_to_temp_file(f.content)
        temp_files.append(temp_f)
        temp_file_descriptor = temp_f.fileno()
        file_descriptors_to_pass.append(temp_file_descriptor)
        bwrap_args.extend(('--file', str(temp_file_descriptor), f.dest))

    # Unset all variables
    for e in environ:
        if e not in bwrap_config.env_no_unset:
            bwrap_args.extend(('--unsetenv', e))

    # Set enviromental variables
    for env_var in bwrap_config.enviromental_variables:
        bwrap_args.extend(env_var.to_args())

    # Change directory
    bwrap_args.extend(('--chdir', '/home/user'))

    bwrap_args.extend(args_to_target)
    p = Popen(bwrap_args, pass_fds=file_descriptors_to_pass)
    p.wait()
    return p


if __name__ == "__main__":
    run_bwrap(argv[1:])
