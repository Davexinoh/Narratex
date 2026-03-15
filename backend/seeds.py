"""
seeds.py
Narratex — Single source of truth for narrative seed keywords and token maps.

Both collector.py and extractor.py import from here.
fetch_narratives.py (OpenClaw skill) maintains its own copy — keep in sync.
"""

NARRATIVE_SEEDS = {
    "AI Infrastructure": [
        "ai", "artificial intelligence", "machine learning", "llm", "gpu compute",
        "fetch", "rndr", "render", "tao", "bittensor", "akt", "akash",
        "worldcoin", "wld", "gpt", "openai", "deai",
    ],
    "DePIN Compute": [
        "depin", "decentralized physical", "helium", "hnt", "iotex",
        "hivemapper", "geodnet", "render", "akash", "filecoin",
        "infrastructure", "compute network", "node operator",
    ],
    "Gaming Infrastructure": [
        "gamefi", "gaming", "web3 game", "play to earn", "p2e",
        "imx", "immutable", "ronin", "ron", "magic", "treasure",
        "beam", "gala", "gods unchained", "axie", "sandbox", "decentraland",
    ],
    "RWA Tokenization": [
        "rwa", "real world asset", "tokenized", "tokenization",
        "ondo", "centrifuge", "maple", "goldfinch", "truefi",
        "real estate token", "treasury token", "institutional defi",
    ],
    "Layer 2 Scaling": [
        "layer 2", "l2", "rollup", "optimism", "op", "arbitrum",
        "arb", "base", "zksync", "polygon", "matic", "starknet",
        "scaling", "ethereum scaling", "eip", "blob",
    ],
    "DeFi Resurgence": [
        "defi", "yield", "liquidity", "amm", "dex", "lending",
        "aave", "compound", "uniswap", "uni", "curve", "crv",
        "gmx", "hyperliquid", "perp", "derivatives", "tvl",
    ],
    "Bitcoin Ecosystem": [
        "bitcoin", "btc", "ordinals", "brc-20", "runes", "stacks",
        "stx", "lightning", "taproot", "btcfi", "wrapped bitcoin",
        "bitcoin layer", "bitcoin defi",
    ],
    "Solana Ecosystem": [
        "solana", "sol", "solana defi", "solana nft", "solana mobile",
        "jupiter", "jup", "raydium", "ray", "phantom", "saga",
        "solana gaming", "bonk", "meme sol", "pyth",
    ],
}

NARRATIVE_TOKENS = {
    "AI Infrastructure":     ["FET", "TAO", "RNDR", "AKT", "WLD", "AGIX", "OCEAN", "NMR"],
    "DePIN Compute":         ["HNT", "IOTX", "FIL", "AKT", "RNDR", "AR", "STORJ"],
    "Gaming Infrastructure": ["IMX", "RON", "MAGIC", "BEAM", "GALA", "SAND", "MANA", "AXS"],
    "RWA Tokenization":      ["ONDO", "CFG", "MPL", "TRU", "POLYX", "RIO"],
    "Layer 2 Scaling":       ["ARB", "OP", "MATIC", "ZKS", "STRK", "MANTA", "METIS"],
    "DeFi Resurgence":       ["AAVE", "UNI", "CRV", "GMX", "DYDX", "PENDLE", "JOE"],
    "Bitcoin Ecosystem":     ["STX", "ORDI", "SATS", "RUNE", "WBTC", "tBTC"],
    "Solana Ecosystem":      ["SOL", "JUP", "RAY", "BONK", "PYTH", "JTO", "ORCA"],
}
