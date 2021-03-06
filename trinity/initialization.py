import os

from eth.chains.mainnet import (
    MAINNET_GENESIS_HEADER,
)
from eth.chains.ropsten import (
    ROPSTEN_GENESIS_HEADER,
)
from eth.exceptions import CanonicalHeadNotFound

from p2p import ecies

from trinity.constants import (
    ROPSTEN_NETWORK_ID,
    MAINNET_NETWORK_ID,
)
from trinity.config import TrinityConfig
from trinity.db.chain import AsyncChainDB
from trinity.exceptions import (
    MissingPath,
)
from trinity.utils.filesystem import (
    is_under_path,
)


def is_data_dir_initialized(trinity_config: TrinityConfig) -> bool:
    """
    - base dir exists
    - chain data-dir exists
    - nodekey exists and is non-empty
    - canonical chain head in db
    """
    if not os.path.exists(trinity_config.data_dir):
        return False

    if not os.path.exists(trinity_config.database_dir):
        return False

    if not trinity_config.logfile_path.parent.exists():
        return False
    elif not trinity_config.logfile_path.exists():
        return False

    if trinity_config.nodekey_path is None:
        # has an explicitely defined nodekey
        pass
    elif not os.path.exists(trinity_config.nodekey_path):
        return False

    if trinity_config.nodekey is None:
        return False

    return True


def is_database_initialized(chaindb: AsyncChainDB) -> bool:
    try:
        chaindb.get_canonical_head()
    except CanonicalHeadNotFound:
        # empty chain database
        return False
    else:
        return True


def initialize_data_dir(trinity_config: TrinityConfig) -> None:
    should_create_data_dir = (
        not trinity_config.data_dir.exists() and
        is_under_path(trinity_config.trinity_root_dir, trinity_config.data_dir)
    )
    if should_create_data_dir:
        trinity_config.data_dir.mkdir(parents=True, exist_ok=True)
    elif not trinity_config.data_dir.exists():
        # we don't lazily create the base dir for non-default base directories.
        raise MissingPath(
            "The base chain directory provided does not exist: `{0}`".format(
                trinity_config.data_dir,
            ),
            trinity_config.data_dir
        )

    # Logfile
    should_create_logdir = (
        not trinity_config.logdir_path.exists() and
        is_under_path(trinity_config.trinity_root_dir, trinity_config.logdir_path)
    )
    if should_create_logdir:
        trinity_config.logdir_path.mkdir(parents=True, exist_ok=True)
        trinity_config.logfile_path.touch()
    elif not trinity_config.logdir_path.exists():
        # we don't lazily create the base dir for non-default base directories.
        raise MissingPath(
            "The base logging directory provided does not exist: `{0}`".format(
                trinity_config.logdir_path,
            ),
            trinity_config.logdir_path
        )

    # Chain data-dir
    os.makedirs(trinity_config.database_dir, exist_ok=True)

    # Nodekey
    if trinity_config.nodekey is None:
        nodekey = ecies.generate_privkey()
        with open(trinity_config.nodekey_path, 'wb') as nodekey_file:
            nodekey_file.write(nodekey.to_bytes())


def initialize_database(trinity_config: TrinityConfig, chaindb: AsyncChainDB) -> None:
    try:
        chaindb.get_canonical_head()
    except CanonicalHeadNotFound:
        if trinity_config.network_id == ROPSTEN_NETWORK_ID:
            # We're starting with a fresh DB.
            chaindb.persist_header(ROPSTEN_GENESIS_HEADER)
        elif trinity_config.network_id == MAINNET_NETWORK_ID:
            chaindb.persist_header(MAINNET_GENESIS_HEADER)
        else:
            # TODO: add genesis data to TrinityConfig and if it's present, use it
            # here to initialize the chain.
            raise NotImplementedError(
                "Only the mainnet and ropsten chains are currently supported"
            )
