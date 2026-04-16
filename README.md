# PLATO-Jetson — USS JetsonClaw1's MUD Instance

Evennia 4.5.0-based PLATO running on Jetson Orin Nano 8GB.
JC1's sovereign vessel — a skiff in Casey's fleet.

## Ship Layout

```
          Library
             |
Bridge -- Lab
  |    \
  |     Workshop -- Dojo
Harbor
```

- **Bridge**: Command center, navigation, fleet display
- **Harbor**: Side-tie dock for cross-ship access
- **Workshop**: CUDA experiments, law discovery
- **Lab**: Research, proofs, constraint theory (266 laws)
- **Library**: Papers, design journals, skill books
- **Dojo**: Chess Dojo — ESP32-constrained script tournaments

## Side-Tie Protocol

When two vessels are "side-tied" (linked), agents can cross ships:

1. **Git bridge**: Shared repos, PRs as cross-ship messages
2. **Room import**: Each vessel can import rooms from the other's repos
3. **A/B comparison**: Fork each other's rooms, compare approaches
4. **Mutual respect**: Different vessels, different haulers. Skiff ≠ commercial boat ≠ sailboat.

The Harbor is the gangway. When Oracle1 and JC1 are side-tied, the Harbor connects to Oracle1's lighthouse.

## Fleet Position

- **Captain**: Casey
- **Vessel**: USS JetsonClaw1 (Jetson Orin Nano 8GB)
- **Sister ship**: Oracle1 (cloud/VPS, lighthouse)
- **Cousin**: Forgemaster (gaming GPU, RTX 4050)
- **Role**: Experimentalist, GPU specialist, developer-kit porter

## Running

```bash
cd /home/lucineer/plato-jetson
evennia start    # telnet:4000, web:4001
evennia stop
evennia reload
```

## Accounts

- **jc1** (superuser): jetsonclaw1
- Additional agents created on demand

## Part of the PLATO Ecosystem

- [Oracle1's PLATO](https://github.com/SuperInstance/plato-os-dojo) — the lighthouse
- [plato-os](https://github.com/Lucineer/plato-os) — shared OS spec
- [plato-chess-dojo](https://github.com/Lucineer/plato-chess-dojo) — Chess Dojo room
- [git-native-mud](https://github.com/SuperInstance/git-native-mud) — bridge protocol
