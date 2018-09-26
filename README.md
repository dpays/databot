
# Overview

The `dpaybot` set of utilities is a set of scripts to create a testnet.
A `dpaybot` testnet allows all, or some subset of, user accounts to
easily be *ported* from the main network.

# dPayBot commands

This repository contains utilities to create a testnet.

`dpaybot snapshot` : Gets account data and other data from the blockchain as necessary to do offline initialization of testnet
`dpaybot txgen` : Translate the output of `snapshot.py` to a set of actions to perform offline initialization of testnet
`dpaybot keysub` : Substitute secret keys into a list of actions
`dpaybot submit` : Submit the output of `txgen.py` to testnet node

# Installation

## Creating a virtualenv

In this step we create a virtualenv to isolate our project from the
system-wide Python installation.  The virtualenv is *activated*,
modifying the `PATH` and the prompt of the current shell,
by sourcing the `activate` script:

```
sudo apt-get install virtualenv python3 libyajl-dev
virtualenv -p $(which python3) ~/ve/dpaybot
source ~/ve/dpaybot/bin/activate
```

## Using dpaybot

The `dpaybot` source can be checked out with `git`.  This documentation
assumes the source code lives in `~/src/dpaybot`:

**Note:**`dpaybot`'s default branch is develop. `master` is condsidered stablish.

```
mkdir -p ~/src
cd ~/src
git clone --branch master git@github.com:dpays/dpaybot
cd dpaybot
git submodule update --init --recursive
pip install pipenv
pipenv install
pip install .
```

If everything is set up correctly, you should be able to run commands
such as `dpaybot --help` as follows:

```
# Execute inside dpaybot virtualenv
dpaybot --help
```

Note, the `dpaybot` script in `~/ve/dpaybot/bin/dpaybot` may be symlinked
elsewhere (for example, `ln -s ~/ve/dpaybot/bin/dpaybot ~/bin/dpaybot`)
to allow `dpaybot` to run without the `virtualenv` being active.

# Example usage

This section contains a single large example.

## Mainnet dpayd

First, we set up a `dpayd` for the main network.  This `dpayd` must be the following characteristics:

- The `dpayd` must be `appbase` version
- The `chain`, `webserver` and `database_api` plugins must be enabled
- The `webserver-http-endpoint` assumed by the following examples is `127.0.0.1:8090`
- If a snapshot at a well-defined single point in time is desired, no seed nodes should be used, so it does not connect to the p2p network

## Taking a snapshot

```
dpaybot snapshot -s http://127.0.0.1:8090 -o snapshot.json
```

As of this writing, the above command takes approximately 5 minutes, writing an approximately 2 GB JSON file with 1,000,000 lines.
If you're running `dpaybot snapshot` interactively and you would like a visual progress indicator, you can install the `pv` program
(`apt-get install pv`) and use it to display the output line count in real time:

```
dpaybot snapshot -s http://127.0.0.1:8090 | pv -l > snapshot.json
```

# Generating actions

Now you can use `dpaybot txgen` to create a list of *actions*.  Actions include
transactions which create and fund the accounts, and wait-for-block instructions
which control the rate at which transactions occur:

```
# As of this writing, this command takes ~10 minutes to start writing actions,
# consumes ~200MB of RAM, with all actions created in about two hours
dpaybot txgen -c txgen.conf -o tn.txlist
```

Some notes about `dpaybot txgen`:

- All accounts have `porter` as an additional authority, allowing the testnet creator to act as any account on the testnet
- The private keys for `porter` and other accounts are deterministically created based on the `secret` option in the config file
- Balances are created by dividing `total_port_balance` proportionally among the live BEX and vesting, subject to `min_vesting_per_account`.
- Therefore, testnet balance is not equal to mainnet balance.  Rather, it is proportional to mainnet balance.
- Accounts listed in `txgen.conf` are considered system accounts, any identically named account in the snapshot will not be ported

# Keys substitution

To maintain separation of concerns in `dpaybot` tools, the `dpaybot txgen` tool
does not directly generate transactions containing private keys (except
the `DPAY_INIT_PRIVATE_KEY` WIF, `5JNHfZYKGaomSFvd4NUdQ9qMcEAC43kujbfjueTHpVapX1Kzq2n`).
Instead *keystrings* such as `publickey:active-porter` are outputted in place
of the actual public key of the `porter` account.

Since transactions can contain arbitrary user-specified data, a fixed
escape sequence cannot be used to delimit keystrings, since it might appear
in user-specified data.  Instead, a variable escape sequence (a short value
that does not appear in the data) is introduced and stored in the `"esc"`
variable.

So a program that knows the keys must substitute them before the transactions
can be submitted to the network.  This is the role of the key substitution tool
`dpaybot keysub`.  The `dpaybot keysub` tool takes as input a list of actions,
generates the specified keys, and substitutes them into each action.

## Deriving secret keys

By default, the private keys generated by `dpaybot keysub` have
known (i.e. insecure) seed strings.  However, a secret may be
added to each seed string by prepending a `set_secret` action
to `dpaybot keysub`.

