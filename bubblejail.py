from subprocess import run as sub_run
from typing import List, Tuple
from dataclasses import dataclass, field
from sys import argv


@dataclass
class BwrapConfigBase:
    arg_word: str = field(init=False)

    def to_args(self) -> Tuple[str, ...]:
        return (self.arg_word, )


@dataclass
class ReadOnlyBind(BwrapConfigBase):
    arg_word = '--ro-bind'
    source: str
    dest: str

    def to_args(self):
        return self.arg_word, self.source, self.dest


@dataclass
class DirCreate(BwrapConfigBase):
    arg_word = '--dir'
    dest: str

    def to_args(self):
        return self.arg_word, self.dest


@dataclass
class Symlink(BwrapConfigBase):
    arg_word = '--symlink'
    source: str
    dest: str

    def to_args(self):
        return self.arg_word, self.source, self.dest


@dataclass
class BwrapArgs:
    read_only_binds: List[ReadOnlyBind]
    dir_create: List[DirCreate]
    symlinks: List[Symlink]
    share_network: bool = False


DEFAULT_CONFIG = BwrapArgs(
    read_only_binds=[
        ReadOnlyBind('/usr', '/usr'),
        ReadOnlyBind('/etc/resolv.conf', '/etc/resolv.conf')
    ],

    dir_create=[DirCreate('/tmp'), DirCreate('/var')],
    symlinks=[Symlink('usr/lib', '/lib'), Symlink('usr/lib64', '/lib64'),
              Symlink('usr/bin', '/bin'), Symlink('usr/sbin', '/sbin')],

)


def run_bwrap(args_to_target: list, bwrap_config: BwrapArgs = DEFAULT_CONFIG):
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

    bwrap_args.extend(args_to_target)
    return sub_run(bwrap_args)


if __name__ == "__main__":
    run_bwrap(argv[1:])
