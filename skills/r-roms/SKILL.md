---
name: r-roms
description: Complete agent-native map of the r/ROMs Megathread site (r-roms.github.io). Contains every route path and every download link across all platform categories (General, Populars, Nintendo, Sony (PlayStation, PlayStation 2, PlayStation 3, PlayStation Portable, PlayStation Vita), Microsoft (Xbox, Xbox 360), Sega, Retro & Arcade, PC, and Miscellaneous). Load this skill when you need to locate any ROM, BIOS, set, or download path on the megathread without re-browsing the site. The full site source is also cloned locally at ~/claudeconfig/r-roms-site.
---

# r/ROMs Megathread — complete path map

## About
The r/ROMs Megathread site aggregates verified ROM, BIOS, and collection download links hosted on mirrors such as the Minerva Archive, Internet Archive, Open Directory, MEGA, and hShop. Every route below is a live site path; each entry lists the direct download mirrors. The full site source is cloned locally at `~/claudeconfig/r-roms-site` (a SvelteKit site, `src/routes/<category>/<page>/+page.svelte`).

## Notes shared across all pages
- **NoPayStation** (nopaystation.com) is the recommended source for PS3/PSP/PS Vita content — check it first, before the links below.
- Internet Archive items marked with a lock icon require a free IA account to download; Minerva mirrors are unrestricted.
- **No-Intro** and **Redump** are hash-catalogued collections of the best-available dumps for a system.
- Archives (ZIP/7z/RAR) must be extracted; 7-Zip is recommended.
- Use a download manager (JDownloader2, AB Download Manager) for bulk/resumable/browser-independent downloads.
- For torrents: use a torrent client (qBittorrent, LibreTorrent on Android); research VPN needs for your jurisdiction; never use a free VPN.

