// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;
import {IssuerAuthority} from "./IssuerAuthority.sol";

/// @notice Baseline: one storage record and one transaction per credential.
contract CredentialRegistry is IssuerAuthority {
    struct Record { address issuer; bytes32 commitment; bool revoked; }
    mapping(bytes32 => Record) public records;
    event CredentialIssued(bytes32 indexed id, address indexed issuer, bytes32 commitment);
    event CredentialRevoked(bytes32 indexed id);

    constructor(address administrator) IssuerAuthority(administrator) {}
    function issue(bytes32 id, bytes32 commitment) external onlyIssuer {
        if (id == bytes32(0) || commitment == bytes32(0)) revert InvalidInput();
        if (records[id].issuer != address(0)) revert AlreadyExists();
        records[id] = Record(msg.sender, commitment, false);
        emit CredentialIssued(id, msg.sender, commitment);
    }
    function revoke(bytes32 id) external {
        Record storage r = records[id];
        if (r.issuer == address(0)) revert NotFound();
        // Disabled issuers may still revoke compromised credentials.
        if (msg.sender != r.issuer && msg.sender != admin) revert Unauthorized();
        if (r.revoked) revert AlreadyExists();
        r.revoked = true;
        emit CredentialRevoked(id);
    }
    function verify(bytes32 id, bytes32 commitment) external view returns (bool) {
        Record storage r = records[id];
        return r.issuer != address(0) && authorizedIssuers[r.issuer]
            && !r.revoked && r.commitment == commitment;
    }
}
