#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module allows to dump snapshot of dPay's livenet contents described in the issue:
https://github.com/dpays/dpaybot/issues/16
"""

import argparse
import json
import sys
from simple_dpay_client.client import DPayRemoteBackend, DPayInterface, DPayRPCException

from . import __version__

DATABASE_API_SINGLE_QUERY_LIMIT = 1000

# Whitelist of exceptions from transaction source (Mainnet).
TRANSACTION_SOURCE_RETRYABLE_ERRORS = [
  "Unable to acquire database lock",
  "Internal Error",
  "Server error",
  "Upstream response error"
]

def list_all_accounts(dpayd):
    """ Generator function providing set of accounts existing in the Main dPay livenet """
    start = ""
    last = ""
    retry_count = 0

    while True:
        retry_count += 1

        try:
            result = dpayd.database_api.list_accounts(
                start=start,
                limit=DATABASE_API_SINGLE_QUERY_LIMIT,
                order="by_name",
                )
            making_progress = False
            for a in result["accounts"]:
                if a["name"] > last:
                    yield a
                    last = a["name"]
                    making_progress = True
                start = last
            if not making_progress:
                break
        except DPayRPCException as e:
            cause = e.args[0].get("error")
            if cause:
                message = cause.get("message")
                data = cause.get("data")
                retry = False

            if message and message in TRANSACTION_SOURCE_RETRYABLE_ERRORS:
                retry = True

            if retry and retry_count < MAX_RETRY:
                print("Recovered (tries: %s): %s" % (retry_count, message), file=sys.stderr)
                if data:
                    print(json.dumps(data, indent=2), file=sys.stderr)
            else:
                raise e

def list_all_witnesses(dpayd):
    """ Generator function providing set of witnesses defined in the Main dPay livenet """
    start = ""
    last = ""
    w_owner = ""

    while True:
        result = dpayd.database_api.list_witnesses(
            start=start,
            limit=DATABASE_API_SINGLE_QUERY_LIMIT,
            order="by_name",
            )
        making_progress = False
        for w in result["witnesses"]:
            w_owner = w["owner"]
            if w_owner > last:
                yield w_owner # Only `owner` member shall be provided
                last = w_owner
                making_progress = True
            start = last
        if not making_progress:
            break

# Helper function to reuse code related to collection dump across different usecases
def dump_collection(c, outfile):
    """ Allows to dump collection into JSON string. """
    outfile.write("[\n")
    first = True
    for o in c:
        if not first:
            outfile.write(",\n")
        json.dump( o, outfile, separators=(",", ":"), sort_keys=True )
        first = False
    outfile.write("\n]")

def dump_all_accounts(dpayd, outfile):
    """ Allows to dump into the snapshot all accounts provided by dPay LiveNet"""
    dump_collection(list_all_accounts(dpayd), outfile)

def dump_all_witnesses(dpayd, outfile):
    """ Allows to dump into the snapshot all witnesses provided by dPay LiveNet"""
    dump_collection(list_all_witnesses(dpayd), outfile)

def dump_dgpo(dpayd, outfile):
    """ Allows to dump into the snapshot all Dynamic Global Properties Objects
        provided by dPay LiveNet
    """
    dgpo = dpayd.database_api.get_dynamic_global_properties(x=None)
    json.dump( dgpo, outfile, separators=(",", ":"), sort_keys=True )

def main(argv):
    """ Tool entry point function """
    parser = argparse.ArgumentParser(prog=argv[0], description="Create snapshot files for dPay")
    parser.add_argument("-s", "--server", default="https://greatbase.dpaynodes.com", dest="server", metavar="URL", help="Specify livenet dpayd server")
    parser.add_argument("-o", "--outfile", default="-", dest="outfile", metavar="FILE", help="Specify output file, - means stdout")
    args = parser.parse_args(argv[1:])

    if args.outfile == "-":
        outfile = sys.stdout
    else:
        outfile = open(args.outfile, "w")

    backend = DPayRemoteBackend(nodes=[args.server], appbase=True)
    dpayd = DPayInterface(backend)

    outfile.write("{\n")
    outfile.write('"metadata":{"snapshot:semver":"%s","snapshot:origin_api":"%s"}' % (__version__, args.server))
    outfile.write(',\n"dynamic_global_properties":')
    dump_dgpo(dpayd, outfile)
    outfile.write(',\n"accounts":')
    dump_all_accounts(dpayd, outfile)
    outfile.write(',\n"witnesses":')
    dump_all_witnesses(dpayd, outfile)
    outfile.write("\n}\n")
    outfile.flush()
    if args.outfile != "-":
        outfile.close()
    return

if __name__ == "__main__":
    main(sys.argv)
