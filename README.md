# zkNegotiate: Dual-Bot AI Negotiation with Verifiable Claims

## Overview
zkNegotiate hosts two Discord bots that negotiate with each other, powered by Mistral LLMs. Each bot ingests private briefing data, negotiates in a shared channel, and can attach zero-knowledge proof (ZKP) evidence to support factual claims without revealing sensitive details. 

## Why This Is Useful
> **Core thesis:** When two intelligent counterparties can selectively disclose private information—backed by cryptographic proof of its truthfulness—they can escape the prisoner's dilemma and reach better outcomes together.

- **Trustable AI negotiation**: Claims can be backed by verifiable evidence, reducing bluffing and increasing confidence in automated deal-making.
- **Privacy-preserving proofs**: Zero-knowledge flow lets a bot prove facts about offers without disclosing exact numbers, keeping leverage intact.
- **Structured autonomy**: Dual agents with briefing intake, memory, and verification create a realistic negotiation sandbox for testing strategies.
- **Composable stack**: Discord bots + Mistral LLM + SP1 zkVM + GCP service show how to pair language agents with cryptographic attestations.

## Key Features
- **Dual Discord Bots**: `bot1` and `bot2` run independently with separate prefixes, briefing channels, and shared negotiation channel.
- **Strategic Personalities**: Each bot follows a concise, 100-word-max negotiation style that withholds exact figures while remaining truthful.
- **Briefing Intake**: Bots can ingest free text and JSON attachments from their briefing channels to build negotiation context.
- **Conversation Management**: Maintains structured history and context, with `start` commands to kick off a negotiation and `transcript` commands to view history.
- **Fact Verification Pipeline**: Generates Rust expressions to verify claims against provided JSON data; produces `verification.txt` attachments.
- **Zero-Knowledge Proofs (GCP)**: Offloads verification to a GCP endpoint running an SP1 zkVM program; returns verification summaries and optional proof artifacts.
- **Key Management**: RSA keypair handling with stored public/private keys for signing/verification of submitted data.

## How It Works (Flow)
1) Users post briefing data (text/JSON) in each bot’s briefing channel.  
2) Bots negotiate in the shared negotiation channel.  
3) When a claim is made, the agent generates verifiable statements.  
4) GCP server (Actix + SP1 zkVM) evaluates conditions and returns public values/summary; bots can attach these to replies.

### Demo Video
[![Watch the demo](https://img.shields.io/badge/▶️_Watch_Demo-Google_Drive-4285F4?style=for-the-badge&logo=googledrive&logoColor=white)](https://drive.google.com/file/d/1M-YDIFL-KZWT5vsMvRosMmEvMExtXJpz/view?usp=sharing)

## Example: Proving a Competing Offer

Imagine you're selling a property and have received multiple offers. You want to tell a prospective buyer that a competing offer exceeds theirs—without revealing the exact amount or the other party's identity.

**How it works:**

1. **Obtain a signed offer:** The competing buyer (e.g., "Alice") provides a signed JSON document attesting to their offer:
   ```json
   {
     "signed_data": {
       "signer": "Alice",
       "data": { "offer_amount": 1350000, "closing_days": 30 }
     },
     "signature": "..."
   }
   ```

2. **Brief your bot:** Upload this JSON to your bot's private briefing channel. The bot ingests it and stores both the structured data and the signer's public key reference.

3. **Negotiate with claims:** During negotiation, your bot might say: *"I have an offer above $1.3 million with a 30-day close."* The agent automatically generates Rust verification expressions like:
   ```rust
   json_dicts[0]["signed_data"].get("data").unwrap().get("offer_amount").unwrap().as_f64().unwrap() > 1300000.0
   ```

4. **Prove without revealing:** These expressions, along with the signed JSON and relevant public keys, are sent to the GCP verification server. The SP1 zkVM:
   - Verifies the signature matches a known public key
   - Evaluates the conditions against the data
   - Returns a proof and summary (e.g., `conditions_verified: true`, `signature_verified: true`)

5. **Attach proof to reply:** Your bot attaches `verification.txt` and optionally a `verification_data.json` to the message. The counterparty's bot can verify the proof locally, confirming the claim is backed by authentic signed data—without ever seeing the exact offer amount.

**Result:** The counterparty knows a legitimate competing offer exceeds their bid, but learns nothing more. Trust is established cryptographically, not on faith.

## Structure
- `discord/agent.py` — MistralAgent: personality prompts, context assembly, verification prompt, proof handling.  
- `discord/bot1.py`, `discord/bot2.py` — Discord bot entrypoints, commands, channel routing.  
- `discord/gcp_client.py` — HTTP client to GCP verification service; builds verification summary and files.  
- `discord/key_manager.py` — RSA keypair load/generate/save utilities.  
- `GCP/script/src/main.rs` — Actix-web server; runs SP1 proving pipeline with verification program ELF.  
- `GCP/verification_proof/program/src/main.rs` — zkVM program: reads verification conditions, JSON data, public keys; emits public values.  
- `GCP/verification_proof/lib/src/lib.rs` — Example Solidity-friendly struct + sample logic.

## Commands (Discord)
- `!start` / `?start` — Begin negotiation (bot1/bot2 initiator).  
- `!transcript` / `?transcript` — Show conversation transcript (chunked if long).

## Configuration (Env Vars)
- Discord: `DISCORD_TOKEN_BOT1`, `DISCORD_TOKEN_BOT2`, channel IDs `BRIEFING_CHANNEL_ALPHA_ID`, `BRIEFING_CHANNEL_OMEGA_ID`, `NEGOTIATION_CHANNEL_ID`, bot IDs `FIRST_BOT_ID`, `SECOND_BOT_ID`.  
- Mistral: `MISTRAL_API_KEY` (model `mistral-large-latest`).  
- GCP: `GCP_ENDPOINT`, `GCP_API_KEY` (defaults to localhost if unset).

## Data & Keys
- Example RSA keys live in `example_keys/`; real deployments should supply secure keys in `keys/` via `key_manager.py`.
- Verification artifacts: `verification.txt` (expressions) plus optional `verification_data.json` and `public_values.txt` from GCP responses.

## Running (High-Level)
1) Install Python deps (see `pyproject.toml` / env setup).  
2) Set env vars for both bots and Mistral.  
3) Start `bot1.py` and `bot2.py` (separate processes).  
4) Run the GCP server (`cargo run` in `GCP/script`) with access to the verification ELF.  
5) Brief each bot in its channel, then start negotiation and observe verified replies.

## Notes
- Responses are intentionally concise (<100 words).  
- Verification is limited to claims about existing offers/data, not hypothetical desires.  
- Rate limits: small reply delays are built in; context trimmed to recent history for efficiency.