// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;
import {CredentialRegistry} from "../src/contracts/CredentialRegistry.sol";
import {BatchCredentialRegistry} from "../src/contracts/BatchCredentialRegistry.sol";
import {IssuerAuthority} from "../src/contracts/IssuerAuthority.sol";

// Minimal cheatcode interface: no external forge-std dependency.
interface Vm {
    function prank(address) external;
    function expectRevert(bytes4) external;
}
contract RegistryTest {
    Vm constant vm = Vm(address(uint160(uint256(keccak256("hevm cheat code")))));
    CredentialRegistry single;
    BatchCredentialRegistry batch;
    address issuer = address(0x1234);
    address attacker = address(0xBAD);
    bytes32 constant ID = bytes32(uint256(1));
    bytes32 constant HASH = bytes32(uint256(2));
    bytes32 constant BATCH = bytes32(uint256(3));

    function setUp() public {
        single = new CredentialRegistry(address(this));
        batch = new BatchCredentialRegistry(address(this));
        single.setIssuer(issuer, true);
        batch.setIssuer(issuer, true);
    }
    function testLifecycle() public {
        vm.prank(issuer);
        single.issue(ID, HASH);
        require(single.verify(ID, HASH), "valid credential rejected");
        require(!single.verify(ID, bytes32(uint256(9))), "tamper accepted");
        vm.prank(issuer);
        single.revoke(ID);
        require(!single.verify(ID, HASH), "revoked credential accepted");
    }
    function testUnauthorizedIssue() public {
        vm.expectRevert(IssuerAuthority.Unauthorized.selector);
        vm.prank(attacker);
        single.issue(ID, HASH);
    }
    function testUnauthorizedRevoke() public {
        vm.prank(issuer);
        single.issue(ID, HASH);
        vm.expectRevert(IssuerAuthority.Unauthorized.selector);
        vm.prank(attacker);
        single.revoke(ID);
    }
    function testDuplicateIssue() public {
        vm.prank(issuer);
        single.issue(ID, HASH);
        vm.expectRevert(IssuerAuthority.AlreadyExists.selector);
        vm.prank(issuer);
        single.issue(ID, HASH);
    }
    function testSuspension() public {
        vm.prank(issuer);
        single.issue(ID, HASH);
        single.setIssuer(issuer, false);
        require(!single.verify(ID, HASH), "disabled issuer accepted");
    }
    function testBatchLifecycle() public {
        bytes32 root = batch.leaf(issuer, BATCH, ID, HASH);
        vm.prank(issuer);
        batch.issueBatch(BATCH, root);
        bytes32[] memory proof = new bytes32[](0);
        require(batch.verify(BATCH, ID, HASH, proof), "batch credential rejected");
        vm.prank(issuer);
        batch.revokeCredential(BATCH, ID);
        require(!batch.verify(BATCH, ID, HASH, proof), "revocation ignored");
    }
    function testFuzzTampering(bytes32 wrongHash) public {
        if (wrongHash == HASH) return;
        vm.prank(issuer);
        single.issue(ID, HASH);
        require(!single.verify(ID, wrongHash), "tamper accepted");
    }
}
