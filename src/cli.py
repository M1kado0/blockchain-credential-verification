"""Local/RPC credential workflow: package, deploy, authorize, issue, verify, revoke.

RPC mutations use unlocked accounts; use only your own local development node.
Remote RPCs are permitted for read-only verification. Never enter real documents
on an untrusted RPC: commitments and identifiers become publicly linkable.
"""
import argparse
import json
import sys
from pathlib import Path
from web3 import Web3
from .chain import deploy, artifact, transact
from .credentials import new_credential, commitment


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rpc', default='http://127.0.0.1:8545')
    sub = p.add_subparsers(dest='command', required=True)
    pack = sub.add_parser('package')
    pack.add_argument('document', type=Path)
    pack.add_argument('output', type=Path)
    dep = sub.add_parser('deploy')
    dep.add_argument('--admin', required=True)
    for cmd in ['authorize', 'issue', 'verify', 'revoke']:
        q = sub.add_parser(cmd)
        q.add_argument('--contract', required=True)
        if cmd != 'verify':
            q.add_argument('--sender', required=True)
            q.add_argument('--local-unlocked', action='store_true',
                           help='explicit consent to use a local node unlocked account')
        if cmd == 'authorize':
            q.add_argument('--issuer', required=True)
            q.add_argument('--disable', action='store_true')
        else:
            q.add_argument('--package', type=Path, required=True)
        if cmd == 'verify':
            q.add_argument('--document', type=Path, required=True)
    args = p.parse_args()
    if args.command == 'package':
        package = new_credential(args.document.read_bytes())
        package['version'] = 'RK-ACADEMIC-CREDENTIAL-V1'
        # x mode avoids destroying an existing salt/credential package.
        with args.output.open('x') as f:
            json.dump(package, f, indent=2)
        print(args.output)
        return
    w3 = Web3(Web3.HTTPProvider(args.rpc, request_kwargs={'timeout': 15}))
    if not w3.is_connected():
        p.error('cannot connect to RPC; start anvil or check --rpc')
    if args.command == 'deploy':
        # Deployment is restricted to localhost nodes with intentionally unlocked accounts.
        from urllib.parse import urlparse
        if urlparse(args.rpc).hostname not in {'127.0.0.1', 'localhost', '::1'}:
            p.error('deployment command supports local development nodes only')
        contract, receipt = deploy(w3, 'CredentialRegistry', Web3.to_checksum_address(args.admin))
        print(json.dumps({'contract': contract.address, 'chain_id': w3.eth.chain_id,
                          'transaction': receipt.transactionHash.hex()}, indent=2))
        return
    if args.command != 'verify':
        from urllib.parse import urlparse
        if not args.local_unlocked or urlparse(args.rpc).hostname not in {'127.0.0.1', 'localhost', '::1'}:
            p.error('mutations require localhost RPC and --local-unlocked')
    contract = w3.eth.contract(address=Web3.to_checksum_address(args.contract),
                               abi=artifact('CredentialRegistry')['abi'])
    if not w3.eth.get_code(contract.address):
        p.error('no contract code at supplied address on this chain')
    if args.command == 'authorize':
        fn = contract.functions.setIssuer(Web3.to_checksum_address(args.issuer), not args.disable)
    else:
        package = json.loads(args.package.read_text())
        if package.get('version') != 'RK-ACADEMIC-CREDENTIAL-V1':
            p.error('unsupported package version')
        cid = bytes.fromhex(package['id'])
        digest = bytes.fromhex(package['commitment'])
        if args.command == 'verify':
            digest = commitment(args.document.read_bytes(), bytes.fromhex(package['salt']))
            valid = contract.functions.verify(cid, digest).call()
            print('VALID' if valid else 'INVALID')
            sys.exit(0 if valid else 1)
        fn = contract.functions.issue(cid, digest) if args.command == 'issue' else contract.functions.revoke(cid)
    receipt = transact(w3, fn, Web3.to_checksum_address(args.sender))
    print(json.dumps({'transaction': receipt.transactionHash.hex(), 'gas_used': receipt.gasUsed}))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, RuntimeError) as e:
        raise SystemExit(f'Error: {e}')
