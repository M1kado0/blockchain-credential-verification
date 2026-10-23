// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

/// @notice Prototype issuer directory. Institutional identity must be checked off-chain.
abstract contract IssuerAuthority {
    address public admin;
    address public pendingAdmin;
    mapping(address => bool) public authorizedIssuers;
    error Unauthorized();
    error InvalidInput();
    error AlreadyExists();
    error NotFound();
    event IssuerAuthorization(address indexed issuer, bool authorized);
    event AdminProposed(address indexed proposed);
    event AdminTransferred(address indexed previous, address indexed current);

    constructor(address administrator) {
        if (administrator == address(0)) revert InvalidInput();
        admin = administrator;
    }
    modifier onlyAdmin() {
        if (msg.sender != admin) revert Unauthorized();
        _;
    }
    modifier onlyIssuer() {
        if (!authorizedIssuers[msg.sender]) revert Unauthorized();
        _;
    }
    function setIssuer(address issuer, bool authorized) external onlyAdmin {
        if (issuer == address(0)) revert InvalidInput();
        authorizedIssuers[issuer] = authorized;
        emit IssuerAuthorization(issuer, authorized);
    }
    function proposeAdmin(address proposed) external onlyAdmin {
        if (proposed == address(0)) revert InvalidInput();
        pendingAdmin = proposed;
        emit AdminProposed(proposed);
    }
    function acceptAdmin() external {
        if (msg.sender != pendingAdmin) revert Unauthorized();
        address previous = admin;
        admin = msg.sender;
        pendingAdmin = address(0);
        emit AdminTransferred(previous, admin);
    }
}
