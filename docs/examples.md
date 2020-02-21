## Example CKBunker Use Cases

### Sign small transactions with just a password

You can set a password and have your Coldcard sign anything below a custom amount provided you enter that password.
Or instead require you to type a pin into the Coldcard for verification. [@6102](https://twitter.com/6102bitcoin/status/1228425672827293696)

### 2/2 multisig with geographic separation and specific spending rules

You can use another Coldcard and program it to make sure no transactions get through that don't adhere to a set of rules you set in advance. This uses 2/2 multisig (meaning your regular wallet is the first and the Coldcard is the second, both needed to send any transaction).

Your regular wallet will sign any transaction you send, but the Coldcard is like a security guard that won't also sign the transaciton unless it follows the rules you set. Rules can include where the bitcoins go (so if an attacker tries to steal your BTC using your main wallet, the Coldcard won't sign).

Rules could also include a time of day or a max amount per day (or any other period of time). For a long-term hodl you might not want to let anyone be able to send the whole amount at once.

What's cool is that this Coldcard could be located anywhere in the world and still sign your transaction.

Because we give the Coldcard a set of rules we can let it execute automatically and sign any transaction that your main wallet presents, as long as the transaction follows whatever rules you set. An attacker would have to nab both your main wallet and the Coldcard (and possibly even reprogram the CC).

While a geographically distributed 2/2 multi-sig is already possible today, it would require someone on the other end to click the buttons and co-sign. As this is pre-programmed it can run automatically and sign any TX within the rules.

[Ben Prentice](https://twitter.com/mrcoolbp/status/1228868296486924289)

### Geographic separation

Advanced: Your Coldcard could be in another country; you can lock Coldcard (boot-to-HSM™ feature). Remote hands can do power cycles if needed & keep Bunker running.  Video-conference with them to send  6-digit code to complete a PSBT authentication (entered on Coldcard keypad). [@DocHex](https://twitter.com/DocHex/status/1228392653592649728)


### Freeze your warm wallet

The HSM policy on your Coldcard could enable spending to just one single cold-storage address (via a whitelist). When your warm wallet is in danger, pull this cord to collect all UTXOs and send them to safety, signed, unattended, by the COLDCARDwallet
[@DocHex](https://twitter.com/DocHex/status/1228394738841157632)

### Meet-me-in-the-Bunker™

Time-based 2FA code from the phones of 3 of these 5 executives needed to authorize spending; Each exec connects to Bunker at the same time, checks proposed transaction and adds their OTP code. Only the Coldcard and exec's phone knows the shared 2FA secret. [@DocHex](https://twitter.com/DocHex/status/1228395590662397953)
·

### Text message signing

You can disable PSBT signing completely and allow automatic signatures on text messages. This turn the Coldcard wallet
 into an HSM for Bitcoin-based auth/attestations. Can be limited to specific BIP32 subpath derivations. Same with address generation/derived XPUBS. [@DocHex](https://twitter.com/DocHex/status/1228396805102194688)
 
 
### Storage Locker™

There is a locker of about 400 bytes of secret storage in the Mk3 secure element. CK Bunker uses this to hold the secret that encrypts bunker's settings (when at rest), such as the private key for the address of the Tor hidden service. So a corrupt LEA <!-- what is LEA? --> can't impersonate your bunker after capture. [@DocHex](https://twitter.com/DocHex/status/1228398842313310208)

### Multsig

Heard you like co-signing! All the Bunker/HSM features work with multisig (P2SH / P2WSH) so maybe you're automatically co-signing some complex multisig from a CasaHODL quorum. [@DocHex](https://twitter.com/DocHex/status/1228403787955687427)



