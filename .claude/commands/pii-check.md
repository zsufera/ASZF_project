---
description: Átnézi az aktuális diffet a use-case kritikus kockázataira (PII-egress, LLM-fallback/temperature, forrásolás, eszkaláció-auditálhatóság).
---

Nézd át az **aktuális, még nem commitolt változtatásokat** (`git diff` + `git diff --staged`) ennek a szabályozott, PII-érzékeny copilotnak a kritikus kockázataira. Ez NEM általános code review — a guardrails (`FEJLESZTESI_GUARDRAILS.md` §10–11) kapuit és a repo-specifikus buktatókat ellenőrzöd.

Menj végig és jelezz minden találatot fájl:sor hivatkozással:

**PII / adatbiztonság**
- Kerül-e **maszkolatlan PII** logba, `print`-be, exception-üzenetbe, trace-be, audit-payloadba vagy teszt-fixture-be?
- LLM-promptba **csak maszkolt** szöveg megy? (`chat_json` hívás bemenete)
- Ügyfél-felé menő szövegből eltávolítják-e a `[Sn]` jelölőket (`strip_source_markers`) az approve/unmask úton?

**LLM-hívás idióma**
- Van **determinisztikus fallback** és **`*_mode` mező**?
- A kivételt **logolják** (`logger.exception`), nem nyelik el némán?
- Nem vezettek-e vissza feltétlen `temperature=`-t a `chat_json`/`_chat_completion` megkerülésével? (gpt-5/o-széria elutasítja)
- A kimenet **validált** (kategória-whitelist, létező citation-id, séma)?

**Forrásolás / agent / audit**
- Minden tartalmi állítás **visszavezethető `chunk_id`-ra**? Nincs fedezet nélküli jogi állítás?
- Eszkalációs döntésnél megvannak az **okok** (auditálható)?
- Új agent-node esetén: van idővonal-bejegyzés ÉS `STEP_META` címke a frontenden?
- Keveredhetnek-e a szolgáltatók dokumentumai a retrievalben?

**Tesztelhetőség / kapuk**
- Új viselkedéshez van **célzott teszt** (regresszióhoz reprodukáló)? Strukturális assert, nem szöveg-snapshot?
- Külső szolgáltatás nélkül fut a teszt (hermetikus)?
- README/spec frissült-e, ha futtatás/endpoint/config változott?

A végén adj rövid, priorizált listát (🔴 blokkoló / 🟠 fontos / 🟢 apró), és javasolj konkrét javítást a 🔴/🟠 elemekhez.
