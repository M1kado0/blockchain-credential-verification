# System model and deployment boundaries

Actors: administrator, institution issuer, credential holder, verifier. The
administrator vets university identities off-chain and authorizes their addresses.
The issuer prepares the exact document, packages its random salt and identifier,
and registers the commitment. The holder presents document/package/proof to a
verifier. The verifier selects a trusted chain and registry, checks the institution
directory and retrieves current contract state.

Adversaries may modify a document, invent an identifier, submit a wrong Merkle
proof, attempt unauthorized issuance/revocation, or reuse a root under another
issuer. Those cases are tested. Authorized malicious issuers, administrator key
compromise, consensus compromise and dishonest RPC results are outside the
integrity guarantees. Blockchain cannot validate the truth of an issued degree.

The governance directory stores only addresses, not institutional names. A real
deployment needs a trusted, maintained mapping between legal institutions and
addresses. Disabling and subsequently re-enabling an issuer restores all of its
non-revoked credentials; compromised issuance needs explicit revocation.
There is no key-rotation mechanism or upgradable proxy. Two-step admin transfer
reduces accidental handover but does not provide multisignature governance.

## Privacy

Public identifiers, issuer addresses, timing, event logs, commitments and roots
are visible. The SHA-256 commitment is computed as:

`SHA256("RK-ACADEMIC-CREDENTIAL-V1" || 0x00 || salt32 || exact_document_bytes)`.

Use a new unpredictable salt and ID for each actual credential. Public hashes
are not automatically legally anonymous. Loss of the salt makes byte-exact
verification impossible; loss of a batch proof creates availability problems.
The example credential and experiment records are explicitly synthetic.

## Kazakhstan discussion points, not implemented integrations

This repo does not claim legal recognition or integration with any state system.
For deployment, evaluate alongside university registrar systems, official digital
signatures and document-verification services. Confirm applicable personal-data,
records retention, accreditation, signature and electronic-document rules using
current official sources before making legal claims in the paper.

An NU scenario is illustrative only. No real NU diploma or student record is
used, and NU has not authorized these prototype issuer addresses. National
deployment needs institutional onboarding, authoritative key distribution,
registrar access controls, key compromise recovery, supported document formats,
proof retention, helpdesk workflows, governance and cost allocation. None of
these operational questions is resolved by observing a lower gas count.

W3C VC interoperability, selective disclosure, zero-knowledge proofs, EDS signing,
IPFS storage and Smart Bridge adapters are potential extensions and are not
implemented or evaluated here. No legal or literature claims from the earlier
conversation are silently treated as verified facts in this codebase.
