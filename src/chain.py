"""Local EVM execution. No testnet gas prices or network finality are modeled."""
import json
from pathlib import Path
from web3 import Web3, EthereumTesterProvider
from eth_tester import EthereumTester, PyEVMBackend

ROOT = Path(__file__).resolve().parents[1]


def local_chain() -> Web3:
    return Web3(EthereumTesterProvider(EthereumTester(backend=PyEVMBackend())))


def artifact(name: str) -> dict:
    path = ROOT / "artifacts" / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"{path}: run npm ci && npm run compile first")
    return json.loads(path.read_text())


def transact(w3, function, sender):
    tx = function.transact({"from": sender})
    receipt = w3.eth.wait_for_transaction_receipt(tx, timeout=120)
    if receipt.status != 1:
        raise RuntimeError(f"transaction reverted: {tx.hex()}")
    return receipt


def deploy(w3, name, admin):
    a = artifact(name)
    factory = w3.eth.contract(abi=a["abi"], bytecode=a["bytecode"])
    receipt = transact(w3, factory.constructor(admin), admin)
    return w3.eth.contract(address=receipt.contractAddress, abi=a["abi"]), receipt


def setup_with_gas():
    """Like setup(), plus per-method deployment and issuer-authorization gas."""
    w3 = local_chain()
    admin, issuer, attacker = w3.eth.accounts[:3]
    single, single_deploy = deploy(w3, "CredentialRegistry", admin)
    batch, batch_deploy = deploy(w3, "BatchCredentialRegistry", admin)
    gas = {}
    for method, contract, deployed in (("individual", single, single_deploy),
                                       ("merkle_batch", batch, batch_deploy)):
        authorized = transact(w3, contract.functions.setIssuer(issuer, True), admin)
        gas[method] = {"deploy_gas": deployed.gasUsed, "authorize_gas": authorized.gasUsed}
    return w3, admin, issuer, attacker, single, batch, gas


def setup():
    return setup_with_gas()[:6]
