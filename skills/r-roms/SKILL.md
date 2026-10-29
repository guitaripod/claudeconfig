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

## Download links by category

The per-page mirrors live in one file per category. Read only the file for the category you need:
- `references/general.md`: General (ddl, torrents, preservation, other)
- `references/populars.md`: Populars (about-rvz-files, metroid, mario, fire-emblem, zelda, pokemon, super-smash-bros, xenoblade)
- `references/nintendo.md`: Nintendo (nintendo-games, nintendo-ds, nintendo-3ds, nintendo-gamecube, nintendo-wii, nintendo-wii-u)
- `references/pc.md`: PC (pc-games)
- `references/miscellaneous.md`: Miscellaneous (rom-sets, bios-sets, other)
- `references/retro-arcade.md`: Retro & Arcade (retro-games, arcade)
- `references/sega.md`: Sega (sega-games, sega-dreamcast, sega-saturn, sega-cd)
- `references/sony.md`: Sony (nopaystation, sony-playstation, sony-playstation-2, sony-playstation-3, sony-playstation-portable, sony-playstation-vita)
- `references/microsoft.md`: Microsoft (microsoft-xbox, microsoft-xbox360)

## Local clone
The full site source is cloned at `~/claudeconfig/r-roms-site`. It is a SvelteKit app; routes live at `src/routes/<category>/<page>/+page.svelte`, and the nav/data pattern is reusable. Use `git -C ~/claudeconfig/r-roms-site pull --ff-only` to refresh it.
