// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;
import {IssuerAuthority} from "./IssuerAuthority.sol";

/// @notice Experimental alternative: one sorted-pair Merkle root per batch.
contract BatchCredentialRegistry is IssuerAuthority {
    struct Batch { address issuer; bytes32 root; bool revoked; }
    mapping(bytes32 => Batch) public batches;
    mapping(bytes32 => mapping(bytes32 => bool)) public revokedCredentials;
    event BatchIssued(bytes32 indexed batchId, address indexed issuer, bytes32 root);
    event BatchRevoked(bytes32 indexed batchId);
    event CredentialRevoked(bytes32 indexed batchId, bytes32 indexed credentialId);

    constructor(address administrator) IssuerAuthority(administrator) {}
    function issueBatch(bytes32 batchId, bytes32 root) external onlyIssuer {
        if (batchId == bytes32(0) || root == bytes32(0)) revert InvalidInput();
        if (batches[batchId].issuer != address(0)) revert AlreadyExists();
        batches[batchId] = Batch(msg.sender, root, false);
        emit BatchIssued(batchId, msg.sender, root);
    }
    function _checkOwner(bytes32 batchId) internal view {
        address issuer = batches[batchId].issuer;
        if (issuer == address(0)) revert NotFound();
        if (msg.sender != issuer && msg.sender != admin) revert Unauthorized();
    }
    function revokeBatch(bytes32 batchId) external {
        _checkOwner(batchId);
        if (batches[batchId].revoked) revert AlreadyExists();
        batches[batchId].revoked = true;
        emit BatchRevoked(batchId);
    }
    function revokeCredential(bytes32 batchId, bytes32 credentialId) external {
        _checkOwner(batchId);
        if (credentialId == bytes32(0)) revert InvalidInput();
        if (revokedCredentials[batchId][credentialId]) revert AlreadyExists();
        revokedCredentials[batchId][credentialId] = true;
        emit CredentialRevoked(batchId, credentialId);
    }
    function leaf(address issuer, bytes32 batchId, bytes32 id, bytes32 commitment)
        public pure returns (bytes32) {
        // Double hashing separates the 128-byte leaf preimage from 64-byte tree nodes.
        return keccak256(bytes.concat(keccak256(abi.encode(issuer, batchId, id, commitment))));
    }
    function verify(bytes32 batchId, bytes32 id, bytes32 commitment, bytes32[] calldata proof)
        external view returns (bool) {
        Batch storage b = batches[batchId];
        if (b.issuer == address(0) || !authorizedIssuers[b.issuer] || b.revoked
            || revokedCredentials[batchId][id] || id == bytes32(0)) return false;
        bytes32 h = leaf(b.issuer, batchId, id, commitment);
        for (uint256 i; i < proof.length; ++i) {
            bytes32 p = proof[i];
            h = h < p ? keccak256(abi.encodePacked(h, p)) : keccak256(abi.encodePacked(p, h));
        }
        return h == b.root;
    }
}
