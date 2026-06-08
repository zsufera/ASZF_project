---
description: Elindítja a backendet és/vagy a frontendet helyi fejlesztéshez (Windows-tudatosan).
argument-hint: "[backend|frontend|both] (alap: both)"
---

Indítsd el a megadott szolgáltatás(oka)t: `$1` (ha üres: mindkettő).

Szabályok és lépések:
1. **Ellenőrizd a portokat először** (8000 backend, 5173 frontend). Ha már fut valami a porton, NE indíts másodikat — jelezd a felhasználónak (a korábbi port-ütközés ebből adódott).
2. **Backend** (ha kért): `uvicorn backend.main:app --reload` a repo gyökeréből, a `.venv`-vel. Friss indítás tölti be a legutóbbi kódot. Háttérben indítsd. Várd meg az „Application startup complete" sort, mielőtt tesztelnél ellene.
3. **Frontend** (ha kért): `cd frontend; npm install; npm run dev` (port 5173). Vite HMR-rel.
4. Ne használj `&&` láncot PowerShellben — `;` vagy külön parancsok.
5. A végén írd ki a belépési adatokat: `ui_demo / ui_demo` (vagy `supervisor_demo / supervisor_demo`), és az URL-eket.

Megjegyzés: ha a backendet a felhasználó a saját termináljából futtatja, ne foglald el a 8000-es portot egy háttérfolyamattal.