## Command-line key generator

The `get_dev_key` program provided with `dpayd` derives
keys using the same algorithm as `dpaybot keysub`.

# Running testnet fastgen node

Now that the transactions have been created, let's use them to initialize a testnet.
Since many blocks worth of transactions are created, `dpaybot submit` will
implement the block wait using `debug_node_plugin` to generate blocks in the
past as rapidly as possible.  So we will run a special node, let's call it the
"fastgen node", with the debug plugin enabled.  The fastgen node is only used to
initialize the network.  (It is called "fastgen" because it generates blocks
as fast as possible, rather than waiting 3 seconds of real time between each
block.)  Later, one or more normal witness nodes will connect
to the fastgen node over p2p, get blocks, and begin normal block production.

The fastgen node needs the following:

- The `dpayd` must be `appbase` version
- The testnet `blockchain` directory should be empty (try `rm -Rf testnet_datadir/blockchain`)
- The following plugins should be enabled:  `chain p2p webserver debug_node database_api network_broadcast_api debug_node_api block_api`
- The `webserver-http-endpoint` assumed by the following examples is `127.0.0.1:9990`
- It must contain functionality from PR's #1722 #1723
- It should listen for p2p, the following examples assume it is listening on `0.0.0.0:12001`

On the testnet, some serializations are different from the main network, and
[they are not handled properly by dpay_python](https://github.com/dpay/dpay-python/issues/89).
Therefore, `dpaybot submit` outsources signing of those transactions to the
`sign_transaction` binary included with `dpayd`.

# Pipelining transactions to testnet

```
( \
  echo '["set_secret", {"secret":"xyz-"}]' ; \
  dpaybot txgen -c txgen.conf \
) | \
dpaybot keysub | \
dpaybot submit -t http://127.0.0.1:9990 --signer dpay/programs/util/sign_transaction -f fail.json
```

# Durables

For consistency across testnet deployments, fixture-like object that must exist for external testing are recreated by the `durables` module.

Copy `durables.conf.example` to `durables.conf`, add any desired objects, and run (typically after initial bootstrap and before `gatling`):

```
( \
  echo '["set_secret", {"secret":"xyz-"}]' ; \
  dpaybot durables -c durables.conf \
) | \
dpaybot keysub | \
dpaybot submit -t http://127.0.0.1:9990 --signer dpay/programs/util/sign_transaction -f die
```

# Warden

Use `warden` to check the current condition of a given chain.  It does some
basic checks to make sure the chain is up and running, then returns error codes.

Returning error code zero (0) means everything looks good.  Non-zero means
something is amiss.

```
dpaybot warden -s http://127.0.0.1:8090 && echo LGTM || echo Bummer.
```

As an example, you can add `warden` to your deployment script to delay the next step until your seed node has synchronized with the initial bootstrap node.

```bash
while [[ $all_clear -ne 0 ]]
do
    dpaybot warden -s http://my-seed-node:8080
    all_clear=$?
    echo Waiting for warden to sound the all-clear.
    sleep 60
done

echo Ready to proceed.
```

# Gatling transactions from mainnet

Populating the test network with transactions from the main network.

To stream from genesis:

```bash
dpaybot gatling -f 1 -o -
```

To stream from block 25066272 to 25066292:

```bash
dpaybot gatling -f 25066272 -t 25066292 -o -
```

To stream starting from block 25066272:

```bash
dpaybot gatling -f 25066272 -o -
```

# Running testnet witness node(s)

At the end of the transactions to be submitted, `dpaybot txgen` creates witnesses `init-0` through `init-20`
and votes for them with large amount of `TESTS`.  The keys of these witnesses are generated by a deterministic
algorithm compatible with the `get_dev_key` utility program, so the keys of the witnesses may be obtained
as follows:

```
programs/util/get_dev_key xxx- block-init-0:21
```

where `xxx` is the `"secret"` string in `txgen.conf`.

So in order to transition block production duties away from the initial node, all that is required
is to connect witness nodes with the correct block production settings.  Each witness node should
specify the fastgen node using the `p2p-seed-node` option in the config file.

Therefore we may add the witness definitions and private keys to the witness config file:

```
i=0 ; while [ $i -lt 21 ] ; do echo witness = '"'init-$i'"' >> testnet_datadir/config.ini ; let i=i+1 ; done
dpay/programs/util/get_dev_key xxx- block-init-0:21 | cut -d '"' -f 4 | sed 's/^/private-key = /' >> testnet_datadir/config.ini
```

Witness duties may of course be split among multiple nodes if desired, simply put the
`witness` and `private-key` definitions in the datadir of each node, and have each
witness node connect to all the others with the `p2p-seed-node` option.

Additionally, because there is a large gap in block timestamps between the end of the
initialization blocks and the beginning of normal production, the witness will need
to specify `--enable-stale-production` and `--required-participation=0` flags.  As
long as a sufficient number of other witness nodes are timely producing blocks, it
is not necessary to use these flags once 128 blocks have been produced after the
transition.

<img src="https://i.imgur.com/h57pDVE.png" width="25%" height="25%" />
