# CryptoTaxTools

## Purpose
Figuring out capital gains and income from cryptocurrencies is a pain right now. I want to write some Python tools to aid in the process. I don't intend to make it very thourough for now, but it should make life a little easier for those calculating their gains manually without using other software like `Cointax` or `Cointracker`. 

I like to keep personal records whenever possible, and these tools should help with that goal.

Use the code here under your own responsibility. I am not a tax advisor or any type of advisor, so you must make sure that whatever numbers you get from using the modules in this repository are correct.

## Lot and Pool Classes
I wrote a couple of classes that provide the most functionality: `Lot` and `Pool`. The idea is to be able to represent each purchase of cryptocurrency as a single `Lot` object that lives inside a `Pool`.

Then, each lot object has its own cost basis and purchase date. This makes it simple to figure out the gains from it and also whether it consisted of a long or short term sale. 

A `Pool` will contain all the lots for that particular asset and can be used to keep track of the total quantity and average cost basis. You can think of a `Pool` as a wallet. For instance, if you have some `BTC` in `Coinbase`, some in `Coinbase Pro`, and some in a hardware wallet (like Trezor or Ledger), then you would create a `Pool` object for `BTC` for each of them.

Once you have different pools, you can transfer `BTC` from one to another with the `transfer()` method. You can also sell `BTC` with the `sell()` method. The pool 