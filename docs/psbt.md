
# Daily Operation: Signing PSBT Files

## PSBT Files

You need to construct the PSBT file on another system.
The CKBunker does not track the blockchain or know your UTXO. We will not make
any assumptions about how you create PSBT files, and there are a growing number of
wallets that can do it: BitcoinCore and Electrum at a minimum.

For testing purposes, we recommend
[`psbt_faker`](https://github.com/Coldcard/psbt_faker) which will
take your XPUB, and make arbitrary fake transactions immediately
suitable for signing as PSBT files.
This is a good way to test your policy choices with specific values and other what-ifs.

## Sign Transaction Tab

(screen shot)

- step by step w/ shot each?


# Next Steps

[Msg Signing](msg-signing.md)