## Site map — every route path on the site
- \`/`\` — Home
- /General/ — General index (navigation shell)
- /Microsoft/ — Microsoft index (navigation shell)
- /Miscellaneous/ — Miscellaneous index (navigation shell)
- /Nintendo/ — Nintendo index (navigation shell)
- /PC/ — PC index (navigation shell)
- /Populars/ — Populars index (navigation shell)
- /Retro & Arcade/ — Retro & Arcade index (navigation shell)
- /Sega/ — Sega index (navigation shell)
- /Sony/ — Sony index — collection of Sony PlayStation games available for download
- `/General/ddl` — Direct Downloads (sites + download managers)
- `/General/torrents` — Torrents (clients, VPN, seedboxes, debrids)
- `/General/preservation` — Preservation Databases (No-Intro, Redump, TOSEC, Hasheous, IGDB, Screenscraper, RetroAchievements, SteamGridDB, HowLongToBeat)
- `/General/other` — Other Information (archive programs, adblock, bypassing download limits)
- `/Populars/about-rvz-files` — About RVZ files
- `/Populars/metroid` — Metroid
- `/Populars/mario` — Mario
- `/Populars/fire-emblem` — Fire Emblem
- `/Populars/zelda` — The Legend of Zelda
- `/Populars/pokemon` — Pokemon
- `/Populars/persona` — Persona
- `/Populars/super-smash-bros` — Super Smash Bros
- `/Populars/xenoblade` — Xenoblade
- `/Nintendo/nintendo-games` — Nintendo Games (FDS, NES, SNES, N64, GB/GBC, GBA, Pokemon Mini, Virtual Boy)
- `/Nintendo/nintendo-ds` — Nintendo DS
- `/Nintendo/nintendo-3ds` — Nintendo 3DS
- `/Nintendo/nintendo-gamecube` — Nintendo GameCube
- `/Nintendo/nintendo-wii` — Nintendo Wii
- `/Nintendo/nintendo-wii-u` — Nintendo Wii U
- `/PC/pc-games` — PC Games
- `/Miscellaneous/rom-sets` — ROM Sets
- `/Miscellaneous/bios-sets` — BIOS Sets
- `/Miscellaneous/other` — Other (non-ROM/BIOS files)
- `/Retro & Arcade/retro-games` — Retro Games
- `/Retro & Arcade/arcade` — Arcade
- `/Sega/sega-games` — SEGA Games
- `/Sega/sega-dreamcast` — Sega Dreamcast
- `/Sega/sega-saturn` — Sega Saturn
- `/Sega/sega-cd` — Sega CD
- `/Sony/nopaystation` — NoPayStation
- `/Sony/sony-playstation` — Sony PlayStation
- `/Sony/sony-playstation-2` — Sony PlayStation 2
- `/Sony/sony-playstation-3` — Sony PlayStation 3
- `/Sony/sony-playstation-portable` — Sony PlayStation Portable (PSP)
- `/Sony/sony-playstation-vita` — Sony PlayStation Vita
- `/Microsoft/microsoft-xbox` — Microsoft Xbox
- `/Microsoft/microsoft-xbox360` — Microsoft Xbox 360

---

## General

### /General/ddl — Direct Downloads
Sites:
- FMHY (https://fmhy.net/gaming#rom-sites) — large collection of free-media sites.
- Vimm's Lair (https://vimm.net) — files up to 3DS/PS3; one download at a time.
- Internet Archive (https://archive.org) — high-risk/traffic content locked behind a free account.
- Edge Emulation (https://edgeemu.net)
- StartGame (https://startgame.world)

Download Managers:
- AB Download Manager (https://abdownloadmanager.com)
- JDownloader2 (https://jdownloader.org/jdownloader2)

### /General/torrents — Torrents
Sites:
- FMHY (https://fmhy.net/gaming#rom-sites)
- Minerva (https://minerva-archive.org), Minerva Torrent Index (https://cdn.minerva-archive.org/torrents/) — torrent mirror of Myrient archive. Discord: https://discord.com/invite/MiNERVA-archive

Torrent Clients:
- qBittorrent (https://www.qbittorrent.org) — Windows, MacOS, Linux
- LibreTorrent (https://gitlab.com/proninyaroslav/libretorrent) — Android

VPN Providers (port forwarding allowed, OpenVPN/Wireguard):
- AirVPN (https://airvpn.org) — Windows, Linux, MacOS, Android
- Windscribe (https://windscribe.net) — Windows, Linux, MacOS, Android
- ProtonVPN (https://protonvpn.com) — Windows, Linux, MacOS, Android

Seedboxes:
- Seedr (https://www.seedr.cc) — TBD

Debrid Services:
- Torbox (https://torbox.app) — TBD

### /General/preservation — Preservation Databases
- No-Intro (https://no-intro.org) — accurate file hashes for flash media
- Redump (https://redump.info) — accurate file hashes for optical media
- TOSEC (https://www.tosecdev.org) — flash (TOSEC), optical (TOSEC-ISO), auxiliary (TOSEC-PIX)
- Hasheous (https://hasheous.org) — ROM hashes matched to metadata
- IGDB (https://www.igdb.com) — metadata and media for games
- Screenscraper (https://www.screenscraper.fr) — image/video media
- RetroAchievements (https://retroachievements.org) — retro game achievements
- SteamGridDB (https://www.steamgriddb.com) — front-end presentation images
- HowLongToBeat (https://howlongtobeat.com) — game/playtime tracking

### /General/other — Other Information
Archive programs:
- PeaZip (https://peazip.github.io) — Windows, MacOS, Linux — Most archive types
- 7Zip (https://www.7-zip.org) — Windows — Most archive types
- Files (iOS) — iOS — .zip (rename .7z to .zip)
- Windows Explorer — Windows — .zip

Adblock: Vivaldi, Brave, Helium browsers; uBlock Origin extension (Chrome/Firefox/Opera links). For Android: Firefox + uBlock Origin.

Bypassing download limits:
- Google Drive: sign in, add file shortcut to a new folder, download the folder as .zip.
- MEGA: 5 GB/24h limit; bypass with VPN or MegaBasterd (https://github.com/tonikelope/megabasterd) + proxy list.

---

## Populars

### /Populars/about-rvz-files — About RVZ files
RVZ works with Dolphin emulator, not real hardware; saves bandwidth. Convert to ISO for real hardware with Dolphin Emulator. Decryption: Batch CIA-3DS Decryptor (https://gbatemp.net/download/batch-cia-3ds-decryptor.35098/); AES keys from pastebin (https://pastebin.com/vRy8c6JP / https://web.archive.org/web/20220707222654/https://pastebin.com/tBY6RHh4). Windows: place `aes_keys.txt` in `C:/Users/<User>/AppData/Roaming/Citra/sysdata`. Linux/macOS: `~/.local/share/Citra-emu/sysdata/aes_keys.txt`.

### /Populars/metroid — Metroid
- Metroid Fusion (GBA) (USA): Minerva https://minerva-archive.org/browse/No-Intro/Nintendo%20-%20Game%20Boy%20Advance/Metroid%20Fusion%20(USA).zip | IA https://archive.org/download/No-Intro_GameBoy_Advance_Collection/mnt/user/ROMS/Nintendo/GBA_2/GBA.zip/GBA%2FMetroid%20Fusion%20%28USA%29.zip
- Metroid Zero Mission (GBA) (USA): Minerva .../Metroid%20-%20Zero%20Mission%20(USA).zip | IA .../GBA%2FMetroid%20-%20Zero%20Mission%20%28USA%29.zip
- Metroid Prime (GC) (USA): Minerva Redump NKit RVZ .../Metroid%20Prime%20(USA).zip | IA https://archive.org/download/GameCube-Redump-2024-Individual-Games-Part1/Metroid%20Prime%20%28USA%29.zip/
- Metroid Prime 2 (GC) (USA): Minerva .../Metroid%20Prime%202%20-%20Echoes%20(USA).zip | IA .../Metroid%20Prime%202%20-%20Echoes%20%28USA%29.zip/
- Metroid Prime 3 (Wii) (USA): Minerva .../Metroid%20Prime%203%20-%20Corruption%20(USA).zip | IA https://archive.org/download/Wii-Redump-2024-Individual-Games-Part4/Metroid%20Prime%203%20-%20Corruption%20%28USA%29.zip
- Metroid Prime Trilogy (Wii) (USA): Minerva .../Metroid%20Prime%20Trilogy%20(USA).zip | IA .../Metroid%20Prime%20Trilogy%20%28USA%29.zip
- Metroid - Samus Returns (3DS) (USA): IA https://archive.org/download/3DS-Redump-2024-Individual-Games-Part1/Metroid%20-%20Samus%20Returns%20%28USA%29%20%28En%2CFr%2CEs%29.zip

### /Populars/mario — Mario
- Mario Party 4 (GC) (USA): IA https://archive.org/download/GameCube-Redump-2024-Individual-Games-Part1/Mario%20Party%204%20%28USA%29%20%28Rev%201%29.zip
- Mario Party 5 (GC) (USA): IA .../Mario%20Party%205%20%28USA%29.zip
- Mario Party 6 (GC) (USA): IA .../Mario%20Party%206%20%28USA%29.zip
- Mario Party 7 (GC) (USA): Minerva Redump NKit RVZ .../Mario%20Party%207%20(USA)%20(Rev%201).zip | IA .../Mario%20Party%207%20%28USA%29%20%28Rev%201%29.zip
- Mario Party 8 (Wii) (USA): Minerva .../Mario%20Party%208%20(USA)%20(Rev%201).zip | IA https://archive.org/download/Wii-Redump-2024-Individual-Games-Part4/Mario%20Party%208%20%28USA%29%20%28Rev%201%29.zip
- Mario Party 9 (Wii) (USA): Minerva .../Mario%20Party%209%20(USA,%20Asia)%20(En,Fr,Es).zip | IA .../Mario%20Party%209%20%28USA%2C%20Asia%29%20%28En%2CFr%2CEs%29.zip
- Mario Kart Double Dash (GC) (USA): Minerva .../Mario%20Kart%20-%20Double%20Dash!!%20(USA).zip | IA https://archive.org/download/GameCube-Redump-2024-Individual-Games-Part1/Mario%20Kart%20-%20Double%20Dash%21%21%20%28USA%29.zip
- Mario Kart Wii (Wii) (USA): IA https://archive.org/download/Wii-Redump-2024-Individual-Games-Part4/Mario%20Kart%20Wii%20%28USA%29%20%28En%2CFr%2CEs%29.zip
- Super Paper Mario (Wii) (USA): Minerva .../Super%20Paper%20Mario%20(USA)%20(Rev%202).zip | IA https://archive.org/download/Wii-Redump-2024-Individual-Games-Part6/Super%20Paper%20Mario%20%28USA%29%20%28Rev%202%29.zip
- Super Mario Sunshine (GC) (USA): Minerva .../Super%20Mario%20Sunshine%20(USA).zip | IA https://archive.org/download/GameCube-Redump-2024-Individual-Games-Part2/Super%20Mario%20Sunshine%20%28USA%29.zip
- Super Mario Galaxy 1 (Wii) (USA): Minerva .../Super%20Mario%20Galaxy%20(USA)%20(En,Fr,Es).zip | IA https://archive.org/download/Wii-Redump-2024-Individual-Games-Part6/Super%20Mario%20Galaxy%20%28USA%29%20%28En%2CFr%2CEs%29.zip
- Super Mario Galaxy 2 (Wii) (USA): Minerva .../Super%20Mario%20Galaxy%202%20(USA)%20(En,Fr,Es).zip | IA .../Super%20Mario%20Galaxy%202%20%28USA%29%20%28En%2CFr%2CEs%29.zip
- New Super Mario Bros. Wii (Wii) (USA): Minerva .../New%20Super%20Mario%20Bros.%20Wii%20(USA)%20(En,Fr,Es)%20(Rev%202).zip | IA https://archive.org/download/Wii-Redump-2024-Individual-Games-Part4/New%20Super%20Mario%20Bros.%20Wii%20%28USA%29%20%28En%2CFr%2CEs%29%20%28Rev%202%29.zip

### /Populars/fire-emblem — Fire Emblem
- Fire Emblem Path of Radiance (GC) (USA): Minerva Redump NKit RVZ .../Fire%20Emblem%20-%20Path%20of%20Radiance%20(USA).zip | IA https://archive.org/download/GameCube-Redump-2024-Individual-Games-Part1/Fire%20Emblem%20-%20Path%20of%20Radiance%20%28USA%29.zip
- Fire Emblem Radiant Dawn (Wii) (USA): Minerva .../Fire%20Emblem%20-%20Radiant%20Dawn%20(USA)%20(Rev%201).zip | IA https://archive.org/download/Wii-Redump-2024-Individual-Games-Part2/Fire%20Emblem%20-%20Radiant%20Dawn%20%28USA%29%20%28Rev%201%29.zip
- Fire Emblem Fates Special Edition (3DS) (USA): Minerva No-Intro .../Fire%20Emblem%20Fates%20-%20Special%20Edition%20(USA).zip | IA https://archive.org/download/3DS-Redump-2024-Individual-Games-Part1/Fire%20Emblem%20Fates%20-%20Special%20Edition%20%28USA%29.zip

### /Populars/zelda — The Legend of Zelda
- Legend of Zelda Ocarina of Time (N64) (USA): Minerva No-Intro .../Legend%20of%20Zelda,%20The%20-%20Ocarina%20of%20Time%20(USA).zip | IA https://archive.org/download/pkmn_collection/Legend%20of%20Zelda%2C%20The%20-%20Ocarina%20of%20Time%20%28USA%29.zip
- Legend of Zelda Wind Waker (GC) (USA): Minerva Redump NKit RVZ .../Legend%20of%20Zelda%2C%20The%20-%20The%20Wind%20Waker%20%28USA%2C%20Canada%29.zip | IA https://archive.org/download/GameCube-Redump-2024-Individual-Games-Part1/Legend%20of%20Zelda%2C%20The%20-%20The%20Wind%20Waker%20%28USA%29.zip
- Legend of Zelda Ocarina of Time & Master Quest (GC) (USA): IA https://archive.org/download/GameCube-Redump-2024-Individual-Games-Part1/Legend%20of%20Zelda%2C%20The%20-%20Ocarina%20of%20Time%20%26%20Master%20Quest%20%28USA%29.zip
- Legend of Zelda Four Swords Adventures (GC) (USA): IA .../Legend%20of%20Zelda%2C%20The%20-%20Four%20Swords%20Adventures%20%28USA%29.zip
- Legend of Zelda Twilight Princess (Wii) (USA): Minerva .../Legend%20of%20Zelda,%20The%20-%20Twilight%20Princess%20(USA)%20(En,Fr,Es)%20(Rev%202).zip | IA https://archive.org/download/Wii-Redump-2024-Individual-Games-Part3/Legend%20of%20Zelda%2C%20The%20-%20Twilight%20Princess%20%28USA%29%20%28En%2CFr%2CEs%29%20%28Rev%202%29.zip
- Legend of Zelda Twilight Princess (GC) (USA): Minerva .../Legend%20of%20Zelda,%20The%20-%20Twilight%20Princess%20(USA).zip | IA https://archive.org/download/GameCube-Redump-2024-Individual-Games-Part1/Legend%20of%20Zelda%2C%20The%20-%20Twilight%20Princess%20%28USA%29.zip
- Legend of Zelda Ocarina of Time 3D (3DS) (USA): Minerva No-Intro .../Legend%20of%20Zelda,%20The%20-%20Ocarina%20of%20Time%203D%20(USA)%20(En,Fr,Es).zip | IA https://archive.org/download/3DS-Redump-2024-Individual-Games-Part1/Legend%20of%20Zelda%2C%20The%20-%20Ocarina%20of%20Time%203D%20%28USA%29%20%28En%2CFr%2CEs%29%20%28Rev%201%29.zip
- Legend of Zelda Skyward Sword (Wii) (USA): Minerva .../Legend%20of%20Zelda,%20The%20-%20Skyward%20Sword%20(USA)%20(En,Fr,Es)%20(Rev%202).zip | IA https://archive.org/download/Wii-Redump-2024-Individual-Games-Part3/Legend%20of%20Zelda%2C%20The%20-%20Skyward%20Sword%20%28USA%29%20%28En%2CFr%2CEs%29%20%28Rev%202%29.zip
- Legend of Zelda A Link Between Worlds (3DS) (USA): IA https://archive.org/download/3DS-Redump-2024-Individual-Games-Part1/Legend%20of%20Zelda%2C%20The%20-%20A%20Link%20Between%20Worlds%20%28USA%29%20%28En%2CFr%2CEs%29.zip
- Legend of Zelda Majora's Mask 3D (3DS) (USA): IA https://archive.org/download/3DS-Redump-2024-Individual-Games-Part1/Legend%20of%20Zelda%2C%20The%20-%20Majora%27s%20Mask%203D%20%28USA%29%20%28En%2CFr%2CEs%29%20%28Rev%201%29.zip
- Legend of Zelda Breath of the Wild (Wii U) (USA): Minerva Game https://minerva-archive.org/browse/No-Intro/Nintendo%20-%20Wii%20U%20(Digital)%20(CDN)/Legend%20of%20Zelda,%20The%20-%20Breath%20of%20the%20Wild%20(USA).zip / Update ...(Update).zip / DLC ...(DLC).zip | IA Game https://archive.org/download/wii-u-retail-nus-usa/The%20Legend%20of%20Zelda%20Breath%20of%20the%20Wild%20%5B00050000101C9400%5D.7z / Update ...[UPDATE%20v208%5D.7z / DLC ...[DLC%5D.7z

### /Populars/pokemon — Pokemon
- Pokemon Red (GB) (USA): Minerva No-Intro .../Pokemon%20-%20Red%20Version%20(USA,%20Europe)%20(SGB%20Enhanced).zip | IA https://archive.org/download/pkmn_collection/pkmn%20collection/GB/Pokemon%20-%20Red%20Version%20%28USA%2C%20Europe%29%20%28SGB%20Enhanced%29.zip
- Pokemon Green (GB) (Japan): Minerva .../Pocket%20Monsters%20-%20Midori%20(Japan)%20(SGB%20Enhanced).zip | IA .../Pocket%20Monsters%20-%20Midori%20%28Japan%29%20%28SGB%20Enhanced%29.zip
- Pokemon Blue (GB) (USA): Minerva .../Pokemon%20-%20Blue%20Version%20(USA,%20Europe)%20(SGB%20Enhanced).zip | IA .../Pokemon%20-%20Blue%20Version%20%28USA%2C%20Europe%29%20%28SGB%20Enhanced%29.zip
- Pokemon Yellow (GB) (USA): Minerva .../Pokemon%20-%20Yellow%20Version%20-%20Special%20Pikachu%20Edition%20(USA,%20Europe)%20(CGB+SGB%20Enhanced).zip | IA .../Pokemon%20-%20Yellow%20Version%20-%20Special%20Pikachu%20Edition%20%28USA%2C%20Europe%29%20%28CGB%2BSGB%20Enhanced%29.zip
- Pokemon Gold (GBC) (USA): Minerva .../Pokemon%20-%20Gold%20Version%20(USA,%20Europe)%20(SGB%20Enhanced)%20(GB%20Compatible).zip | IA .../Pokemon%20-%20Gold%20Version%20%28USA%2C%20Europe%29%20%28SGB%20Enhanced%29%20%28GB%20Compatible%29.zip
- Pokemon Silver (GBC) (USA): Minerva .../Pokemon%20-%20Silver%20Version%20(USA,%20Europe)%20(SGB%20Enhanced)%20(GB%20Compatible).zip | IA .../Pokemon%20-%20Silver%20Version%20%28USA%2C%20Europe%29%20%28SGB%20Enhanced%29%20%28GB%20Compatible%29.zip
- Pokemon Crystal (GBC) (USA): Minerva .../Pokemon%20-%20Crystal%20Version%20(USA).zip | IA https://archive.org/download/pkmn_collection/pkmn%20collection/GBC/Pokemon%20-%20Crystal%20Version%20%28USA%29.zip
- Pokemon Ruby (GBA) (USA): Minerva .../Pokemon%20-%20Ruby%20Version%20(USA,%20Europe).zip | IA https://archive.org/download/pkmn_collection/pkmn%20collection/GBA/Pokemon%20-%20Ruby%20Version%20%28USA%29.zip
- Pokemon Sapphire (GBA) (USA): Minerva .../Pokemon%20-%20Sapphire%20Version%20(USA,%20Europe).zip | IA .../Pokemon%20-%20Sapphire%20Version%20%28USA%29.zip
- Pokemon FireRed (GBA) (USA): Minerva .../Pokemon%20-%20FireRed%20Version%20(USA,%20Europe).zip | IA .../Pokemon%20-%20FireRed%20Version%20%28USA%29.zip
- Pokemon LeafGreen (GBA) (USA): Minerva .../Pokemon%20-%20LeafGreen%20Version%20(USA,%20Europe).zip | IA .../Pokemon%20-%20LeafGreen%20Version%20%28USA%29.zip
- Pokemon Emerald (GBA) (USA): Minerva .../Pokemon%20-%20Emerald%20Version%20(USA,%20Europe).zip | IA .../Pokemon%20-%20Emerald%20Version%20%28USA%2C%20Europe%29.zip
- Pokemon Diamond (NDS) (USA): Minerva No-Intro .../Pokemon%20-%20Diamond%20Version%20(USA)%20(Rev%205).zip | IA https://archive.org/download/pkmn_collection/pkmn%20collection/NDS/Pokemon%20-%20Diamond%20Version%20%28USA%29%20%28Rev%205%29.zip
- Pokemon Pearl (NDS) (USA): Minerva .../Pokemon%20-%20Pearl%20Version%20(USA)%20(Rev%205).zip | IA .../Pokemon%20-%20Pearl%20Version%20%28USA%29%20%28Rev%205%29.zip
- Pokemon Platinum (NDS) (USA): Minerva .../Pokemon%20-%20Platinum%20Version%20(USA).zip | IA https://archive.org/download/pkmn_collection/pkmn%20collection/NDS/Pokemon%20-%20Platinum%20Version%20%28USA%29.zip
- Pokemon HeartGold (NDS) (USA): Minerva .../Pokemon%20-%20HeartGold%20Version%20(USA).zip | IA https://archive.org/download/pkmn_collection/pkmn%20collection/NDS/Pokemon%20-%20HeartGold%20Version%20%28USA%29.zip
- Pokemon SoulSilver (NDS) (USA): Minerva .../Pokemon%20-%20SoulSilver%20Version%20(USA,%20Australia).zip | IA .../Pokemon%20-%20SoulSilver%20Version%20%28USA%29.zip
- Pokemon Black (NDS) (USA): Minerva .../Pokemon%20-%20Black%20Version%20(USA,%20Europe)%20(NDSi%20Enhanced).zip | IA https://archive.org/download/pkmn_collection/pkmn%20collection/NDS/Pokemon%20-%20Black%20Version%20%28USA%2C%20Europe%29%20%28NDSi%20Enhanced%29.zip
- Pokemon White (NDS) (USA): Minerva .../Pokemon%20-%20White%20Version%20(USA,%20Europe)%20(NDSi%20Enhanced).zip | IA .../Pokemon%20-%20White%20Version%20%28USA%2C%20Europe%29%20%28NDSi%20Enhanced%29.zip
- Pokemon Black 2 (NDS) (USA): Minerva .../Pokemon%20-%20Black%20Version%202%20(USA,%20Europe)%20(NDSi%20Enhanced).zip | IA https://archive.org/download/pkmn_collection/pkmn%20collection/NDS/Pokemon%20-%20Black%20Version%202%20%28USA%2C%20Europe%29%20%28NDSi%20Enhanced%29.zip
- Pokemon White 2 (NDS) (USA): Minerva .../Pokemon%20-%20White%20Version%202%20(USA,%20Europe)%20(NDSi%20Enhanced).zip | IA .../Pokemon%20-%20White%20Version%202%20%28USA%2C%20Europe%29%20%28NDSi%20Enhanced%29.zip
- Pokemon X (3DS) (USA): Minerva 3DS .../Pokemon%20X%20(USA)%20(En,Ja,Fr,De,Es,It,Ko).zip / CIA .../Pokemon%20X%20(World)%20(En,Ja,Fr,De,Es,It,Ko)%20(Legit%20CIA).zip | IA 3DS https://archive.org/download/3DS-Redump-2024-Individual-Games-Part1/Pokemon%20X%20%28USA%29%20%28En%2CJa%2CFr%2CDe%2CEs%2CIt%2CKo%29.zip
- Pokemon Y (3DS) (USA): Minerva 3DS .../Pokemon%20Y%20(USA)%20(En,Ja,Fr,De,Es,It,Ko).zip / CIA .../Pokemon%20Y%20(World)%20(En,Ja,Fr,De,Es,It,Ko)%20(Legit%20CIA).zip | IA 3DS .../Pokemon%20Y%20%28USA%29%20%28En%2CJa%2CFr%2CDe%2CEs%2CIt%2CKo%29.zip
- Pokemon Omega Ruby (3DS) (USA): Minerva 3DS .../Pokemon%20Omega%20Ruby%20(USA)%20(En,Ja,Fr,De,Es,It,Ko)%20(Rev%202).zip / CIA .../Pokemon%20-%20Omega%20Ruby%20(World)%20(En,Ja,Fr,De,Es,It,Ko)%20(Legit%20CIA).zip | IA 3DS https://archive.org/download/3DS-Redump-2024-Individual-Games-Part1/Pokemon%20Omega%20Ruby%20%28USA%29%20%28En%2CJa%2CFr%2CDe%2CEs%2CIt%2CKo%29%20%28Rev%202%29.zip
- Pokemon Alpha Sapphire (3DS) (USA): Minerva 3DS .../Pokemon%20Alpha%20Sapphire%20(USA)%20(En,Ja,Fr,De,Es,It,Ko)%20(Rev%202).zip / CIA .../Pokemon%20-%20Alpha%20Sapphire%20(World)%20(En,Ja,Fr,De,Es,It,Ko)%20(Legit%20CIA).zip | IA 3DS .../Pokemon%20Alpha%20Sapphire%20%28USA%29%20%28En%2CJa%2CFr%2CDe%2CEs%2CIt%2CKo%29%20%28Rev%202%29.zip
- Pokemon Sun (3DS) (USA): Minerva 3DS .../Pokemon%20Sun%20(USA)%20(En,Ja,Fr,De,Es,It,Zh,Ko).zip / CIA .../Pokemon%20Sun%20%28USA%29%20%28En%2CJa%2CFr%2CDe%2CEs%2CIt%2CZh%2CKo%29%20%28CIA%29.7z | IA 3DS https://archive.org/download/3DS-Redump-2024-Individual-Games-Part1/Pokemon%20Sun%20%28USA%29%20%28En%2CJa%2CFr%2CDe%2CEs%2CIt%2CZh%2CKo%29.zip
- Pokemon Moon (3DS) (USA): Minerva 3DS .../Pokemon%20Moon%20(USA)%20(En,Ja,Fr,De,Es,It,Zh,Ko).zip / CIA .../Pokemon%20Moon%20%28USA%29%20%28En%2CJa%2CFr%2CDe%2CEs%2CIt%2CZh%2CKo%29%20%28CIA%29.7z | IA 3DS .../Pokemon%20Moon%20%28USA%29%20%28En%2CJa%2CFr%2CDe%2CEs%2CIt%2CZh%2CKo%29.zip
- Pokemon Ultra Sun (3DS) (USA): Minerva 3DS .../Pokemon%20Ultra%20Sun%20(USA)%20(En,Ja,Fr,De,Es,It,Zh,Ko).zip / CIA .../Pokemon%20Ultra%20Sun%20%28USA%29%20%28En%2CJa%2CFr%2CDe%2CEs%2CIt%2CZh%2CKo%29%20%28CIA%29.7z | IA 3DS .../Pokemon%20Ultra%20Sun%20%28USA%29%20%28En%2CJa%2CFr%2CDe%2CEs%2CIt%2CZh%2CKo%29.zip
- Pokemon Ultra Moon (3DS) (USA): Minerva 3DS .../Pokemon%20Ultra%20Moon%20(USA)%20(En,Ja,Fr,De,Es,It,Zh,Ko).zip / CIA .../Pokemon%20Ultra%20Moon%20%28USA%29%20%28En%2CJa%2CFr%2CDe%2CEs%2CIt%2CZh%2CKo%29%20%28CIA%29.7z | IA 3DS .../Pokemon%20Ultra%20Moon%20%28USA%29%20%28En%2CJa%2CFr%2CDe%2CEs%2CIt%2CZh%2CKo%29.zip

### /Populars/super-smash-bros — Super Smash Bros
- Super Smash Bros Brawl (Wii) (USA): Minerva Redump NKit RVZ .../Super%20Smash%20Bros.%20Brawl%20(USA)%20(Rev%202).zip | IA https://archive.org/download/Wii-Redump-2024-Individual-Games-Part6/Super%20Smash%20Bros.%20Brawl%20%28USA%29%20%28Rev%202%29.zip
- Super Smash Bros Melee (GC) (USA): Minerva .../Super%20Smash%20Bros.%20Melee%20(USA)%20(En,Ja)%20(Rev%202).zip | IA https://archive.org/download/GameCube-Redump-2024-Individual-Games-Part2/Super%20Smash%20Bros.%20Melee%20%28USA%29%20%28En%2CJa%29%20%28Rev%202%29.zip
- Super Smash Bros for Nintendo 3DS (3DS) (USA): IA https://archive.org/download/3DS-Redump-2024-Individual-Games-Part1/Super%20Smash%20Bros.%20for%20Nintendo%203DS%20%28USA%29%20%28En%2CFr%2CEs%29%20%28Rev%207%29.zip
- Super Smash Bros for Wii U (Wii U) (USA): Minerva Game https://minerva-archive.org/browse/No-Intro/Nintendo%20-%20Wii%20U%20(Digital)%20(CDN)/Super%20Smash%20Bros.%20for%20Wii%20U%20(USA)%20(En,Fr,Es).zip / Update ...(Update).zip / DLC ...(v96)%20(DLC).zip | IA Game https://archive.org/download/wii-u-retail-nus-usa/Super%20Smash%20Bros.%20for%20Wii%20U%20%5B0005000010144F00%5D.7z / Update ...[UPDATE%20v304%5D.7z / DLC ...[DLC%5D.7z

### /Populars/xenoblade — Xenoblade
- Xenoblade Chronicles (Wii) (USA): Minerva Redump NKit RVZ .../Xenoblade%20Chronicles%20%28USA%2C%20Asia%29%20%28En%2CFr%2CEs%29.zip | IA https://archive.org/download/Wii-Redump-2024-Individual-Games-Part6/Xenoblade%20Chronicles%20%28USA%2C%20Asia%29%20%28En%2CFr%2CEs%29.zip
- Xenoblade Chronicles X (Wii U) (USA): Minerva Game https://minerva-archive.org/browse/No-Intro/Nintendo%20-%20Wii%20U%20(Digital)%20(CDN)/Xenoblade%20Chronicles%20X%20(USA)%20(En,Fr,Es).zip / Update ...(Update).zip / DLC ...(v0)%20(DLC).zip | IA Game https://archive.org/download/wii-u-retail-nus-usa/Xenoblade%20Chronicles%20X%20%5B00050000101C4D00%5D.7z / Update ...[UPDATE%20v48%5D.7z / DLC ...[DLC%5D.7z

---

## Nintendo

### /Nintendo/nintendo-games — Nintendo Games
Older systems are in /Retro & Arcade/retro-games.

Nintendo FDS Downloads:
- Nintendo - Family Computer Disk System (FDS): Minerva No-Intro https://minerva-archive.org/browse/No-Intro/Nintendo%20-%20Family%20Computer%20Disk%20System%20(FDS)/
- Nintendo - Family Computer Disk System (QD): Minerva No-Intro ...(QD)/

Nintendo NES Downloads:
- Nintendo - Nintendo Entertainment System (Headered): Minerva No-Intro https://minerva-archive.org/browse/No-Intro/Nintendo%20-%20Nintendo%20Entertainment%20System%20(Headered)/
- Nintendo - Nintendo Entertainment System (Headerless): Minerva No-Intro ...(Headerless)/
- Nintendo - NES Collection: IA https://archive.org/details/NES_Test_Collection_3

Nintendo SNES Downloads:
- Nintendo - Super Nintendo Entertainment System: Minerva No-Intro https://minerva-archive.org/browse/No-Intro/Nintendo%20-%20Super%20Nintendo%20Entertainment%20System/ | IA https://archive.org/details/No-Intro_SNES_Collection

Nintendo 64 Downloads:
- Nintendo - Nintendo 64 (BigEndian): Minerva No-Intro https://minerva-archive.org/browse/No-Intro/Nintendo%20-%20Nintendo%2064%20(BigEndian)/
- Nintendo - Nintendo 64 (ByteSwapped): Minerva No-Intro ...(ByteSwapped)/
- Nintendo - Nintendo 64DD: Minerva No-Intro https://minerva-archive.org/browse/No-Intro/Nintendo%20-%20Nintendo%2064DD/
- Nintendo - N64 Collection: IA https://archive.org/details/No-Intro_N64_Collection

Nintendo Gameboy & Gameboy Color Downloads:
- Nintendo - Game Boy Color: Minerva No-Intro https://minerva-archive.org/browse/No-Intro/Nintendo%20-%20Game%20Boy%20Color/ | IA https://archive.org/details/No-Intro_GameBoy_Color_Collection
- Nintendo - Game Boy: Minerva No-Intro https://minerva-archive.org/browse/No-Intro/Nintendo%20-%20Game%20Boy/ | IA https://archive.org/details/No-Intro_GameBoy_Collection

Nintendo Gameboy Advance Downloads:
- Nintendo - Game Boy Advance: Minerva No-Intro https://minerva-archive.org/browse/No-Intro/Nintendo%20-%20Game%20Boy%20Advance/
- Nintendo - Game Boy Advance (Multiboot): Minerva No-Intro ...(Multiboot)/
- Nintendo - Game Boy Advance (Video): Minerva No-Intro ...(Video)/
- Nintendo - Game Boy Advance (e-Reader): Minerva No-Intro ...(e-Reader)/
- Nintendo - Game Boy Advance Collection: IA https://archive.org/details/No-Intro_GameBoy_Advance_Collection

Nintendo Pokemon Mini Downloads:
- Nintendo - Pokemon Mini: Minerva No-Intro https://minerva-archive.org/browse/No-Intro/Nintendo%20-%20Pokemon%20Mini/

Nintendo Virtual Boy Downloads:
- Nintendo - Virtual Boy: Minerva No-Intro https://minerva-archive.org/browse/No-Intro/Nintendo%20-%20Virtual%20Boy/

### /Nintendo/nintendo-ds — Nintendo DS
- Nintendo - Nintendo DS (Decrypted): Minerva No-Intro https://minerva-archive.org/browse/No-Intro/Nintendo%20-%20Nintendo%20DS%20(Decrypted)/
- Nintendo - Nintendo DS (Encrypted): Minerva No-Intro ...(Encrypted)/
- Nintendo - Nintendo DS (Download Play): Minerva No-Intro ...(Download%20Play)/
- Nintendo - Nintendo DSi (Decrypted): Minerva No-Intro https://minerva-archive.org/browse/No-Intro/Nintendo%20-%20Nintendo%20DSi%20(Decrypted)/
- Nintendo - Nintendo DSi (Encrypted): Minerva No-Intro ...(Encrypted)/
- Nintendo - Nintendo DSi (Digital): Minerva No-Intro ...(Digital)/
- DSiWare: IA https://archive.org/download/MarioCubeLite/DSiWare/ | Open Directory https://repo.mariocube.com/DSiWare/
- No-Intro Nintendo DS (Download Play) (2022-07-07): IA https://archive.org/download/No-Intro-nintendo-nintendo-ds-download-play_202207
- Nintendo DS Anti-Piracy Fixed ROMs: Minerva https://minerva-archive.org/browse/Internet%20Archive/chadmaster/nds_apfix/apfix/ | IA https://archive.org/download/nds_apfix/apfix/
- DS No-Intro 2024: IA https://archive.org/details/DS-No-Intro-2024-Myrient-Zipped
- DSi No-Intro 2024: IA https://archive.org/details/DSi-No-Intro-2024-Myrient-Zipped-2

### /Nintendo/nintendo-3ds — Nintendo 3DS
- 3DS Content in CIA Format: hShop https://hshop.erista.me/
- Nintendo - Nintendo 3DS (Decrypted): Minerva No-Intro https://minerva-archive.org/browse/No-Intro/Nintendo%20-%20Nintendo%203DS%20(Decrypted)/
- Nintendo - Nintendo 3DS (Encrypted): Minerva No-Intro ...(Encrypted)/
- Nintendo - New Nintendo 3DS (Decrypted): Minerva No-Intro https://minerva-archive.org/browse/No-Intro/Nintendo%20-%20New%20Nintendo%203DS%20(Decrypted)/
- Nintendo - New Nintendo 3DS (Encrypted): Minerva No-Intro ...(Encrypted)/
- Nintendo - Nintendo 3DS (Digital) (Deprecated): Minerva No-Intro ...(Digital)%20(Deprecated)/
- Nintendo - New Nintendo 3DS (Digital) (Deprecated): Minerva No-Intro ...(Digital)%20(Deprecated)/
- Unofficial - Nintendo - Nintendo 3DS (Digital) (Updates and DLC) (Decrypted): Minerva No-Intro ...(Updates%20and%20DLC)%20(Decrypted)/
- Unofficial - Nintendo - Nintendo 3DS (Digital) (Updates and DLC) (Encrypted): Minerva No-Intro ...(Updates%20and%20DLC)%20(Encrypted)/
- Nintendo - Nintendo 3DS (Digital) (CDN): Minerva No-Intro ...(Digital)%20(CDN)/
- Nintendo - Nintendo 3DS (Digital) (Dev ROMs): Minerva No-Intro ...(Dev%20ROMs)/
- Nintendo - Nintendo 3DS (Digital) (Pre-Install): Minerva No-Intro ...(Pre-Install)/
- 3DS-Main - Encrypted (Part 1) (#-R): IA https://archive.org/download/3ds-main-encrypted
- 3DS-Main - Encrypted (Part 2) (S-Z): IA https://archive.org/download/3ds-main-encrypted-p2
- 3DS No-Intro 2024 Individual Games Part 1: IA https://archive.org/details/3DS-Redump-2024-Individual-Games-Part1
- 3DS No-Intro 2024 Individual Games Part 2: IA https://archive.org/details/3DS-Redump-2024-Individual-Games-Part2
- N3DS No-Intro Collection 2024: IA https://archive.org/details/xenoblade-chronicles-3-d-europe-en-fr-de-es-it

### /Nintendo/nintendo-gamecube — Nintendo GameCube
RVZ format recommended for Dolphin; convert to ISO for real hardware with Dolphin.

RVZ Downloads:
- Nintendo - GameCube - NKit RVZ [zstd-19-128k]: Minerva Redump https://minerva-archive.org/browse/Redump/Nintendo%20-%20GameCube%20-%20NKit%20RVZ%20[zstd-19-128k]/
- RVZ - Nintendo GameCube (Redump) - USA Set: IA https://archive.org/download/rvz-gc-usa-redump/RVZ-GC-USA-REDUMP/
- RVZ - Nintendo GameCube (Redump) - Europe Set: IA https://archive.org/download/rvz-gc-europe-redump/RVZ-GC-EUROPE-REDUMP/
- RVZ - Nintendo GameCube (Redump) - Asia Set: IA https://archive.org/download/rvz-gc-asia-redump/RVZ-GC-ASIA-REDUMP/

Redump Downloads:
- Redump - Nintendo - GameCube (America) (20160527): Minerva Parts 1/2/3 https://minerva-archive.org/browse/Internet%20Archive/Unknown/RedumpNintendoGameCubeAmerica/ / ...Part2/ / ...Part3/
- Redump - Nintendo - GameCube (Japan): Minerva https://minerva-archive.org/browse/Internet%20Archive/pixelspoil/NCubeJ/ | IA https://archive.org/download/NCubeJ
- Redump - Nintendo - GameCube (Europe): Minerva https://minerva-archive.org/browse/Internet%20Archive/kodi_amp_spmc_canada/EuropeanGamecubeCollectionByGhostware/
- Redump - Nintendo - GameCube (Australia): Minerva https://minerva-archive.org/browse/Internet%20Archive/kodi_amp_spmc_canada/AustraliaGamecubeCollectionByGhostware/
- Redump - Nintendo - GameCube (Asia): Minerva https://minerva-archive.org/browse/Internet%20Archive/kodi_amp_spmc_canada/AsiaGamecubeCollectionByGhostware/ | IA https://archive.org/download/AsiaGamecubeCollectionByGhostware
- GameCube Redump 2024 Individual Games: IA Part 1 https://archive.org/details/GameCube-Redump-2024-Individual-Games-Part1 / Part 2 https://archive.org/details/GameCube-Redump-2024-Individual-Games-Part2

### /Nintendo/nintendo-wii — Nintendo Wii
- Nintendo - Wii - NKit RVZ [zstd-19-128k]: Minerva Redump https://minerva-archive.org/browse/Redump/Nintendo%20-%20Wii%20-%20NKit%20RVZ%20%5Bzstd-19-128k%5D/
- Wii Rom Set By Ghostware Part 1: Minerva https://minerva-archive.org/browse/Internet%20Archive/kodi_amp_spmc_canada/WiiRomSetByGhostware/
- Wii Rom Set By Ghostware Part 2: Minerva .../WiiRomSetByGhostwarePart2/
- Wii Rom Set By Ghostware Part 3: Minerva .../WiiRomSetByGhostwarePart3/
- WiiWare, VC, DLC, Channels & IOS: IA https://repo.mariocube.com/WADs/_WiiWare,%20VC,%20DLC,%20Channels%20&%20IOS/ | Open Directory https://archive.org/download/MarioCubeLite/WADs/_WiiWare%2C%20VC%2C%20DLC%2C%20Channels%20%26%20IOS/
- NKit Fully Loaded: Minerva https://minerva-archive.org/browse/Internet%20Archive/bingbong294/NKitFullyLoaded2020429/ | IA https://archive.org/download/NKitFullyLoaded2020429/NKit%202020.4.29
- Wii Redump 2024 Individual Games: IA Part 1 https://archive.org/details/Wii-Redump-2024-Individual-Games-Part1 / Part 2 ...Part2 / Part 3 ...Part3 / Part 4 ...Part4 / Part 5 ...Part5 / Part 6 ...Part6

### /Nintendo/nintendo-wii-u — Nintendo Wii U
Tools: WiiUDownloader (https://github.com/Xpl0itU/WiiUDownloader/releases/latest); Wii U USB Helper guide https://wiki.agilly1989.xyz/books/wiiu/page/usbhelper-usbhelperlauncher; CDecrypt (https://github.com/VitaSmith/cdecrypt/releases/latest); WUX→WUD video https://myrient.erista.me/assets/wux.mp4.

- Nintendo Wii U Disc (USA) Full Set WUA Format (Embedded DLC & Updates): Minerva https://minerva-archive.org/browse/Internet%20Archive/teamgt19/nintendo-wii-u-usa-full-set-wua-format-embedded-dlc-updates/
- Nintendo Wii U [eShop] (USA) Full Set WUA Format (Embedded DLC & Updates) + Virtual Console: Minerva https://minerva-archive.org/browse/Internet%20Archive/teamgt19/nintendo-wii-u-eshop-usa-full-set-wua-format-embedded-dlc-updates/
- Nintendo - Wii U (Digital) (CDN): Minerva No-Intro https://minerva-archive.org/browse/No-Intro/Nintendo%20-%20Wii%20U%20(Digital)%20(CDN)/
- Wii U: Retail NUS [USA]: Minerva https://minerva-archive.org/browse/Internet%20Archive/archiver_2020/wii-u-retail-nus-usa/ | IA https://archive.org/download/wii-u-retail-nus-usa
- Wii U: Download NUS [USA]: Minerva https://minerva-archive.org/browse/Internet%20Archive/archiver_2020/wii-u-download-nus-usa/
- Wii U: TurboGrafx-16 NUS: Minerva https://minerva-archive.org/browse/Internet%20Archive/archiver_2020/wii-u-turbografx16-nus/ | IA https://archive.org/download/wii-u-turbografx16-nus
- Wii U: Wii NUS: Minerva https://minerva-archive.org/browse/Internet%20Archive/archiver_2020/wii-u-wii-nus/ | IA https://archive.org/download/wii-u-wii-nus
- Wii U: Nintendo 64 NUS: Minerva https://minerva-archive.org/browse/Internet%20Archive/archiver_2020/wii-u-nintendo-64-nus/ | IA https://archive.org/download/wii-u-nintendo-64-nus
- Wii U: NES & Famicom NUS: Minerva https://minerva-archive.org/browse/Internet%20Archive/archiver_2020/wii-u-nes-fc-nus/ | IA https://archive.org/download/wii-u-nes-fc-nus
- Wii U: Super Nintendo NUS: Minerva https://minerva-archive.org/browse/Internet%20Archive/archiver_2020/wii-u-super-nintendo-snes-nus/ | IA https://archive.org/download/wii-u-super-nintendo-snes-nus
- Wii U: Nintendo DS NUS: Minerva https://minerva-archive.org/browse/Internet%20Archive/archiver_2020/wii-u-nintendo-ds-nds-nus/ | IA https://archive.org/download/wii-u-nintendo-ds-nds-nus
- Wii U: Gameboy Advance NUS: Minerva https://minerva-archive.org/browse/Internet%20Archive/archiver_2020/wii-u-gameboy-advance-nus/ | IA https://archive.org/download/wii-u-gameboy-advance-nus
- Wii U: Retail Game Disc NUS: Minerva https://minerva-archive.org/browse/Internet%20Archive/archiver_2020/wii-u-retail-game-disc-nus-usa/ | IA https://archive.org/download/wii-u-retail-game-disc-nus-usa
- Nintendo - Wii U - WUX: Minerva Redump https://minerva-archive.org/browse/Redump/Nintendo%20-%20Wii%20U%20-%20WUX/

---

## PC

### /PC/pc-games — PC Games
- Total DOS Collection Release 16 March 2019: Minerva https://minerva-archive.org/browse/Internet%20Archive/sketch_the_cow/Total_DOS_Collection_Release_16_March_2019/ | IA https://archive.org/download/Total_DOS_Collection_Release_16_March_2019
- ExoDos: https://www.retro-exo.com/exodos.html
- eXoWin3 2.0: https://www.retro-exo.com/win3x.html
- DOOM WADs: Minerva https://minerva-archive.org/browse/Internet%20Archive/chadmaster/2020_03_22_DOOM/DOOM%20WADs/ | IA https://archive.org/download/2020_03_22_DOOM/DOOM%20WADs/
- Apple - Macintosh: Minerva Redump https://minerva-archive.org/browse/Redump/Apple%20-%20Macintosh/ | IA https://archive.org/download/apple_macintosh
- IBM - PC compatible: Minerva Redump https://minerva-archive.org/browse/Redump/IBM%20-%20PC%20compatible/
- Redump PC-Compatible Assembly: 0-9 IA https://archive.org/download/redump_pc_0
- Redump PC-Compatible Assembly: A IA https://archive.org/download/redump_pc_A
- Redump PC-Compatible Assembly: B (Part 1) IA https://archive.org/download/redump_pc_B
- Redump PC-Compatible Assembly: B (Part 2) IA https://archive.org/download/redump_pc_B-2
- Redump PC-Compatible Assembly: C (Part 1) IA https://archive.org/download/redump_pc_C
- Redump PC-Compatible Assembly: C (Part 2) IA https://archive.org/download/redump_pc_C-2
- Redump PC-Compatible Assembly: C (Part 3) IA https://archive.org/download/redump_pc_C-3
- Redump PC-Compatible Assembly: C (Part 4) IA https://archive.org/download/redump_pc_C-4
- Redump PC-Compatible Assembly: D (Part 1) IA https://archive.org/download/redump_pc_D
- Redump PC-Compatible Assembly: D (Part 2) IA https://archive.org/download/redump_pc_D-2
- Redump PC-Compatible Assembly: E IA https://archive.org/download/redump_pc_E
- Redump PC-Compatible Assembly: F IA https://archive.org/download/redump_pc_F
- Redump PC-Compatible Assembly: G (Part 1) IA https://archive.org/download/redump_pc_G
- Redump PC-Compatible Assembly: G (Part 2) IA https://archive.org/download/redump_pc_G-2
- Redump PC-Compatible Assembly: G (Part 3) IA https://archive.org/download/redump_pc_G-3
- Redump PC-Compatible Assembly: H IA https://archive.org/download/redump_pc_H
- Redump PC-Compatible Assembly: I IA https://archive.org/download/redump_pc_I
- Redump PC-Compatible Assembly: J IA https://archive.org/download/redump_pc_J
- Redump PC-Compatible Assembly: K IA https://archive.org/download/redump_pc_K
- Redump PC-Compatible Assembly: L IA https://archive.org/download/redump_pc_L
- Redump PC-Compatible Assembly: M (Part 1) IA https://archive.org/download/redump_pc_M
- Redump PC-Compatible Assembly: M (Part 2) IA https://archive.org/download/redump_pc_M-2
- Redump PC-Compatible Assembly: N IA https://archive.org/download/redump_pc_N
- Redump PC-Compatible Assembly: O IA https://archive.org/download/redump_pc_O
- Redump PC-Compatible Assembly: P (Part 1) IA https://archive.org/download/redump_pc_P
- Redump PC-Compatible Assembly: P (Part 2) IA https://archive.org/download/redump_pc_P-2
- Redump PC-Compatible Assembly: P (Part 3) IA https://archive.org/download/redump_pc_P-3
- Redump PC-Compatible Assembly: Q IA https://archive.org/download/redump_pc_Q
- Redump PC-Compatible Assembly: R IA https://archive.org/download/redump_pc_R
- Redump PC-Compatible Assembly: S (Part 1) IA https://archive.org/download/redump_pc_S
- Redump PC-Compatible Assembly: S (Part 2) IA https://archive.org/download/redump_pc_S-2
- Redump PC-Compatible Assembly: S (Part 3) IA https://archive.org/download/redump_pc_S-3
- Redump PC-Compatible Assembly: T (Part 1) IA https://archive.org/download/redump_pc_T
- Redump PC-Compatible Assembly: T (Part 2) IA https://archive.org/download/redump_pc_T-2
- Redump PC-Compatible Assembly: U IA https://archive.org/download/redump_pc_U
- Redump PC-Compatible Assembly: V IA https://archive.org/download/redump_pc_V
- Redump PC-Compatible Assembly: W IA https://archive.org/download/redump_pc_W
- Redump PC-Compatible Assembly: X IA https://archive.org/download/redump_pc_X
- Redump PC-Compatible Assembly: Y IA https://archive.org/download/redump_pc_Y
- Redump PC-Compatible Assembly: Z IA https://archive.org/download/redump_pc_Z

1990s to early 2000s:
- Internet Archive: https://archive.org/
- MyAbandonware: https://www.myabandonware.com/
- VetusWare: https://vetusware.com/
- Ovagames: http://www.ovagames.com/

---

## Miscellaneous

### /Miscellaneous/rom-sets — ROM Sets
- No-Intro - ROM Sets: IA https://archive.org/download/ni-roms/roms/
- The Unofficial Redump Hoard: IA https://archive.org/details/redump
- CVLT OF MIRRORS: IA https://archive.org/details/@cvlt_of_mirrors
- TOSEC: IA https://archive.org/download/tosec-main
- [TOSEC-ISO] 3DO: IA https://archive.org/download/tosec-iso-3do
- [TOSEC-ISO] Acorn: IA https://archive.org/download/tosec-iso-acorn
- [TOSEC-ISO] American Laser Games: IA https://archive.org/download/tosec-iso-american-laser-games
- [TOSEC-ISO] Apple: IA https://archive.org/download/tosec-iso-apple
- [TOSEC-ISO] Atari: IA https://archive.org/download/tosec-iso-atari
- [TOSEC-ISO] Bandai: IA https://archive.org/download/tosec-iso-bandai
- [TOSEC-ISO] Capcom: IA https://archive.org/download/tosec-iso-capcom
- [TOSEC-ISO] Commodore: IA https://archive.org/download/tosec-iso-commodore
- [TOSEC-ISO] Fujitsu: IA https://archive.org/download/tosec-iso-fujitsu
- [TOSEC-ISO] IBM: IA https://archive.org/download/tosec-iso-ibm
- [TOSEC-ISO] Incredible Technologies: IA https://archive.org/download/tosec-iso-incredible-technologies
- [TOSEC-ISO] Konami: IA https://archive.org/download/tosec-iso-konami
- [TOSEC-ISO] Mattel: IA https://archive.org/download/tosec-iso-mattel
- [TOSEC-ISO] Memorex: IA https://archive.org/download/tosec-iso-memorex
- [TOSEC-ISO] Microsoft: IA https://archive.org/download/tosec-iso-microsoft
- [TOSEC-ISO] Multi-format: IA https://archive.org/download/tosec-iso-multi-format
- [TOSEC-ISO] Namco-Sega-Nintendo: IA https://archive.org/download/tosec-iso-namco-sega-nintendo
- [TOSEC-ISO] NEC: IA https://archive.org/download/tosec-iso-nec
- [TOSEC-ISO] Nintendo: IA https://archive.org/download/tosec-iso-nintendo_
- [TOSEC-ISO] Philips: IA https://archive.org/download/tosec-iso-philips
- [TOSEC-ISO] Sega Part 1: IA https://archive.org/download/tosec-iso-sega
- [TOSEC-ISO] Sega Part 2: IA https://archive.org/download/tosec-iso-sega-part2
- [TOSEC-ISO] Sinclair: IA https://archive.org/download/tosec-iso-sinclair
- [TOSEC-ISO] SNK: IA https://archive.org/download/tosec-iso-snk
- [TOSEC-ISO] Sony: IA https://archive.org/download/tosec-iso-sony
- [TOSEC-ISO] Tomy: IA https://archive.org/download/tosec-iso-tomy
- [TOSEC-ISO] VM Labs: IA https://archive.org/download/tosec-iso-vm-labs
- [TOSEC-ISO] VTech: IA https://archive.org/download/tosec-iso-vtech
- [TOSEC-ISO] ZAPiT Games: IA https://archive.org/download/tosec-iso-zapit-games
- Hardware Target Game Database (HTGDB) Gamepacks: IA https://archive.org/download/htgdb-gamepacks
- English Translation ROMs Collection: IA https://archive.org/download/En-ROMs/En-ROMs/
- Super Mario World Hacks: IA https://archive.org/download/super-mario-world-hacks
- Super Famicom - Enhanced Colors: IA https://archive.org/download/super-famicom-enhanced-colors/ROMs/
- Nintendo - Super Famicom - Speed Hacks: IA https://archive.org/download/sfc-speedhacks/ROMs/
- Complete Sega MD+ Collection (MegaSD, Mega Everdrive Pro & Genesis Plus GX Compatible): IA https://archive.org/download/mdplus_collection_22_04_16
- Sega Model 3 ROMs: IA https://archive.org/download/segamodel3/ROMs/

### /Miscellaneous/bios-sets — BIOS Sets
- RetroBIOS: https://abdess.github.io/retrobios/ | GitHub https://github.com/Abdess/retrobios
- Redump BIOS sets: IA https://archive.org/download/2019_11_25_redump_bios
- TOSEC Firmware and Operating Systems Collection: IA https://archive.org/download/tosec_fw_os
- Retroarch System Files (BIOS/Firmwares/OS): IA https://archive.org/download/RetroarchSystemFiles/Retroarch-System/
- Firmwares: MEGA https://mega.nz/folder/9ZdQwaaY#u63KaI0MsKcIqWE2GQmUuA

### /Miscellaneous/other — Other
- No-Intro - Source Code Sets: IA https://archive.org/download/ni-sc/ni-sc/
- [TOSEC-PIX] Part 1: IA https://archive.org/download/tosec-pix
- [TOSEC-PIX] Part 2: IA https://archive.org/download/tosec-pix-part2

---

## Retro & Arcade

### /Retro & Arcade/retro-games — Retro Games
- Atari - 2600: Minerva No-Intro https://minerva-archive.org/browse/No-Intro/Atari%20-%202600/ | IA https://archive.org/download/ni-roms/roms/Atari%20-%202600.zip/ / https://archive.org/download/nointro.atari-2600
- Atari - 5200: Minerva No-Intro https://minerva-archive.org/browse/No-Intro/Atari%20-%205200/ | IA https://archive.org/download/ni-roms/roms/Atari%20-%202600.zip/ / https://archive.org/download/nointro.atari-5200
- Atari - 7800: Minerva No-Intro https://minerva-archive.org/browse/No-Intro/Atari%20-%207800/ | IA Download 1 https://archive.org/download/ni-roms/roms/Atari%20-%207800.zip/ / Download 2 https://archive.org/download/nointro.atari-7800
- NEC - PC Engine - TurboGrafx 16: Minerva No-Intro https://minerva-archive.org/browse/No-Intro/NEC%20-%20PC%20Engine%20-%20TurboGrafx-16/ | IA Download 1 https://archive.org/download/ni-roms/roms/NEC%20-%20PC%20Engine%20-%20TurboGrafx-16.zip/ / Download 2 https://archive.org/download/nointro.tg-16
- Atari - Jaguar CD Interactive Multimedia System: Minerva Redump https://minerva-archive.org/browse/Redump/Atari%20-%20Jaguar%20CD%20Interactive%20Multimedia%20System/ | IA https://archive.org/download/atari_jaguar-cd
- Bandai - Pippin: Minerva Redump https://minerva-archive.org/browse/Redump/Bandai%20-%20Pippin/ | IA https://archive.org/download/bandai_pippin
- Fujitsu - FM-Towns: Minerva Redump https://minerva-archive.org/browse/Redump/Fujitsu%20-%20FM-Towns/ | IA https://archive.org/download/fujitsu_fm_towns_series
- NEC - PC Engine CD & TurboGrafx CD: Minerva Redump https://minerva-archive.org/browse/Redump/NEC%20-%20PC%20Engine%20CD%20&%20TurboGrafx%20CD/ | IA https://archive.org/download/nec_pc-engine-cd_turbografx-cd
- NEC - PC-FX & PC-FXGA: Minerva Redump https://minerva-archive.org/browse/Redump/NEC%20-%20PC-FX%20&%20PC-FXGA/ | IA https://archive.org/download/nec_pc-fxpc_fxga
- NEC - PC-98 series: Minerva Redump https://minerva-archive.org/browse/Redump/NEC%20-%20PC-98%20series/ | IA https://archive.org/download/nec_pc-98_series
- Panasonic - 3DO Interactive Multiplayer: Minerva Redump https://minerva-archive.org/browse/Redump/Panasonic%20-%203DO%20Interactive%20Multiplayer/ | IA https://archive.org/download/panasonic_3do_interactive_multiplayer
- Philips - CD-i: Minerva Redump https://minerva-archive.org/browse/Redump/Philips%20-%20CD-i/ | IA https://archive.org/download/philips_cd-i
- SNK - Neo Geo CD: Minerva Redump https://minerva-archive.org/browse/Redump/SNK%20-%20Neo%20Geo%20CD/ | IA https://archive.org/download/snk_neo_geo
- Atari Jaguar: Minerva https://minerva-archive.org/browse/Internet%20Archive/chadmaster/jagcd-chd-zstd/jagcd-chd-zstd/ | IA https://archive.org/download/jagcd-chd-zstd/jagcd-chd-zstd/
- PC Engine CD - TurboGrafx CD: Minerva https://minerva-archive.org/browse/Internet%20Archive/chadmaster/pcecd-chd-zstd-redump/pcecd-chd-zstd/ | IA https://archive.org/download/pcecd-chd-zstd-redump
- Panasonic - 3DO Interactive Multiplayer: Minerva https://minerva-archive.org/browse/Internet%20Archive/chadmaster/3do-chd-zstd-redump/3do-chd-zstd/ | IA https://archive.org/download/3do-chd-zstd-redump/3do-chd-zstd/
- SNK - NeoGeo CD: Minerva https://minerva-archive.org/browse/Internet%20Archive/chadmaster/ngcd-chd-zstd-redump/ngcd-chd-zstd/ | IA https://archive.org/download/ngcd-chd-zstd-redump/ngcd-chd-zstd/

### /Retro & Arcade/arcade — Arcade
- Arcade - Konami - FireBeat: Minerva Redump https://minerva-archive.org/browse/Redump/Arcade%20-%20Konami%20-%20FireBeat/ | IA https://archive.org/download/konami_firebeat
- Arcade - Konami - M2: Minerva Redump https://minerva-archive.org/browse/Redump/Arcade%20-%20Konami%20-%20M2/ | IA https://archive.org/download/konami_m2
- Arcade - Konami - System 573: Minerva Redump https://minerva-archive.org/browse/Redump/Arcade%20-%20Konami%20-%20System%20573/ | IA https://archive.org/download/konami_system_573
- Arcade - Konami - System GV: Minerva Redump https://minerva-archive.org/browse/Redump/Arcade%20-%20Konami%20-%20System%20GV/ | IA https://archive.org/download/konami_system_gv
- Arcade - Konami - e-Amusement: Minerva Redump https://minerva-archive.org/browse/Redump/Arcade%20-%20Konami%20-%20e-Amusement/ | IA https://archive.org/download/konami_e-amusement
- Arcade - Namco - Sega - Nintendo - Triforce: Minerva Redump https://minerva-archive.org/browse/Redump/Arcade%20-%20Namco%20-%20Sega%20-%20Nintendo%20-%20Triforce/ | IA https://archive.org/download/namco_sega_nintendo_triforce
- Arcade - Namco - System 246: Minerva Redump https://minerva-archive.org/browse/Redump/Arcade%20-%20Namco%20-%20System%20246/ | IA https://archive.org/download/namco_system_246
- Arcade - Sega - Chihiro: Minerva Redump https://minerva-archive.org/browse/Redump/Arcade%20-%20Sega%20-%20Chihiro/ | IA https://archive.org/download/sega_chihiro
- Arcade - Sega - Lindbergh: Minerva Redump https://minerva-archive.org/browse/Redump/Arcade%20-%20Sega%20-%20Lindbergh/ | IA https://archive.org/download/sega_lindbergh
- Arcade - Sega - Naomi: Minerva Redump https://minerva-archive.org/browse/Redump/Arcade%20-%20Sega%20-%20Naomi/ | IA https://archive.org/download/sega_naomi
- Arcade - Sega - Naomi 2: Minerva Redump https://minerva-archive.org/browse/Redump/Arcade%20-%20Sega%20-%20Naomi%202/ | IA https://archive.org/download/sega_naomi_2
- Arcade - Sega - RingEdge: Minerva Redump https://minerva-archive.org/browse/Redump/Arcade%20-%20Sega%20-%20RingEdge/ | IA https://archive.org/download/sega_ringedge
- Arcade - Sega - RingEdge 2: Minerva Redump https://minerva-archive.org/browse/Redump/Arcade%20-%20Sega%20-%20RingEdge%202/ | IA https://archive.org/download/sega_ringedge_2
- MAME 0.266 Software List ROMs Merged: Minerva https://minerva-archive.org/browse/Internet%20Archive/chadmaster/mame-sl/mame-sl/ | IA https://archive.org/download/mame-sl/mame-sl/
- MAME 0.266 CHDs Merged: Minerva https://minerva-archive.org/browse/Internet%20Archive/lollo_220/MAME_0.225_CHDs_merged/ | IA https://archive.org/download/MAME_0.225_CHDs_merged
- MAME 0.265 ROMs Merged: Minerva https://minerva-archive.org/browse/Internet%20Archive/chadmaster/mame-merged/mame-merged/ | IA https://archive.org/download/mame-merged/mame-merged/
- MAME 0.265 BIOS Sets: Minerva https://minerva-archive.org/browse/Internet%20Archive/chadmaster/mame-merged/BIOS/ | IA https://archive.org/download/mame-merged/BIOS/
- HBMAME 0.244 ROMs Merged: Minerva https://minerva-archive.org/browse/Internet%20Archive/aberusugi/hbmame_0244_roms/ | IA https://archive.org/download/hbmame_0244_roms
- MAME 0.258 ROMs + CHDs + EXTRAs: Minerva https://minerva-archive.org/browse/Internet%20Archive/rompacker/mame-chds-roms-extras-complete/ | IA https://archive.org/download/mame-chds-roms-extras-complete
- MAME Support Files: Minerva https://minerva-archive.org/browse/Internet%20Archive/chadmaster/mame-support/Support/ | IA https://archive.org/download/mame-support/Support/
- FinalBurn Neo Nightly ROMs + Support (Updated Monthly): Minerva https://minerva-archive.org/browse/Internet%20Archive/chadmaster/2020_01_06_fbn/ | IA https://archive.org/download/2020_01_06_fbn/
- FinalBurn Neo 1.0.0.2 ROMs + Support: Minerva https://minerva-archive.org/browse/Internet%20Archive/chadmaster/fbneo/ | IA https://archive.org/download/fbneo/
- FinalBurn Neo Arcade ROM Set (Full Non-Merged): Minerva https://minerva-archive.org/browse/Internet%20Archive/chadmaster/fbnarcade-fullnonmerged/arcade/ | IA https://archive.org/download/fbnarcade-fullnonmerged/arcade/
- MAME ROM usage guide: https://archive.org/details/mame-chds-roms-extras-complete
- Other MAME sets via torrent: https://pleasuredome.github.io/pleasuredome/

---

## Sega

### /Sega/sega-games — SEGA Games
Older systems in /Retro & Arcade/retro-games.
- Sega - 32X: Minerva No-Intro https://minerva-archive.org/browse/No-Intro/Sega%20-%2032X/ | IA Download 1 https://archive.org/download/ni-roms/roms/Sega%20-%2032X.zip/ / Download 2 https://archive.org/download/nointro.32x
- Sega - Game Gear: Minerva No-Intro https://minerva-archive.org/browse/No-Intro/Sega%20-%20Game%20Gear/ | IA Download 1 https://archive.org/download/ni-roms/roms/Sega%20-%20Game%20Gear.zip/ / Download 2 https://archive.org/download/nointro.gg
- Sega - Master System - Mark III: Minerva No-Intro https://minerva-archive.org/browse/No-Intro/Sega%20-%20Master%20System%20-%20Mark%20III/ | IA Download 1 https://archive.org/download/ni-roms/roms/Sega%20-%20Master%20System%20-%20Mark%20III.zip/ / Download 2 https://archive.org/download/nointro.ms-mkiii
- Sega - Mega Drive - Genesis: Minerva No-Intro https://minerva-archive.org/browse/No-Intro/Sega%20-%20Mega%20Drive%20-%20Genesis/ | IA Download 1 https://archive.org/download/ni-roms/roms/Sega%20-%20Mega%20Drive%20-%20Genesis.zip/ / Download 2 https://archive.org/download/nointro.md

### /Sega/sega-dreamcast — Sega Dreamcast
GDI format recommended; not all emulators support BIN/CUE.
- Sega - Dreamcast (BIN/CUE): Minerva Redump https://minerva-archive.org/browse/Redump/Sega%20-%20Dreamcast/ | IA https://archive.org/download/sega_dreamcast
- Sega - Dreamcast (CHD): Minerva https://minerva-archive.org/browse/Internet%20Archive/chadmaster/dc-chd-zstd-redump/dc-chd-zstd/ | IA https://archive.org/download/dc-chd-zstd-redump/dc-chd-zstd/
- TOSEC Dreamcast USA GDI: IA https://archive.org/download/tosecdcus20190822
- TOSEC Dreamcast EUR GDI: IA https://archive.org/download/18wheeleramericanprotruckerv1.7002001segapalm4
- TOSEC Dreamcast JAP GDI: IA https://archive.org/download/interludev1.0032003necinterchanneljp
- Dreamcast Collection By Ghostware Multi-region: Minerva https://minerva-archive.org/browse/Internet%20Archive/kodi_amp_spmc_canada/DreamcastCollectionByGhostwareMulti-region/ | IA https://archive.org/download/DreamcastCollectionByGhostwareMulti-region
- Almost Complete Dreamcast GDI: Minerva https://minerva-archive.org/browse/Internet%20Archive/cmpltromsets/almstcmpltdrmcst/ | IA https://archive.org/download/almstcmpltdrmcst
- TiZ Homebrew Apps: MEGA https://mega.nz/#F!q7oxzDga!JfJulP8EX1-poB0nkgy2ZA

### /Sega/sega-saturn — Sega Saturn
- Sega - Saturn (BIN/CUE): Minerva Redump https://minerva-archive.org/browse/Redump/Sega%20-%20Saturn/ | IA https://archive.org/download/sega_saturn
- Sega - Saturn (CHD) USA: Minerva https://minerva-archive.org/browse/Internet%20Archive/chadmaster/chd_saturn/CHD-Saturn/USA/ | IA https://archive.org/download/chd_saturn/CHD-Saturn/USA/
- Sega - Saturn (CHD) EUR: Minerva https://minerva-archive.org/browse/Internet%20Archive/chadmaster/chd_saturn/CHD-Saturn/Europe/ | IA https://archive.org/download/chd_saturn/CHD-Saturn/Europe/
- Sega - Saturn (CHD) JPN: Minerva https://minerva-archive.org/browse/Internet%20Archive/chadmaster/chd_saturn/CHD-Saturn/Japan/ | IA https://archive.org/download/chd_saturn/CHD-Saturn/Japan/
- Sega - Saturn (CHD) Other: Minerva https://minerva-archive.org/browse/Internet%20Archive/chadmaster/chd_saturn/CHD-Saturn/Other-Regions/ | IA https://archive.org/download/chd_saturn/CHD-Saturn/Other-Regions/
- Sega - Saturn (CHD) Translations: Minerva https://minerva-archive.org/browse/Internet%20Archive/chadmaster/chd_saturn/CHD-Saturn/Translations/ | IA https://archive.org/download/chd_saturn/CHD-Saturn/Translations/
- Sega - Saturn (CHD) Improvements: Minerva https://minerva-archive.org/browse/Internet%20Archive/chadmaster/chd_saturn/CHD-Saturn/Improvements/ | IA https://archive.org/download/chd_saturn/CHD-Saturn/Improvements/

### /Sega/sega-cd — Sega CD
- Sega - Mega CD & Sega CD (BIN/CUE): Minerva Redump https://minerva-archive.org/browse/Redump/Sega%20-%20Mega%20CD%20&%20Sega%20CD/ | IA https://archive.org/download/sega_mega-cd_sega-cd
- Sega - Mega CD & Sega CD (CHD) USA: Minerva https://minerva-archive.org/browse/Internet%20Archive/chadmaster/chd_segacd/CHD-SegaCD-NTSC/ | IA https://archive.org/download/chd_segacd/CHD-SegaCD-NTSC/
- Sega - Mega CD & Sega CD (CHD) EUR: Minerva https://minerva-archive.org/browse/Internet%20Archive/chadmaster/chd_segacd/CHD-MegaCD-PAL/ | IA https://archive.org/download/chd_segacd/CHD-MegaCD-PAL/
- Sega - Mega CD & Sega CD (CHD) JPN: Minerva https://minerva-archive.org/browse/Internet%20Archive/chadmaster/chd_segacd/CHD-MegaCD-NTSCJ/ | IA https://archive.org/download/chd_segacd/CHD-MegaCD-NTSCJ/
- Sega - Mega CD & Sega CD (CHD) Bonus: Minerva https://minerva-archive.org/browse/Internet%20Archive/chadmaster/chd_segacd/CHD-SegaCD-Bonus/ | IA https://archive.org/download/chd_segacd/CHD-SegaCD-Bonus/

---

## Sony

### /Sony/nopaystation — NoPayStation
NoPayStation (nopaystation.com) is the best and fastest source for PSP, PS3 and PS Vita content — a database of games from Sony's CDN with decryption keys. Check it first.

### /Sony/sony-playstation — Sony PlayStation
- Sony - PlayStation: Minerva Redump https://minerva-archive.org/browse/Redump/Sony%20-%20PlayStation/
- Sony PlayStation (Part 1: #-D) - Redump.org: IA https://archive.org/download/sony_playstation_part1
- Sony PlayStation (Part 2: E-I) - Redump.org: IA https://archive.org/download/sony_playstation_part2
- Sony PlayStation (Part 3: J-N) - Redump.org: IA https://archive.org/download/sony_playstation_part3
- Sony PlayStation (Part 4: O-S) - Redump.org: IA https://archive.org/download/sony_playstation_part4
- Sony PlayStation (Part 5: T-Z) - Redump.org: IA https://archive.org/download/sony_playstation_part5
- PS1 Redump .chd USA: Minerva https://minerva-archive.org/browse/Internet%20Archive/chadmaster/chd_psx/CHD-PSX-USA/ | IA https://archive.org/download/chd_psx/CHD-PSX-USA/
- PS1 Redump .chd EUR: Minerva https://minerva-archive.org/browse/Internet%20Archive/chadmaster/chd_psx_eur/CHD-PSX-EUR/ | IA https://archive.org/download/chd_psx_eur/CHD-PSX-EUR/
- PS1 Redump .chd JPN Part 1: Minerva https://minerva-archive.org/browse/Internet%20Archive/chadmaster/chd_psx_jap/CHD-PSX-JAP/ | IA https://archive.org/download/chd_psx_jap/CHD-PSX-JAP/
- PS1 Redump .chd JPN Part 2: Minerva https://minerva-archive.org/browse/Internet%20Archive/chadmaster/chd_psx_jap_p2/CHD-PSX-JAP/ | IA https://archive.org/download/chd_psx_jap_p2/CHD-PSX-JAP/
- PS1 Redump .chd Misc: Minerva https://minerva-archive.org/browse/Internet%20Archive/chadmaster/chd_psx_misc/CHD-PSX-Misc/ | IA https://archive.org/download/chd_psx_misc/CHD-PSX-Misc/

### /Sony/sony-playstation-2 — Sony PlayStation 2
- Sony - PlayStation 2: Minerva Redump https://minerva-archive.org/browse/Redump/Sony%20-%20PlayStation%202/
- PS2 Redump 2024 Individual Games Part 1 (# - B): IA https://archive.org/details/PS2-Redump-2024-Individual-Games-Part1
- PS2 Redump 2024 Individual Games Part 2 (B - C): IA https://archive.org/details/PS2-Redump-2024-Individual-Games-Part2
- PS2 Redump 2024 Individual Games Part 3 (C - D): IA https://archive.org/details/PS2-Redump-2024-Individual-Games-Part3
- PS2 Redump 2024 Individual Games Part 4 (D - F): IA https://archive.org/details/PS2-Redump-2024-Individual-Games-Part4
- PS2 Redump 2024 Individual Games Part 5 (F - G): IA https://archive.org/details/PS2-Redump-2024-Individual-Games-Part5
- PS2 Redump 2024 Individual Games Part 6 (G - H): IA https://archive.org/details/PS2-Redump-2024-Individual-Games-Part6
- PS2 Redump 2024 Individual Games Part 7 (H - K): IA https://archive.org/details/PS2-Redump-2024-Individual-Games-Part7
- PS2 Redump 2024 Individual Games Part 8 (K - M): IA https://archive.org/details/PS2-Redump-2024-Individual-Games-Part8
- PS2 Redump 2024 Individual Games Part 9 (M - N): IA https://archive.org/details/PS2-Redump-2024-Individual-Games-Part9
- PS2 Redump 2024 Individual Games Part 10 (N - O): IA https://archive.org/details/PS2-Redump-2024-Individual-Games-Part10
- PS2 Redump 2024 Individual Games Part 11 (O - P): IA https://archive.org/details/PS2-Redump-2024-Individual-Games-Part11
- PS2 Redump 2024 Individual Games Part 12 (P - S): IA https://archive.org/details/PS2-Redump-2024-Individual-Games-Part12
- PS2 Redump 2024 Individual Games Part 13 (S - S): IA https://archive.org/details/PS2-Redump-2024-Individual-Games-Part13
- PS2 Redump 2024 Individual Games Part 14 (S - S, Part 2): IA https://archive.org/details/PS2-Redump-2024-Individual-Games-Part14
- PS2 Redump 2024 Individual Games Part 15 (S - T): IA https://archive.org/details/PS2-Redump-2024-Individual-Games-Part15
- PS2 Redump 2024 Individual Games Part 16 (T - W): IA https://archive.org/details/PS2-Redump-2024-Individual-Games-Part16
- PS2 Redump 2024 Individual Games Part 17 (W - Z): IA https://archive.org/details/PS2-Redump-2024-Individual-Games-Part17

### /Sony/sony-playstation-3 — Sony PlayStation 3
NoPayStation recommended; check it first.

Minerva (torrent-based):
- Sony - PlayStation 3: https://minerva-archive.org/browse/Redump/Sony%20-%20PlayStation%203/
- Sony - PlayStation 3 (PSN) (Content): https://minerva-archive.org/browse/No-Intro/Sony%20-%20PlayStation%203%20(PSN)%20(Content)/
- Sony - PlayStation 3 (PSN) (Updates): https://minerva-archive.org/browse/No-Intro/Sony%20-%20PlayStation%203%20(PSN)%20(Updates)/
- PS3 PSN Part 1: https://minerva-archive.org/browse/Internet%20Archive/aitus95/PS3_PSN_1/
- PS3 PSN Part 2: https://minerva-archive.org/browse/Internet%20Archive/aitus95/PS3_PSN_2/
- PS3 Games (# - C): https://minerva-archive.org/browse/Internet%20Archive/aitus95/PS3_ALVRO_PART_1/
- PS3 Games (C - D): https://minerva-archive.org/browse/Internet%20Archive/aitus95/PS3_ALVRO_PART_2/
- PS3 Games (D - G): https://minerva-archive.org/browse/Internet%20Archive/aitus95/PS3_ALVRO_PART_3/
- PS3 Games (D - G) (Other): https://minerva-archive.org/browse/Internet%20Archive/aitus95/PS3_ALVRO_PART_3_OTHER/
- PS3 Games (G - J): https://minerva-archive.org/browse/Internet%20Archive/aitus95/PS3_ALVRO_PART_4/
- PS3 Games (J - M): https://minerva-archive.org/browse/Internet%20Archive/aitus95/PS3_ALVRO_PART__5/
- PS3 Games (M - N): https://minerva-archive.org/browse/Internet%20Archive/aitus95/PS3_ALVRO_PART_6/
- PS3 Games (N - R): https://minerva-archive.org/browse/Internet%20Archive/aitus95/PS3_ALVRO_PART_7/
- PS3 Games (R - S): https://minerva-archive.org/browse/Internet%20Archive/aitus95/PS3_ALVRO_PART_8/
- PS3 Games (S - T): https://minerva-archive.org/browse/Internet%20Archive/aitus95/PS3_ALVRO_PART_9/
- PS3 Games (T): https://minerva-archive.org/browse/Internet%20Archive/aitus95/PS3_ALVRO_PART_10/
- PS3 Games (T - Z): https://minerva-archive.org/browse/Internet%20Archive/aitus95/PS3_ALVRO_PART_11/

Internet Archive:
- PS3 No-Intro USA Part 1..10: https://archive.org/download/PS3_NOINTRO_USA_1 .. PS3_NOINTRO_USA_10 (note Part 5 is PS3_NOINTRO_USA__5)
- PS3 No-Intro EUR Part 1..8: https://archive.org/download/PS3_NOINTRO_EUR_1 .. PS3_NOINTRO_EUR_8
- PS3 No-Intro JAP Part 1..4: https://archive.org/download/PS3_NOINTRO_JAP_1 .. PS3_NOINTRO_JAP_4
- PS3 PSN Part 1: https://archive.org/download/PS3_PSN_1
- PS3 PSN Part 2: https://archive.org/download/PS3_PSN_2
- Sony PlayStation 3 - Redump 2024 Parts 1..34 (ranges #-A through W-Z): IA details pages https://archive.org/details/PS3-Redump-2024-Individual-Games-Part1 .. Part34

### /Sony/sony-playstation-portable — Sony PlayStation Portable (PSP)
- Sony - PlayStation Portable: Minerva Redump https://minerva-archive.org/browse/Redump/Sony%20-%20PlayStation%20Portable/
- PSP Redump .iso (Part 1): IA https://archive.org/download/sony_playstation_portable_part1
- PSP Redump .iso (Part 2): IA https://archive.org/download/sony_playstation_portable_part2
- PSP Redump .iso (Part 3): IA https://archive.org/download/sony_playstation_portable_part3
- PSP Redump .iso (Part 4): IA https://archive.org/download/sony_playstation_portable_part4
- PSP Redump .chd (Part 1): Minerva https://minerva-archive.org/browse/Internet%20Archive/chadmaster/psp-chd-zstd-redump-part1/psp-chd-zstd/ | IA https://archive.org/download/psp-chd-zstd-redump-part1/psp-chd-zstd/
- PSP Redump .chd (Part 2): Minerva https://minerva-archive.org/browse/Internet%20Archive/chadmaster/psp-chd-zstd-redump-part2/psp-chd-zstd/ | IA https://archive.org/download/psp-chd-zstd-redump-part2/psp-chd-zstd/
- PSP DLC: Minerva https://minerva-archive.org/browse/Internet%20Archive/storage_manager/PSP-DLC/PSP%20DLC/ | IA https://archive.org/download/PSP-DLC/PSP%20DLC/
- PSP No-Intro DLC: Minerva https://minerva-archive.org/browse/Internet%20Archive/storage_manager/PSP-DLC/%5BNo-Intro%5D%20PSP%20DLC/ | IA https://archive.org/download/PSP-DLC/%5BNo-Intro%5D%20PSP%20DLC/
- PSP DLC (Alvro Files): IA https://archive.org/download/PSP_DLC

### /Sony/sony-playstation-vita — Sony PlayStation Vita
NoPayStation recommended; check it first.
- Sony - PlayStation Vita (PSN) (Content): Minerva No-Intro https://minerva-archive.org/browse/No-Intro/Sony%20-%20PlayStation%20Vita%20(PSN)%20(Content)/
- Sony - PlayStation Vita (PSN) (Updates): Minerva No-Intro https://minerva-archive.org/browse/No-Intro/Sony%20-%20PlayStation%20Vita%20(PSN)%20(Updates)/
- Unofficial - Sony - PlayStation Vita (BlackFinPSV): Minerva No-Intro https://minerva-archive.org/browse/No-Intro/Unofficial%20-%20Sony%20-%20PlayStation%20Vita%20(BlackFinPSV)/
- Unofficial - Sony - PlayStation Vita (NoNpDrm): Minerva No-Intro https://minerva-archive.org/browse/No-Intro/Unofficial%20-%20Sony%20-%20PlayStation%20Vita%20(NoNpDrm)/
- Unofficial - Sony - PlayStation Vita (PSN) (Decrypted) (VPK): Minerva No-Intro https://minerva-archive.org/browse/No-Intro/Unofficial%20-%20Sony%20-%20PlayStation%20Vita%20(PSN)%20(Decrypted)%20(VPK)/
- Unofficial - Sony - PlayStation Vita (PSVgameSD): Minerva No-Intro https://minerva-archive.org/browse/No-Intro/Unofficial%20-%20Sony%20-%20PlayStation%20Vita%20(PSVgameSD)/
- Unofficial - Sony - PlayStation Vita (VPK): Minerva No-Intro https://minerva-archive.org/browse/No-Intro/Unofficial%20-%20Sony%20-%20PlayStation%20Vita%20(VPK)/
- Sony - PlayStation Vita Games (USA)(NoNpDRM): IA https://archive.org/download/sony-playstation-vita-usa-full-set-nonpdrm-format
- Sony - PlayStation Vita DLC & Updates (USA)(NoNpDRM): Minerva https://minerva-archive.org/browse/Internet%20Archive/teamgt19/sony-playstation-vita-usa-full-set-nonpdrm-format-dlc-updates/ | IA https://archive.org/download/sony-playstation-vita-usa-full-set-nonpdrm-format-dlc-updates
- PSVITA VPK: IA https://archive.org/download/PSVITA_VPK
- PSVITA MAIDUMP: Minerva https://minerva-archive.org/browse/Internet%20Archive/aitus95/PSVITA_MAIDUMP/ | IA https://archive.org/download/PSVITA_MAIDUMP

---

## Microsoft

### /Microsoft/microsoft-xbox — Microsoft Xbox
- Microsoft - Xbox: Minerva Redump https://minerva-archive.org/browse/Redump/Microsoft%20-%20Xbox/
- Microsoft Xbox - # - Redump.org: IA https://archive.org/download/microsoft_xbox_numberssymbols
- Microsoft Xbox - A - Redump.org: IA https://archive.org/download/microsoft_xbox_a
- Microsoft Xbox - B - Redump.org: IA https://archive.org/download/microsoft_xbox_b
- Microsoft Xbox - C (Part 1) - Redump.org: IA https://archive.org/download/microsoft_xbox_c_part1
- Microsoft Xbox - C (Part 2) - Redump.org: IA https://archive.org/download/microsoft_xbox_c_part2
- Microsoft Xbox - D (Part 1) - Redump.org: IA https://archive.org/download/microsoft_xbox_d_part1
- Microsoft Xbox - D (Part 2) - Redump.org: IA https://archive.org/download/microsoft_xbox_d_part2
- Microsoft Xbox - E - Redump.org: IA https://archive.org/download/microsoft_xbox_e
- Microsoft Xbox - F - Redump.org: IA https://archive.org/download/microsoft_xbox_f
- Microsoft Xbox - G - Redump.org: IA https://archive.org/download/microsoft_xbox_g
- Microsoft Xbox - H - Redump.org: IA https://archive.org/download/microsoft_xbox_h
- Microsoft Xbox - I - Redump.org: IA https://archive.org/download/microsoft_xbox_i
- Microsoft Xbox - J - Redump.org: IA https://archive.org/download/microsoft_xbox_j
- Microsoft Xbox - K - Redump.org: IA https://archive.org/download/microsoft_xbox_k
- Microsoft Xbox - L - Redump.org: IA https://archive.org/download/microsoft_xbox_l
- Microsoft Xbox - M (Part 1) - Redump.org: IA https://archive.org/download/microsoft_xbox_m_part1
- Microsoft Xbox - M (Part 2) - Redump.org: IA https://archive.org/download/microsoft_xbox_m_part2
- Microsoft Xbox - N (Part 1) - Redump.org: IA https://archive.org/download/microsoft_xbox_n_part1
- Microsoft Xbox - N (Part 2) - Redump.org: IA https://archive.org/download/microsoft_xbox_n_part2
- Microsoft Xbox - O (Part 1) - Redump.org: IA https://archive.org/download/microsoft_xbox_o_part1
- Microsoft Xbox - O (Part 2) - Redump.org: IA https://archive.org/download/microsoft_xbox_o_part2
- Microsoft Xbox - P - Redump.org: IA https://archive.org/download/microsoft_xbox_p
- Microsoft Xbox - Q - Redump.org: IA https://archive.org/download/microsoft_xbox_q
- Microsoft Xbox - R - Redump.org: IA https://archive.org/download/microsoft_xbox_r
- Microsoft Xbox - S (Part 1) - Redump.org: IA https://archive.org/download/microsoft_xbox_s_part1
- Microsoft Xbox - S (Part 2) - Redump.org: IA https://archive.org/download/microsoft_xbox_s_part2
- Microsoft Xbox - T (Part 1) - Redump.org: IA https://archive.org/download/microsoft_xbox_t_part1
- Microsoft Xbox - T (Part 2) - Redump.org: IA https://archive.org/download/microsoft_xbox_t_part2
- Microsoft Xbox - U - Redump.org: IA https://archive.org/download/microsoft_xbox_u
- Microsoft Xbox - V - Redump.org: IA https://archive.org/download/microsoft_xbox_v
- Microsoft Xbox - W - Redump.org: IA https://archive.org/download/microsoft_xbox_w
- Microsoft Xbox - X - Redump.org: IA https://archive.org/download/microsoft_xbox_x
- Microsoft Xbox - Y - Redump.org: IA https://archive.org/download/microsoft_xbox_y
- Microsoft Xbox - Z - Redump.org: IA https://archive.org/download/microsoft_xbox_z

### /Microsoft/microsoft-xbox360 — Microsoft Xbox 360
- Microsoft - Xbox 360: Minerva Redump https://minerva-archive.org/browse/Redump/Microsoft%20-%20Xbox%20360/
- Microsoft Xbox 360 - # - Redump.org: IA https://archive.org/download/microsoft_xbox360_numberssymbols
- Microsoft Xbox 360 - A (Part 1) - Redump.org: IA https://archive.org/download/microsoft_xbox360_a_part1
- Microsoft Xbox 360 - A (Part 2) - Redump.org: IA https://archive.org/download/microsoft_xbox360_a_part2
- Microsoft Xbox 360 - B (Part 1) - Redump.org: IA https://archive.org/download/microsoft_xbox360_b_part1
- Microsoft Xbox 360 - B (Part 2) - Redump.org: IA https://archive.org/download/microsoft_xbox360_b_part2
- Microsoft Xbox 360 - C (Part 1) - Redump.org: IA https://archive.org/download/microsoft_xbox360_c_part1
- Microsoft Xbox 360 - C (Part 2) - Redump.org: IA https://archive.org/download/microsoft_xbox360_c_part2
- Microsoft Xbox 360 - D (Part 1) - Redump.org: IA https://archive.org/download/microsoft_xbox360_d_part1
- Microsoft Xbox 360 - D (Part 2) - Redump.org: IA https://archive.org/download/microsoft_xbox360_d_part2
- Microsoft Xbox 360 - D (Part 3) - Redump.org: IA https://archive.org/download/microsoft_xbox360_d_part3
- Microsoft Xbox 360 - E - Redump.org: IA https://archive.org/download/microsoft_xbox360_e
- Microsoft Xbox 360 - F (Part 1) - Redump.org: IA https://archive.org/download/microsoft_xbox360_f_part1
- Microsoft Xbox 360 - F (Part 2) - Redump.org: IA https://archive.org/download/microsoft_xbox360_f_part2
- Microsoft Xbox 360 - G - Redump.org: IA https://archive.org/download/microsoft_xbox360_g
- Microsoft Xbox 360 - H - Redump.org: IA https://archive.org/download/microsoft_xbox360_h
- Microsoft Xbox 360 - I - Redump.org: IA https://archive.org/download/microsoft_xbox360_i
- Microsoft Xbox 360 - J - Redump.org: IA https://archive.org/download/microsoft_xbox360_j
- Microsoft Xbox 360 - K - Redump.org: IA https://archive.org/download/microsoft_xbox360_k
- Microsoft Xbox 360 - L - Redump.org: IA https://archive.org/download/microsoft_xbox360_l
- Microsoft Xbox 360 - M (Part 1) - Redump.org: IA https://archive.org/download/microsoft_xbox360_m_part1
- Microsoft Xbox 360 - M (Part 2) - Redump.org: IA https://archive.org/download/microsoft_xbox360_m_part2
- Microsoft Xbox 360 - N (Part 1) - Redump.org: IA https://archive.org/download/microsoft_xbox360_n_part1
- Microsoft Xbox 360 - N (Part 2) - Redump.org: IA https://archive.org/download/microsoft_xbox360_n_part2
- Microsoft Xbox 360 - O - Redump.org: IA https://archive.org/download/microsoft_xbox360_o
- Microsoft Xbox 360 - P - Redump.org: IA https://archive.org/download/microsoft_xbox360_p
- Microsoft Xbox 360 - Q - Redump.org: IA https://archive.org/download/microsoft_xbox360_q
- Microsoft Xbox 360 - R - Redump.org: IA https://archive.org/download/microsoft_xbox360_r
- Microsoft Xbox 360 - S (Part 1) - Redump.org: IA https://archive.org/download/microsoft_xbox360_s_part1
- Microsoft Xbox 360 - S (Part 2) - Redump.org: IA https://archive.org/download/microsoft_xbox360_s_part2
- Microsoft Xbox 360 - T (Part 1) - Redump.org: IA https://archive.org/download/microsoft_xbox360_t_part1
- Microsoft Xbox 360 - T (Part 2) - Redump.org: IA https://archive.org/download/microsoft_xbox360_t_part2
- Microsoft Xbox 360 - U - Redump.org: IA https://archive.org/download/microsoft_xbox360_u
- Microsoft Xbox 360 - V - Redump.org: IA https://archive.org/download/microsoft_xbox360_v
- Microsoft Xbox 360 - W - Redump.org: IA https://archive.org/download/microsoft_xbox360_w
- Microsoft Xbox 360 - X (Part 1) - Redump.org: IA https://archive.org/download/microsoft_xbox360_x_part1
- Microsoft Xbox 360 - X (Part 2) - Redump.org: IA https://archive.org/download/microsoft_xbox360_x_part2
- Microsoft Xbox 360 - Y - Redump.org: IA https://archive.org/download/microsoft_xbox360_y
- Microsoft Xbox 360 - Z - Redump.org: IA https://archive.org/download/microsoft_xbox360_z
- Unofficial - Microsoft - Xbox 360 (Title Updates): Minerva No-Intro https://minerva-archive.org/browse/No-Intro/Unofficial%20-%20Microsoft%20-%20Xbox%20360%20(Title%20Updates)/
- Microsoft - Xbox 360 (Digital): Minerva No-Intro https://minerva-archive.org/browse/No-Intro/Microsoft%20-%20Xbox%20360%20(Digital)/
- Microsoft Xbox 360 - Title Updates - No-Intro: IA https://archive.org/download/microsoft_xbox360_title-updates
- Microsoft Xbox 360 - Digital (Part 1): IA https://archive.org/download/microsoft_xbox360_digital_part1
- Microsoft Xbox 360 - Digital (Part 2): IA https://archive.org/download/microsoft_xbox360_digital_part2
- Microsoft Xbox 360 - Digital (Part 3): IA https://archive.org/download/microsoft_xbox360_digital_part3
- Microsoft Xbox 360 - Digital (Part 4): IA https://archive.org/download/microsoft_xbox360_digital_part4
- Microsoft Xbox 360 - Digital (Part 5): IA https://archive.org/download/microsoft_xbox360_digital_part5
- Microsoft Xbox 360 - Digital (Part 6): IA https://archive.org/download/microsoft_xbox360_digital_part6
- Microsoft Xbox 360 - Digital (Part 7): IA https://archive.org/download/microsoft_xbox360_digital_part7
- Xbox 360 Games (# - D) (Other): IA https://archive.org/download/XBOX_360_1_OTHER
- Xbox 360 Games (# - D): IA https://archive.org/download/XBOX_360_1
- Xbox 360 Games (D - H): IA https://archive.org/download/XBOX_360_2
- Xbox 360 Games (H - M): IA https://archive.org/download/XBOX_360_3
- Xbox 360 Games (M - P): IA https://archive.org/download/XBOX_360_4
- Xbox 360 Games (P - T): IA https://archive.org/download/XBOX_360_5
- Xbox 360 Games (T - Z): IA https://archive.org/download/XBOX_360_6
- Xbox 360 DLC Part 1: IA https://archive.org/download/XBOX_360_DLC_1
- Xbox 360 DLC Part 2: IA https://archive.org/download/XBOX_360_DLC_2
- Xbox 360 DLC Part 3: IA https://archive.org/download/XBOX_360_DLC_3
- Xbox 360 DLC Part 4: IA https://archive.org/download/XBOX_360_DLC_4
- Xbox 360 DLC Part 5: IA https://archive.org/download/XBOX_360_DLC_5
- Xbox 360 DLC Part 6: IA https://archive.org/download/XBOX_360_DLC_6
- Xbox 360 XBLIG Part 1: IA https://archive.org/download/XBOX_360_XBLIG_1
- Xbox 360 XBLIG Part 2: IA https://archive.org/download/XBOX_360_XBLIG_2
- Xbox 360 XBLIG Part 3: IA https://archive.org/download/XBOX_360_XBLIG_3
- Xbox 360 XBLIG Part 4: IA https://archive.org/download/XBOX_360_XBLIG_4
- Xbox 360 XBLA: IA https://archive.org/download/XBOX_360_XBLA
- Xbox 360 XBLA DLC: IA https://archive.org/download/XBOX_360_XBLA_DLC
- Rock Band DLC Complete Collection Xbox 360 by Americo: Minerva https://minerva-archive.org/browse/Internet%20Archive/mdashk/rock-band-dlc-complete-collection-xbox-360-by-americo/ | IA https://archive.org/download/rock-band-dlc-complete-collection-xbox-360-by-americo

---

## Local clone
The full site source is cloned at `~/claudeconfig/r-roms-site`. It is a SvelteKit app; routes live at `src/routes/<category>/<page>/+page.svelte`, and the nav/data pattern is reusable. Use `git -C ~/claudeconfig/r-roms-site pull --ff-only` to refresh it.
