# GateSeal ⛩️

A one-time panic button for pausable contracts.

![](/assets/monty-python.png)

## What is a GateSeal?

A GateSeal is a contract that allows the designated account to instantly put a set of contracts on pause (i.e. seal) for a limited duration. GateSeals are meant to be used as a panic button for crucial contracts in case of an emergency. Each GateSeal is one-time use only and immediately becomes unusable once activated. If the seal was never triggered, the GateSeal would still eventually after a set period.

## What is it for?

To put such crucial components of the Lido protocol as `WithdrawalQueue` and `ValidatorExitBus` on hold, the DAO must hold a vote which may take up to several days to pass. GateSeals provide a way to temporarily pause these contracts immediately if the emergency calls for a swifter response. This will give the Lido DAO the time to come up with a solution, hold a vote, implement changes, etc.

## How does it work?

A GateSeal is set up with an immutable configuration at the time of construction:
- the sealing committee, an account responsible for triggering the seal,
- the seal duration, a period for which the contracts will be sealed,
- the sealables, a list of contracts to be sealed,
- the expiry period, a period after which the GateSeal becomes unusable. 

If an emergency arises, the sealing committee simply calls the seal function and puts the contracts on pause for the set duration. 

While GateSeals provide a quick and easy way to safeguard the protocol from unexpected situations, it is undesireable for a decentralized protocol to rely on a multisig in any capacity. This is why GateSeals are only a temporary solution and, thus, implement a kind of "inconvenience bomb" in that each GateSeal has a limited lifespan and must be set up anew once expired. This encourages the protocol to come with a sustainable long-term solution sooner rather than later.

## How are GateSeals created?

GateSeals are created using the GateSealFactory. The factory uses the blueprint pattern whereby new GateSeals are deployed using the initcode (blueprint) stored onchain. The blueprint is essentially a broken GateSeal that can only be used to create new GateSeals.

While Vyper offers ways to create new contracts, we opted to use the blueprint pattern because it creates a fully autonomous contract without any dependencies. Unlike other contract-creating functions, [`create_from_blueprint`](https://docs.vyperlang.org/en/stable/built-in-functions.html#chain-interaction) invokes the constructor of the contract, thus, helping avoid the initilization shenanigans.

The blueprint follows the [EIP-5202](https://eips.ethereum.org/EIPS/eip-5202) format, which includes a header that makes the contract uncallable and specifies the version. 

## Contributing

### Prerequisites
This project was developed using these dependencies with their exact versions listed below:
- Python 3.10
- Poetry 1.1.13
- Node.js 16.14.2
- Yarn 1.22.19

Other versions may work as well but were not tested at all.

### Setup

1. Activate poetry virtual environment,
```shell
poetry shell
```

2. Install Python dependencies
```shell
poetry install
```

3. Install Node.js modules
```shell
yarn
```

### Test

By default tests run on the local Hardhat network,
```shell
ape test
```

### Deploy
TODO

## Helpful links
TODO