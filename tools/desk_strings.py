"""Desk-only translation strings (keys prefixed DESK_*).

These have NO firmware counterpart (Connect/Live-read/History/... chrome that only
exists in the PC app), so unlike the S_* keys they are NOT derived from the firmware
STRTAB — they are authored here by hand and MERGED into the catalogs by
`gen_locales.py`. Keep the firmware-shared vocabulary in `S_*` keys (from STRTAB);
add only genuinely Desk-specific text here.

Confidence: FR reviewed (infinitive register). DE/ES are a first full pass (all keys
translated, no EN fallback) — a native proofread is still recommended, same as the
DE/ES accents in `locale_accents.py`.
Each entry: DESK_KEY -> {en, fr, de, es}. printf %s/%d and {name} (str.format) are
honored by i18n.t().
"""

DESK = {
    # --- Sidebar navigation / top-bar titles ---
    # (Repair/Settings/About reuse the firmware S_REPAIR/S_SETTINGS/S_ABOUT keys.)
    "DESK_NAV_CONNECT": {
        "en": "Connect", "fr": "Connecter",
        "de": "Verbinden", "es": "Conectar"},
    "DESK_NAV_LIVE": {
        "en": "Live read", "fr": "Lecture directe",
        "de": "Direktmessung", "es": "Lectura directa"},
    "DESK_NAV_BATTERIES": {
        "en": "Batteries", "fr": "Batteries",
        "de": "Akkus", "es": "Baterías"},

    # --- Live read screen ---
    "DESK_READ_PACK": {
        "en": "Read pack", "fr": "Lire le pack",
        "de": "Akku lesen", "es": "Leer batería"},
    "DESK_READING": {
        "en": "Reading…", "fr": "Lecture…",
        "de": "Lese…", "es": "Leyendo…"},
    "DESK_CONNECT_FIRST_HINT": {
        "en": "Connect a bridge, then read a pack.",
        "fr": "Connecter un pont, puis lire un pack.",
        "de": "Bridge verbinden, dann Akku lesen.",
        "es": "Conectar un puente y luego leer una batería."},
    # Our OWN cycle-based health estimate (not the Makita SOH gauge).
    "DESK_HEALTH_EST": {
        "en": "Health (est.)", "fr": "Santé (est.)",
        "de": "Zustand (gesch.)", "es": "Salud (est.)"},
    # Pack age in whole years, shown next to the production date. %d = the number.
    "DESK_AGE_YEARS": {
        "en": "%d yr", "fr": "%d ans",
        "de": "%d J.", "es": "%d años"},
    "DESK_NOT_CONNECTED": {
        "en": "Not connected - open Connect first.",
        "fr": "Non connecté - ouvrir Connecter d'abord.",
        "de": "Nicht verbunden - erst Verbinden öffnen.",
        "es": "Sin conexión - abrir Conectar primero."},
    "DESK_READING_PACK": {
        "en": "Reading pack…", "fr": "Lecture du pack…",
        "de": "Lese Akku…", "es": "Leyendo batería…"},
    "DESK_NO_PACK_DETECTED": {
        "en": "No pack detected.", "fr": "Aucun pack détecté.",
        "de": "Kein Akku erkannt.", "es": "Ninguna batería detectada."},
    "DESK_READ_OK": {
        "en": "Read OK.", "fr": "Lecture OK.",
        "de": "Lesen OK.", "es": "Lectura OK."},
    "DESK_READ_FAIL_BRIDGE": {
        "en": "Read failed (no response). The PocketOBI may have left PC bridge "
              "mode - check its screen shows 'USB bridge ACTIVE'.",
        "fr": "Échec de lecture (pas de réponse). PocketOBI a peut-être quitté "
              "le mode pont PC - vérifier que son écran affiche 'USB bridge ACTIVE'.",
        "de": "Lesen fehlgeschlagen (keine Antwort). Der PocketOBI hat evtl. den "
              "PC-Brücken-Modus verlassen - Anzeige sollte 'USB bridge ACTIVE' zeigen.",
        "es": "Fallo de lectura (sin respuesta). El PocketOBI puede haber salido del "
              "modo puente PC - comprobar que muestre 'USB bridge ACTIVE'."},
    "DESK_READ_FAIL": {
        "en": "Read failed: %s", "fr": "Échec de lecture : %s",
        "de": "Lesen fehlgeschlagen: %s", "es": "Fallo de lectura: %s"},
    "DESK_SAVE_READING": {
        "en": "Save reading", "fr": "Enregistrer la lecture",
        "de": "Messung speichern", "es": "Guardar lectura"},
    "DESK_SAVED_READING": {
        "en": "Saved reading #%d to history.",
        "fr": "Lecture #%d enregistrée dans l'historique.",
        "de": "Messung #%d im Verlauf gespeichert.",
        "es": "Lectura #%d guardada en el historial."},
    "DESK_SAVE_FAIL": {
        "en": "Save failed: %s", "fr": "Échec de l'enregistrement : %s",
        "de": "Speichern fehlgeschlagen: %s", "es": "Fallo al guardar: %s"},
    "DESK_PACK_VOLTAGE": {
        "en": "Pack voltage", "fr": "Tension pack",
        "de": "Pack-Spannung", "es": "Tensión del pack"},
    "DESK_CELL_VOLTAGES": {
        "en": "Cell voltages", "fr": "Tensions cellules",
        "de": "Zellspannungen", "es": "Tensiones de celdas"},
    "DESK_NOMINAL": {
        "en": "nominal 18.0 V · %dS Li-ion", "fr": "nominal 18.0 V · %dS Li-ion",
        "de": "nominal 18.0 V · %dS Li-ion", "es": "nominal 18.0 V · %dS Li-ion"},
    "DESK_CELL_TEMP": {
        "en": "Cell temp", "fr": "Temp. cellule",
        "de": "Zelltemp.", "es": "Temp celda"},
    "DESK_BOARD_TEMP": {
        "en": "Board temp", "fr": "Temp. carte",
        "de": "Platinentemp.", "es": "Temp placa"},
    "DESK_TEMP_SPREAD": {
        "en": "Temp spread", "fr": "Écart temp",
        "de": "Temp-Diff.", "es": "Dif. temp"},
    "DESK_CELL_SPREAD": {
        "en": "Cell spread", "fr": "Écart cellules",
        "de": "Zell-Diff.", "es": "Dif. celdas"},
    "DESK_CYCLES": {
        "en": "Cycles", "fr": "Cycles",
        "de": "Zyklen", "es": "Ciclos"},

    # --- Diagnostic engine (verdict.diagnose) — richer prose than the device, same
    # classification/terminology. {name} placeholders via i18n.t(..., **kwargs).
    "DESK_DIAG_PROBE_CELL":  {"en": "cell probe",  "fr": "sonde cellule",
                              "de": "Zellfühler", "es": "sonda de celda"},
    "DESK_DIAG_PROBE_BOARD": {"en": "board probe", "fr": "sonde carte",
                              "de": "Platinenfühler", "es": "sonda de placa"},
    "DESK_DIAG_PROBE_BOTH":  {"en": "cell and board probes", "fr": "sondes cellule et carte",
                              "de": "Zell- und Platinenfühler", "es": "sondas de celda y placa"},
    "DESK_DIAG_PROBE_CELL_W":  {"en": "cell",  "fr": "cellule", "de": "Zell", "es": "celda"},
    "DESK_DIAG_PROBE_BOARD_W": {"en": "board", "fr": "carte", "de": "Platinen", "es": "placa"},
    "DESK_DIAG_SENSE_TITLE": {"en": "Group {grp} reads ~0 V", "fr": "Groupe {grp} lit ~0 V",
                              "de": "Gruppe {grp} liest ~0 V", "es": "Grupo {grp} lee ~0 V"},
    "DESK_DIAG_SENSE_OBS": {
        "en": "group {grp} reads ~0 V while the pack is alive ({pv:.0f} V)",
        "fr": "le groupe {grp} lit ~0 V alors que le pack est vivant ({pv:.0f} V)",
        "de": "Gruppe {grp} liest ~0 V, während der Akku aktiv ist ({pv:.0f} V)",
        "es": "el grupo {grp} lee ~0 V mientras el pack está vivo ({pv:.0f} V)"},
    "DESK_DIAG_SENSE_CAUSE": {
        "en": "a dead group would pull the whole pack down, so this points to a broken "
              "sense (balance) lead on that group, not a dead cell",
        "fr": "un groupe mort ferait chuter tout le pack ; cela indique donc un fil de "
              "mesure (équilibrage) cassé sur ce groupe, pas une cellule morte",
        "de": "eine tote Gruppe würde den ganzen Akku herunterziehen; das deutet also auf "
              "eine gebrochene Sense-/Balance-Leitung an dieser Gruppe hin, nicht auf eine "
              "tote Zelle",
        "es": "un grupo muerto haría caer todo el pack, así que esto apunta a un cable de "
              "sensado (balanceo) roto en ese grupo, no a una celda muerta"},
    "DESK_DIAG_SENSE_CHECK": {
        "en": "measure group {grp} directly at the cells; if it is charged, inspect and "
              "reflow its sense lead",
        "fr": "mesurer le groupe {grp} directement aux cellules ; s'il est chargé, "
              "inspecter et ressouder son fil de mesure",
        "de": "Gruppe {grp} direkt an den Zellen messen; wenn geladen, die Sense-Leitung "
              "prüfen und nachlöten",
        "es": "medir el grupo {grp} directamente en las celdas; si está cargado, "
              "inspeccionar y resoldar su cable de sensado"},
    "DESK_DIAG_WEAK_TITLE": {"en": "Group {grp} is low", "fr": "Groupe {grp} bas",
                             "de": "Gruppe {grp} niedrig", "es": "Grupo {grp} bajo"},
    "DESK_DIAG_WEAK_OBS": {
        "en": "group {grp} reads {val:.2f} V, below the safe minimum",
        "fr": "le groupe {grp} lit {val:.2f} V, sous le minimum de sécurité",
        "de": "Gruppe {grp} liest {val:.2f} V, unter dem sicheren Minimum",
        "es": "el grupo {grp} lee {val:.2f} V, por debajo del mínimo seguro"},
    "DESK_DIAG_WEAK_CAUSE": {
        "en": "a tired group, or simply deeply discharged",
        "fr": "un groupe fatigué, ou simplement très déchargé",
        "de": "eine müde Gruppe, oder einfach tiefentladen",
        "es": "un grupo cansado, o simplemente muy descargado"},
    "DESK_DIAG_WEAK_CHECK": {
        "en": "measure group {grp} with a DMM; try a gentle slow charge and re-read - if "
              "it will not hold above {vmin:.1f} V, it is failing",
        "fr": "mesurer le groupe {grp} au multimètre ; tenter une charge lente et relire - "
              "s'il ne tient pas au-dessus de {vmin:.1f} V, il est défaillant",
        "de": "Gruppe {grp} mit einem Multimeter messen; langsam laden und erneut lesen - "
              "hält sie nicht über {vmin:.1f} V, ist sie defekt",
        "es": "medir el grupo {grp} con un multímetro; probar una carga lenta y releer - "
              "si no aguanta por encima de {vmin:.1f} V, está fallando"},
    "DESK_DIAG_IMB_TITLE": {"en": "Cells are imbalanced", "fr": "Cellules déséquilibrées",
                            "de": "Zellen unsymmetrisch", "es": "Celdas desequilibradas"},
    "DESK_DIAG_IMB_OBS": {
        "en": "a {diff:.2f} V cell spread, group {grp} lowest",
        "fr": "un écart de {diff:.2f} V entre cellules, groupe {grp} le plus bas",
        "de": "eine Zelldifferenz von {diff:.2f} V, Gruppe {grp} am niedrigsten",
        "es": "una diferencia de {diff:.2f} V entre celdas, grupo {grp} el más bajo"},
    "DESK_DIAG_IMB_CAUSE": {
        "en": "often drift a balance charge fixes; sometimes a weakening group",
        "fr": "souvent une dérive qu'une charge d'équilibrage corrige ; parfois un groupe "
              "qui faiblit",
        "de": "oft eine Drift, die eine Balance-Ladung behebt; manchmal eine schwächelnde "
              "Gruppe",
        "es": "a menudo una deriva que una carga de balanceo corrige; a veces un grupo que "
              "se debilita"},
    "DESK_DIAG_IMB_CHECK": {
        "en": "slow-charge and re-read - spread closes = drift, group {grp} stays low = weakening",
        "fr": "charger lentement et relire - l'écart se referme = dérive, le groupe {grp} "
              "reste bas = faiblesse",
        "de": "langsam laden und erneut lesen - Differenz schließt sich = Drift, Gruppe "
              "{grp} bleibt niedrig = Schwäche",
        "es": "cargar lento y releer - la diferencia se cierra = deriva, el grupo {grp} "
              "sigue bajo = debilidad"},
    "DESK_DIAG_THERM_TITLE": {
        "en": "Temperature probe reading is off",
        "fr": "Lecture de sonde de température anormale",
        "de": "Temperaturfühler-Messwert auffällig",
        "es": "Lectura de sonda de temperatura anómala"},
    "DESK_DIAG_THERM_OBS_BOTH": {
        "en": "both probes read impossible values ({tc:.0f} °C / {tm:.0f} °C)",
        "fr": "les deux sondes lisent des valeurs impossibles ({tc:.0f} °C / {tm:.0f} °C)",
        "de": "beide Fühler lesen unmögliche Werte ({tc:.0f} °C / {tm:.0f} °C)",
        "es": "ambas sondas leen valores imposibles ({tc:.0f} °C / {tm:.0f} °C)"},
    "DESK_DIAG_THERM_OBS_ONE": {
        "en": "the {name} reads {val:.0f} °C - an impossible value - while the {other_name} "
              "reads {other_v:.0f} °C",
        "fr": "la {name} lit {val:.0f} °C - valeur impossible - alors que la {other_name} "
              "lit {other_v:.0f} °C",
        "de": "der {name} liest {val:.0f} °C - ein unmöglicher Wert - während der "
              "{other_name} {other_v:.0f} °C liest",
        "es": "la {name} lee {val:.0f} °C - un valor imposible - mientras la {other_name} "
              "lee {other_v:.0f} °C"},
    "DESK_DIAG_THERM_CAUSE": {
        "en": "the reading is untrustworthy: most often a disconnected or dead {probe} thermistor",
        "fr": "lecture peu fiable : le plus souvent une thermistance {probe} débranchée ou morte",
        "de": "der Messwert ist unzuverlässig: meist ein abgeklemmter oder toter "
              "{probe}-Thermistor",
        "es": "la lectura no es fiable: casi siempre un termistor de {probe} desconectado o muerto"},
    "DESK_DIAG_THERM_CAUSE_RU": {
        "en": "the reading is untrustworthy: most often a disconnected or dead {probe} "
              "thermistor, though a real extreme is just possible if the pack was stressed",
        "fr": "lecture peu fiable : le plus souvent une thermistance {probe} débranchée ou "
              "morte, même si une vraie valeur extrême reste possible si le pack a été sollicité",
        "de": "der Messwert ist unzuverlässig: meist ein abgeklemmter oder toter "
              "{probe}-Thermistor, wobei ein echtes Extrem knapp möglich ist, wenn der Akku "
              "belastet wurde",
        "es": "la lectura no es fiable: casi siempre un termistor de {probe} desconectado o "
              "muerto, aunque un extremo real es apenas posible si el pack fue exigido"},
    "DESK_DIAG_THERM_CHECK": {
        "en": "re-read at room temperature; if it still reads this, check and replace the {name}",
        "fr": "relire à température ambiante ; si la valeur persiste, contrôler et remplacer "
              "la {name}",
        "de": "bei Raumtemperatur erneut lesen; bleibt der Wert, den {name} prüfen und ersetzen",
        "es": "releer a temperatura ambiente; si persiste, comprobar y sustituir la {name}"},
    "DESK_DIAG_THERM_CHECK_RU": {
        "en": "let the pack settle to room temperature, then re-read; if it still reads this, "
              "check and replace the {name}",
        "fr": "laisser le pack revenir à température ambiante, puis relire ; si la valeur "
              "persiste, contrôler et remplacer la {name}",
        "de": "den Akku auf Raumtemperatur kommen lassen, dann erneut lesen; bleibt der "
              "Wert, den {name} prüfen und ersetzen",
        "es": "dejar que el pack se estabilice a temperatura ambiente, luego releer; si "
              "persiste, comprobar y sustituir la {name}"},
    "DESK_DIAG_GAP_TITLE": {
        "en": "Cell and board temperatures disagree",
        "fr": "Températures cellule et carte divergentes",
        "de": "Zell- und Platinentemperatur weichen ab",
        "es": "Temperaturas de celda y placa difieren"},
    "DESK_DIAG_GAP_OBS": {
        "en": "cell probe {tc:.0f} °C vs board probe {tm:.0f} °C - a {gap:.0f} °C temperature spread",
        "fr": "sonde cellule {tc:.0f} °C contre sonde carte {tm:.0f} °C - un écart de {gap:.0f} °C",
        "de": "Zellfühler {tc:.0f} °C gegenüber Platinenfühler {tm:.0f} °C - eine Differenz "
              "von {gap:.0f} °C",
        "es": "sonda de celda {tc:.0f} °C frente a sonda de placa {tm:.0f} °C - una "
              "diferencia de {gap:.0f} °C"},
    "DESK_DIAG_GAP_CAUSE": {
        "en": "measured at rest, a wide gap points more to a drifting probe than to real heat",
        "fr": "au repos, un écart important indique plutôt une sonde qui dérive qu'une vraie chaleur",
        "de": "in Ruhe deutet eine große Differenz eher auf einen driftenden Fühler als auf "
              "echte Wärme hin",
        "es": "medido en reposo, una diferencia amplia apunta más a una sonda que deriva que "
              "a calor real"},
    "DESK_DIAG_GAP_CAUSE_RU": {
        "en": "the board can legitimately run hotter right after charge or heavy use",
        "fr": "la carte peut légitimement chauffer plus juste après une charge ou un usage intensif",
        "de": "die Platine kann direkt nach dem Laden oder starker Nutzung berechtigt wärmer sein",
        "es": "la placa puede estar legítimamente más caliente justo tras una carga o un uso intenso"},
    "DESK_DIAG_GAP_CHECK": {
        "en": "compare each probe to an external thermometer to find which one is off",
        "fr": "comparer chaque sonde à un thermomètre externe pour trouver laquelle dérive",
        "de": "jeden Fühler mit einem externen Thermometer vergleichen, um den abweichenden zu finden",
        "es": "comparar cada sonda con un termómetro externo para hallar cuál se desvía"},
    "DESK_DIAG_GAP_CHECK_RU": {
        "en": "let the pack rest to room temperature and re-read; if the gap remains, compare "
              "each probe to an external thermometer",
        "fr": "laisser le pack revenir à température ambiante et relire ; si l'écart persiste, "
              "comparer chaque sonde à un thermomètre externe",
        "de": "den Akku auf Raumtemperatur kommen lassen und erneut lesen; bleibt die "
              "Differenz, jeden Fühler mit einem externen Thermometer vergleichen",
        "es": "dejar que el pack vuelva a temperatura ambiente y releer; si la diferencia "
              "persiste, comparar cada sonda con un termómetro externo"},
    "DESK_DIAG_LATCHED_TITLE": {
        "en": "BMS has a latched fault flag", "fr": "Le BMS a un défaut latché",
        "de": "BMS hat einen gespeicherten Fehler", "es": "El BMS tiene un fallo memorizado"},
    "DESK_DIAG_LATCHED_OBS": {
        "en": "the BMS memorised a fault from a past event ({why})",
        "fr": "le BMS a mémorisé un défaut d'un événement passé ({why})",
        "de": "das BMS hat einen Fehler aus einem früheren Ereignis gespeichert ({why})",
        "es": "el BMS memorizó un fallo de un evento pasado ({why})"},
    "DESK_DIAG_LATCHED_CAUSE": {
        "en": "the BMS has latched this fault; clearing it won't hold, it re-asserts on charge",
        "fr": "le BMS a latché ce défaut; l'effacer ne tient pas, il revient à la charge",
        "de": "das BMS hat diesen Fehler verriegelt; loeschen haelt nicht, er kehrt beim Laden zurueck",
        "es": "el BMS ha bloqueado este fallo; borrarlo no aguanta, vuelve al cargar"},
    "DESK_DIAG_LATCHED_CHECK": {
        "en": "unlock, then charge and watch - re-locks in ~10 s = real fault (bench work); "
              "holds = stale flag",
        "fr": "débloquer, puis charger et observer - re-verrouille en ~10 s = vrai défaut "
              "(travail d'atelier) ; tient = drapeau obsolète",
        "de": "entsperren, dann laden und beobachten - sperrt in ~10 s erneut = echter Fehler "
              "(Werkstattarbeit); hält = veraltetes Flag",
        "es": "desbloquear, luego cargar y observar - se rebloquea en ~10 s = fallo real "
              "(trabajo de taller); aguanta = flag obsoleto"},
    "DESK_DIAG_WHY_OD": {
        "en": "likely left flat (over-discharge)",
        "fr": "probablement laissé à plat (sur-décharge)",
        "de": "wohl tiefentladen liegen gelassen", "es": "probablemente dejada descargada del todo"},
    "DESK_DIAG_WHY_OL": {
        "en": "likely run in overload", "fr": "probablement utilisé en surcharge",
        "de": "wohl in Überlast betrieben", "es": "probablemente usada en sobrecarga"},
    "DESK_DIAG_WHY_WEAR": {
        "en": "consistent with normal wear", "fr": "cohérent avec une usure normale",
        "de": "im Rahmen normalen Verschleißes", "es": "coherente con un desgaste normal"},
    "DESK_DIAG_WHY_UNCLEAR": {
        "en": "cause unclear - see the Health counters",
        "fr": "cause floue - voir les compteurs Santé",
        "de": "Ursache unklar - siehe Zustands-Zähler",
        "es": "causa incierta - ver los contadores de Salud"},
    "DESK_DIAG_NOFAULT_TITLE": {"en": "No lock, no fault", "fr": "Pas de verrou, pas de défaut",
                                "de": "Keine Sperre, kein Fehler", "es": "Sin bloqueo, sin fallo"},
    "DESK_DIAG_NOFAULT_OBS": {
        "en": "no charger lock, no hardware fault, no latched flag",
        "fr": "pas de verrou chargeur, pas de défaut matériel, pas de drapeau latché",
        "de": "keine Ladesperre, kein Hardware-Fehler, kein gespeichertes Flag",
        "es": "sin bloqueo de cargador, sin fallo de hardware, sin flag memorizado"},
    "DESK_DIAG_NOFAULT_CAUSE": {"en": "pack looks healthy", "fr": "le pack semble sain",
                                "de": "der Akku wirkt gesund", "es": "el pack parece sano"},
    "DESK_DIAG_NOFAULT_CHECK": {"en": "nothing to repair", "fr": "rien à réparer",
                                "de": "nichts zu reparieren", "es": "nada que reparar"},
    "DESK_DIAG_FALSELOCK_TITLE": {"en": "False lockout", "fr": "Faux verrouillage",
                                  "de": "Falsche Sperre", "es": "Bloqueo falso"},
    "DESK_DIAG_FALSELOCK_OBS": {
        "en": "charger lock set, but no hardware fault and no latched flag",
        "fr": "verrou chargeur posé, mais aucun défaut matériel ni drapeau latché",
        "de": "Ladesperre gesetzt, aber kein Hardware-Fehler und kein gespeichertes Flag",
        "es": "bloqueo de cargador puesto, pero sin fallo de hardware ni flag memorizado"},
    "DESK_DIAG_FALSELOCK_CAUSE": {
        "en": "a protection lockout (e.g. tripped over-discharge), not a real fault",
        "fr": "un verrouillage de protection (ex. sur-décharge déclenchée), pas un vrai défaut",
        "de": "eine Schutzsperre (z. B. ausgelöste Tiefentladung), kein echter Fehler",
        "es": "un bloqueo de protección (p. ej. sobredescarga activada), no un fallo real"},
    "DESK_DIAG_FALSELOCK_CHECK": {
        "en": "the unlock should clear it and hold - charge afterwards to confirm",
        "fr": "le déblocage devrait l'effacer et tenir - charger ensuite pour confirmer",
        "de": "das Entsperren sollte sie löschen und halten - danach laden zur Bestätigung",
        "es": "el desbloqueo debería borrarlo y aguantar - cargar después para confirmar"},
    "DESK_DIAG_WARM": {
        "en": "pack is warm ({hi:.0f} °C) - let it cool for a clean resting diagnosis",
        "fr": "pack chaud ({hi:.0f} °C) - le laisser refroidir pour un diagnostic au repos fiable",
        "de": "Akku ist warm ({hi:.0f} °C) - für eine saubere Ruhe-Diagnose abkühlen lassen",
        "es": "el pack está caliente ({hi:.0f} °C) - dejar enfriar para un diagnóstico en reposo fiable"},
    "DESK_DIAG_WARM_RU": {
        "en": "pack is warm ({hi:.0f} °C) - normal after charge or heavy use",
        "fr": "pack chaud ({hi:.0f} °C) - normal après une charge ou un usage intensif",
        "de": "Akku ist warm ({hi:.0f} °C) - normal nach Laden oder starker Nutzung",
        "es": "el pack está caliente ({hi:.0f} °C) - normal tras cargar o un uso intenso"},
    "DESK_DIAG_GATE_FIXHW": {"en": "Fix the hardware first.", "fr": "Réparer d'abord le matériel.",
                             "de": "Zuerst die Hardware reparieren.", "es": "Reparar primero el hardware."},
    "DESK_DIAG_GATE_UNLOCK": {
        "en": "An unlock should clear this lock.", "fr": "Un déblocage devrait lever ce verrou.",
        "de": "Ein Entsperren sollte diese Sperre lösen.",
        "es": "Un desbloqueo debería quitar este bloqueo."},
    "DESK_DIAG_GATE_NOTHING": {"en": "Nothing to repair.", "fr": "Rien à réparer.",
                               "de": "Nichts zu reparieren.", "es": "Nada que reparar."},

    # --- Repair wizard (checklist labels/values + Before/After reuse firmware S_* keys) ---
    "DESK_RPR_LOCKED": {"en": "locked", "fr": "verrouillé", "de": "gesperrt", "es": "bloqueado"},
    "DESK_RPR_UNLOCKED": {"en": "unlocked", "fr": "déverrouillé", "de": "entsperrt", "es": "desbloqueado"},
    "DESK_RPR_STEP_READ": {"en": "Read", "fr": "Lire", "de": "Lesen", "es": "Leer"},
    "DESK_RPR_STEP_CLASSIFY": {"en": "Classify", "fr": "Classer", "de": "Einordnen", "es": "Clasificar"},
    "DESK_RPR_STEP_UNLOCK": {"en": "Unlock", "fr": "Débloquer", "de": "Entsperren", "es": "Desbloquear"},
    "DESK_RPR_STEP_CONFIRM": {"en": "Confirm", "fr": "Confirmer", "de": "Bestätigen", "es": "Confirmar"},
    "DESK_RPR_S1_TITLE": {"en": "Step 1 — Read the pack", "fr": "Étape 1 — Lire le pack",
                          "de": "Schritt 1 — Akku lesen", "es": "Paso 1 — Leer el pack"},
    "DESK_RPR_S1_DESC": {
        "en": "Take a baseline reading before any repair.",
        "fr": "Prendre une lecture de référence avant toute réparation.",
        "de": "Vor jeder Reparatur eine Basismessung nehmen.",
        "es": "Tomar una lectura de referencia antes de cualquier reparación."},
    "DESK_RPR_BASELINE": {"en": "Baseline read: %s", "fr": "Lecture de référence : %s",
                          "de": "Basismessung: %s", "es": "Lectura de referencia: %s"},
    "DESK_RPR_S2_TITLE": {"en": "Step 2 - Classify", "fr": "Étape 2 - Classer",
                          "de": "Schritt 2 - Einordnen", "es": "Paso 2 - Clasificar"},
    "DESK_RPR_RECENTLY_USED": {
        "en": "Pack was just charged or used (affects temperature)",
        "fr": "Pack juste chargé ou utilisé (influe sur la température)",
        "de": "Akku wurde gerade geladen oder benutzt (beeinflusst die Temperatur)",
        "es": "El pack se acaba de cargar o usar (afecta a la temperatura)"},
    "DESK_RPR_OBSERVATION": {"en": "Observation", "fr": "Observation",
                             "de": "Beobachtung", "es": "Observación"},
    "DESK_RPR_CAUSE": {"en": "Likely cause", "fr": "Cause probable",
                       "de": "Mögl. Ursache", "es": "Causa probable"},
    "DESK_RPR_CHECK": {"en": "Check", "fr": "Vérification", "de": "Prüfung", "es": "Comprobación"},
    "DESK_RPR_OVERRIDE": {
        "en": "Override: unlock anyway (fix the hardware first)",
        "fr": "Forcer : débloquer quand même (réparer d'abord le matériel)",
        "de": "Erzwingen: trotzdem entsperren (zuerst die Hardware reparieren)",
        "es": "Forzar: desbloquear igualmente (reparar primero el hardware)"},
    "DESK_RPR_PROCEED": {"en": "Proceed to unlock", "fr": "Passer au déblocage",
                         "de": "Weiter zum Entsperren", "es": "Pasar al desbloqueo"},
    "DESK_RPR_START_OVER": {"en": "Start over", "fr": "Recommencer",
                            "de": "Neu starten", "es": "Empezar de nuevo"},
    "DESK_RPR_S3_TITLE": {"en": "Step 3 — Unlock / repair", "fr": "Étape 3 — Débloquer / réparer",
                          "de": "Schritt 3 — Entsperren / reparieren", "es": "Paso 3 — Desbloquear / reparar"},
    "DESK_RPR_S3_DESC": {
        "en": "Clears the charger-lock nybble and recomputes the checksums, then commits and "
              "resets errors. The failure code is never touched. The arm is accepted once per "
              "insertion — if it fails, remove and reinsert the pack before retrying.",
        "fr": "Efface le quartet de verrou chargeur et recalcule les sommes de contrôle, puis "
              "valide et réinitialise les erreurs. Le code de défaut n'est jamais touché. "
              "L'armement n'est accepté qu'une fois par insertion — en cas d'échec, retirer et "
              "réinsérer le pack avant de réessayer.",
        "de": "Löscht das Ladesperre-Nibble und berechnet die Prüfsummen neu, bestätigt dann "
              "und setzt Fehler zurück. Der Fehlercode wird nie angetastet. Die Scharfschaltung "
              "wird einmal pro Einsetzen akzeptiert — schlägt sie fehl, den Akku entnehmen und "
              "neu einsetzen, bevor erneut versucht wird.",
        "es": "Borra el nibble de bloqueo del cargador y recalcula las sumas de comprobación, "
              "luego confirma y reinicia los errores. El código de fallo nunca se toca. El "
              "armado se acepta una vez por inserción — si falla, retirar y reinsertar el pack "
              "antes de reintentar."},
    "DESK_RPR_UNLOCK_NOW": {"en": "Unlock now", "fr": "Débloquer maintenant",
                            "de": "Jetzt entsperren", "es": "Desbloquear ahora"},
    "DESK_RPR_UNLOCKING": {"en": "Unlocking…", "fr": "Déblocage…",
                           "de": "Entsperre…", "es": "Desbloqueando…"},
    "DESK_RPR_WRITING": {
        "en": "Writing repaired frame and resetting…",
        "fr": "Écriture de la trame réparée et réinitialisation…",
        "de": "Schreibe reparierte Frame und setze zurück…",
        "es": "Escribiendo la trama reparada y reiniciando…"},
    "DESK_RPR_UNLOCK_DONE": {"en": "Unlock done. Re-read: %s", "fr": "Déblocage effectué. Relecture : %s",
                             "de": "Entsperren fertig. Erneut gelesen: %s", "es": "Desbloqueo hecho. Relectura: %s"},
    "DESK_RPR_UNLOCK_FAILED": {"en": "Unlock failed: %s", "fr": "Échec du déblocage : %s",
                               "de": "Entsperren fehlgeschlagen: %s", "es": "Fallo al desbloquear: %s"},
    "DESK_RPR_S4_TITLE": {"en": "Step 4 - Confirm", "fr": "Étape 4 - Confirmer",
                          "de": "Schritt 4 - Bestätigen", "es": "Paso 4 - Confirmar"},
    "DESK_RPR_RES_HEALTHY": {
        "en": "Unlocked - the pack now reads healthy.",
        "fr": "Débloqué - le pack lit maintenant sain.",
        "de": "Entsperrt - der Akku liest jetzt gesund.",
        "es": "Desbloqueado - el pack ahora lee sano."},
    "DESK_RPR_RES_REALFAULT": {
        "en": "Charger lock cleared, but a hardware fault remains - the unlock cannot fix that.",
        "fr": "Verrou chargeur effacé, mais un défaut matériel persiste - le déblocage ne peut "
              "pas le corriger.",
        "de": "Ladesperre gelöscht, aber ein Hardware-Fehler bleibt - das Entsperren kann das "
              "nicht beheben.",
        "es": "Bloqueo del cargador borrado, pero queda un fallo de hardware - el desbloqueo no "
              "puede arreglarlo."},
    "DESK_RPR_RES_SUSPECT": {
        "en": "Lock cleared, but a latched/soft fault remains - likely to re-lock on charge.",
        "fr": "Verrou effacé, mais un défaut latché/léger persiste - risque de re-verrouillage "
              "à la charge.",
        "de": "Sperre gelöscht, aber ein gespeicherter/weicher Fehler bleibt - sperrt beim "
              "Laden wahrscheinlich erneut.",
        "es": "Bloqueo borrado, pero queda un fallo memorizado/leve - probable rebloqueo al cargar."},
    "DESK_RPR_RES_STILLLOCKED": {
        "en": "Still locked after unlock - the BMS re-locked it.",
        "fr": "Toujours verrouillé après déblocage - le BMS l'a re-verrouillé.",
        "de": "Nach dem Entsperren weiterhin gesperrt - das BMS hat erneut gesperrt.",
        "es": "Sigue bloqueado tras el desbloqueo - el BMS lo rebloqueó."},
    "DESK_RPR_RES_UNLOCKED": {"en": "Unlocked.", "fr": "Débloqué.",
                              "de": "Entsperrt.", "es": "Desbloqueado."},
    "DESK_RPR_HOLD_Q": {
        "en": "Did it hold after charging? (optional)",
        "fr": "A-t-il tenu après charge ? (facultatif)",
        "de": "Hat es nach dem Laden gehalten? (optional)",
        "es": "¿Aguantó tras cargar? (opcional)"},
    "DESK_RPR_HELD": {"en": "held", "fr": "tenu", "de": "gehalten", "es": "aguantó"},
    "DESK_RPR_RELOCKED": {"en": "re-locked", "fr": "re-verrouillé",
                          "de": "erneut gesperrt", "es": "rebloqueado"},
    "DESK_RPR_UNKNOWN": {"en": "unknown", "fr": "inconnu", "de": "unbekannt", "es": "desconocido"},
    "DESK_RPR_NOTES": {"en": "Notes (optional)…", "fr": "Notes (facultatif)…",
                       "de": "Notizen (optional)…", "es": "Notas (opcional)…"},
    "DESK_RPR_SAVE_SESSION": {
        "en": "Save repair session", "fr": "Enregistrer la session de réparation",
        "de": "Reparatursitzung speichern", "es": "Guardar sesión de reparación"},
    "DESK_RPR_SAVED": {
        "en": "Repair session saved to history.",
        "fr": "Session de réparation enregistrée dans l'historique.",
        "de": "Reparatursitzung im Verlauf gespeichert.",
        "es": "Sesión de reparación guardada en el historial."},

    # --- Connect screen ---
    "DESK_CONN_TITLE": {
        "en": "CONNECT TO A POCKETOBI BRIDGE", "fr": "SE CONNECTER À UN PONT POCKETOBI",
        "de": "MIT EINER POCKETOBI-BRÜCKE VERBINDEN", "es": "CONECTAR A UN PUENTE POCKETOBI"},
    "DESK_CONN_PORT": {"en": "Serial port", "fr": "Port série",
                       "de": "Serieller Port", "es": "Puerto serie"},
    "DESK_CONN_CONNECTING": {"en": "Connecting…", "fr": "Connexion…",
                             "de": "Verbinde…", "es": "Conectando…"},
    "DESK_CONN_DISCONNECT": {"en": "Disconnect", "fr": "Déconnecter",
                             "de": "Trennen", "es": "Desconectar"},
    "DESK_CONN_NOT_CONNECTED": {"en": "Not connected.", "fr": "Non connecté.",
                                "de": "Nicht verbunden.", "es": "Sin conexión."},
    "DESK_CONN_PICK_PORT": {
        "en": "Pick a valid serial port first.", "fr": "Choisir d'abord un port série valide.",
        "de": "Zuerst einen gültigen seriellen Port wählen.",
        "es": "Elegir primero un puerto serie válido."},
    "DESK_CONN_OPENING": {
        "en": "Opening %s and waiting for the bridge…",
        "fr": "Ouverture de %s et attente du pont…",
        "de": "Öffne %s und warte auf die Brücke…",
        "es": "Abriendo %s y esperando el puente…"},
    "DESK_CONN_TIP": {
        "en": "Tip: on the PocketOBI, open Tools › PC bridge first (or turn on Settings › "
              "PC bridge at boot).",
        "fr": "Astuce : sur le PocketOBI, ouvrir d'abord Outils › Pont PC (ou activer "
              "Réglages › Pont PC au démarrage).",
        "de": "Tipp: am PocketOBI zuerst Werkzeuge › PC-Brücke öffnen (oder Einstellungen › "
              "PC-Brücke beim Start aktivieren).",
        "es": "Consejo: en el PocketOBI, abrir primero Herramientas › Puente PC (o activar "
              "Ajustes › Puente PC al inicio)."},
    "DESK_CONN_DEMO_TITLE": {
        "en": "NO HARDWARE? TRY A DEMO PACK", "fr": "PAS DE MATÉRIEL ? ESSAYER UN PACK DÉMO",
        "de": "KEINE HARDWARE? EINEN DEMO-AKKU PROBIEREN", "es": "¿SIN HARDWARE? PROBAR UN PACK DEMO"},
    "DESK_CONN_USE_DEMO": {"en": "Use demo bridge", "fr": "Utiliser le pont démo",
                           "de": "Demo-Brücke verwenden", "es": "Usar el puente demo"},
    "DESK_CONN_CONNECTED": {"en": "Connected — bridge active.", "fr": "Connecté — pont actif.",
                            "de": "Verbunden — Brücke aktiv.", "es": "Conectado — puente activo."},
    "DESK_CONN_CONNECTED_FW": {
        "en": "Connected — firmware %s, bridge active.",
        "fr": "Connecté — firmware %s, pont actif.",
        "de": "Verbunden — Firmware %s, Brücke aktiv.",
        "es": "Conectado — firmware %s, puente activo."},
    "DESK_CONN_WARN_LEGACY": {
        "en": "  ⚠ Older firmware (pre-contract): some readings and verdicts may be missing or "
              "differ from this app. Update the PocketOBI firmware for full parity.",
        "fr": "  ⚠ Firmware ancien (pré-contrat) : certaines lectures et verdicts peuvent "
              "manquer ou différer de cette app. Mettre à jour le firmware PocketOBI pour une "
              "parité complète.",
        "de": "  ⚠ Ältere Firmware (vor Vertrag): einige Messwerte und Urteile können fehlen "
              "oder von dieser App abweichen. Firmware des PocketOBI für volle Parität aktualisieren.",
        "es": "  ⚠ Firmware antiguo (pre-contrato): algunas lecturas y veredictos pueden faltar "
              "o diferir de esta app. Actualizar el firmware del PocketOBI para plena paridad."},
    "DESK_CONN_WARN_MISMATCH": {
        "en": "  ⚠ Firmware protocol v%s ≠ app v%s: verdicts may diverge. Update whichever "
              "side is older.",
        "fr": "  ⚠ Protocole firmware v%s ≠ app v%s : les verdicts peuvent diverger. Mettre à "
              "jour le côté le plus ancien.",
        "de": "  ⚠ Firmware-Protokoll v%s ≠ App v%s: Urteile können abweichen. Die ältere Seite "
              "aktualisieren.",
        "es": "  ⚠ Protocolo de firmware v%s ≠ app v%s: los veredictos pueden diferir. "
              "Actualizar el lado más antiguo."},
    "DESK_CONN_ERR_OPEN": {
        "en": "Cannot open %s — is another program using it (Arduino IDE serial monitor, etc.)?",
        "fr": "Impossible d'ouvrir %s — un autre programme l'utilise-t-il (moniteur série "
              "Arduino IDE, etc.) ?",
        "de": "%s kann nicht geöffnet werden — benutzt es ein anderes Programm "
              "(Arduino-IDE-Seriellmonitor usw.)?",
        "es": "No se puede abrir %s — ¿lo usa otro programa (monitor serie del IDE de Arduino, etc.)?"},
    "DESK_CONN_ERR_NORESP": {
        "en": "No response from the bridge. On the PocketOBI, open Tools › PC bridge (or enable "
              "it at boot), then Connect again.",
        "fr": "Pas de réponse du pont. Sur le PocketOBI, ouvrir Outils › Pont PC (ou l'activer "
              "au démarrage), puis se reconnecter.",
        "de": "Keine Antwort von der Brücke. Am PocketOBI Werkzeuge › PC-Brücke öffnen (oder "
              "beim Start aktivieren), dann erneut verbinden.",
        "es": "Sin respuesta del puente. En el PocketOBI, abrir Herramientas › Puente PC (o "
              "activarlo al inicio), luego conectar de nuevo."},
    "DESK_CONN_DEMO_ACTIVE": {"en": "Demo bridge active: %s.", "fr": "Pont démo actif : %s.",
                              "de": "Demo-Brücke aktiv: %s.", "es": "Puente demo activo: %s."},
    "DESK_CONN_DISCONNECTED": {"en": "Disconnected.", "fr": "Déconnecté.",
                               "de": "Getrennt.", "es": "Desconectado."},
    "DESK_CONN_NO_PORTS": {"en": "(no ports found)", "fr": "(aucun port trouvé)",
                           "de": "(keine Ports gefunden)", "es": "(ningún puerto encontrado)"},

    # --- Settings screen ---
    "DESK_SET_DISPLAY": {"en": "Display", "fr": "Affichage", "de": "Anzeige", "es": "Pantalla"},
    "DESK_SET_CONNECTION": {"en": "Connection", "fr": "Connexion", "de": "Verbindung", "es": "Conexión"},
    "DESK_SET_DATA": {"en": "Data", "fr": "Données", "de": "Daten", "es": "Datos"},
    "DESK_SET_APPEARANCE": {"en": "Appearance", "fr": "Apparence",
                            "de": "Erscheinungsbild", "es": "Apariencia"},
    "DESK_SET_TEMP_UNIT": {"en": "Temperature unit", "fr": "Unité de température",
                           "de": "Temperatureinheit", "es": "Unidad de temperatura"},
    "DESK_SET_CSV_COLS": {"en": "CSV export columns", "fr": "Colonnes de l'export CSV",
                          "de": "CSV-Exportspalten", "es": "Columnas del export CSV"},
    "DESK_SET_DEFAULT_PORT": {"en": "Default serial port", "fr": "Port série par défaut",
                              "de": "Standard-Seriellport", "es": "Puerto serie por defecto"},
    "DESK_SET_DARK": {"en": "Dark", "fr": "Sombre", "de": "Dunkel", "es": "Oscuro"},
    "DESK_SET_LIGHT": {"en": "Light", "fr": "Clair", "de": "Hell", "es": "Claro"},
    "DESK_SET_CSV_MAKITA": {"en": "Makita-compatible", "fr": "Compatible Makita",
                            "de": "Makita-kompatibel", "es": "Compatible con Makita"},
    "DESK_SET_CSV_FULL": {"en": "Full (+ PocketOBI extras)", "fr": "Complet (+ extras PocketOBI)",
                          "de": "Vollständig (+ PocketOBI-Extras)", "es": "Completo (+ extras PocketOBI)"},
    "DESK_SET_PORT_PH": {"en": "e.g. COM4 (blank = ask)", "fr": "ex. COM4 (vide = demander)",
                         "de": "z. B. COM4 (leer = fragen)", "es": "p. ej. COM4 (vacío = preguntar)"},
    "DESK_SET_DB_FILE": {"en": "Database file:  %s", "fr": "Fichier base de données :  %s",
                         "de": "Datenbankdatei:  %s", "es": "Archivo de base de datos:  %s"},
    "DESK_SET_CLEAR": {"en": "Clear local history…", "fr": "Effacer l'historique local…",
                       "de": "Lokalen Verlauf löschen…", "es": "Borrar el historial local…"},
    "DESK_SET_SAVE": {"en": "Save settings", "fr": "Enregistrer les réglages",
                      "de": "Einstellungen speichern", "es": "Guardar ajustes"},
    "DESK_SET_SAVED": {"en": "Saved.", "fr": "Enregistré.", "de": "Gespeichert.", "es": "Guardado."},
    "DESK_SET_CLEAR_TITLE": {"en": "Clear local history", "fr": "Effacer l'historique local",
                             "de": "Lokalen Verlauf löschen", "es": "Borrar el historial local"},
    "DESK_SET_CLEAR_MSG": {
        "en": "Delete ALL local readings, repair sessions\nand battery records? This cannot "
              "be undone.",
        "fr": "Supprimer TOUTES les lectures locales, sessions\nde réparation et fiches "
              "batterie ? Action irréversible.",
        "de": "ALLE lokalen Messungen, Reparatursitzungen\nund Akku-Einträge löschen? Nicht "
              "umkehrbar.",
        "es": "¿Eliminar TODAS las lecturas locales, sesiones\nde reparación y fichas de "
              "batería? Es irreversible."},
    "DESK_SET_CLEAR_YES": {"en": "Delete everything", "fr": "Tout supprimer",
                           "de": "Alles löschen", "es": "Eliminar todo"},
    "DESK_SET_CANCEL": {"en": "Cancel", "fr": "Annuler", "de": "Abbrechen", "es": "Cancelar"},
    "DESK_SET_CLEARED": {"en": "Local history cleared.", "fr": "Historique local effacé.",
                         "de": "Lokaler Verlauf gelöscht.", "es": "Historial local borrado."},

    # --- Connection status chip (app.py) ---
    "DESK_STATUS_NOT_CONNECTED": {"en": "not connected", "fr": "non connecté",
                                  "de": "nicht verbunden", "es": "sin conexión"},
    "DESK_STATUS_DISCONNECTED": {"en": "disconnected", "fr": "déconnecté",
                                 "de": "getrennt", "es": "desconectado"},

    # --- Shared component defaults ---
    "DESK_NO_READING": {"en": "No reading", "fr": "Aucune lecture",
                        "de": "Keine Messung", "es": "Sin lectura"},
    "DESK_NO_READINGS": {"en": "no readings", "fr": "aucune lecture",
                         "de": "keine Messungen", "es": "sin lecturas"},

    # --- Batteries / History screen (metric/status logical KEYS stay stable; only
    # the display labels below are translated, mapped back to keys in the code) ---
    "DESK_HIST_SEARCH_PH": {
        "en": "Search S/N, model, alias, owner…",
        "fr": "Rechercher S/N, modèle, alias, propriétaire…",
        "de": "S/N, Modell, Alias, Besitzer suchen…",
        "es": "Buscar S/N, modelo, alias, propietario…"},
    "DESK_HIST_LOAD_DEMO": {"en": "Load demo data", "fr": "Charger les données démo",
                            "de": "Demodaten laden", "es": "Cargar datos demo"},
    "DESK_HIST_CLEAR_DEMO": {"en": "Clear demo data", "fr": "Effacer les données démo",
                             "de": "Demodaten löschen", "es": "Borrar datos demo"},
    "DESK_HIST_EXPORT_CSV": {"en": "Export CSV", "fr": "Exporter CSV",
                             "de": "CSV exportieren", "es": "Exportar CSV"},
    "DESK_HIST_EXPORT_REPORT": {"en": "Export report (JSON)", "fr": "Exporter le rapport (JSON)",
                                "de": "Bericht exportieren (JSON)", "es": "Exportar informe (JSON)"},
    "DESK_HIST_NO_BATTERIES": {
        "en": "No batteries yet.\nRead a pack, or load demo data.",
        "fr": "Aucune batterie.\nLire un pack, ou charger les données démo.",
        "de": "Noch keine Akkus.\nEinen Akku lesen oder Demodaten laden.",
        "es": "Aún no hay baterías.\nLeer un pack o cargar datos demo."},
    "DESK_HIST_SELECT_BATTERY": {"en": "Select a battery", "fr": "Sélectionner une batterie",
                                 "de": "Einen Akku wählen", "es": "Seleccionar una batería"},
    "DESK_HIST_EDIT_IDENTITY": {"en": "Edit identity", "fr": "Modifier l'identité",
                                "de": "Identität bearbeiten", "es": "Editar identidad"},
    "DESK_HIST_COMPARE": {"en": "Compare readings", "fr": "Comparer les lectures",
                          "de": "Messungen vergleichen", "es": "Comparar lecturas"},
    "DESK_HIST_HEALTH_CARD": {"en": "Health card", "fr": "Fiche de santé",
                              "de": "Zustandskarte", "es": "Ficha de salud"},
    "DESK_HIST_OWNER": {"en": "Owner", "fr": "Propriétaire", "de": "Besitzer", "es": "Propietario"},
    "DESK_HIST_STATUS": {"en": "Status", "fr": "Statut", "de": "Status", "es": "Estado"},
    "DESK_HIST_READINGS": {"en": "Readings", "fr": "Lectures", "de": "Messungen", "es": "Lecturas"},
    "DESK_HIST_REPAIRS": {"en": "Repairs", "fr": "Réparations", "de": "Reparaturen", "es": "Reparaciones"},
    "DESK_HIST_FIRST_SEEN": {"en": "First seen", "fr": "Première vue",
                             "de": "Erstmals", "es": "Primera vez"},
    "DESK_HIST_LAST_SEEN": {"en": "Last seen", "fr": "Dernière vue",
                            "de": "Zuletzt", "es": "Última vez"},
    "DESK_HIST_VERDICT_TIME": {"en": "Verdict over time", "fr": "Verdict dans le temps",
                               "de": "Urteil im Zeitverlauf", "es": "Veredicto en el tiempo"},
    "DESK_HIST_TREND": {"en": "Trend", "fr": "Tendance", "de": "Trend", "es": "Tendencia"},
    "DESK_HIST_NO_REPAIRS": {
        "en": "No repair sessions.", "fr": "Aucune session de réparation.",
        "de": "Keine Reparatursitzungen.", "es": "Sin sesiones de reparación."},
    "DESK_HIST_ALL_STATUS": {"en": "All status", "fr": "Tous statuts",
                             "de": "Alle Status", "es": "Todos los estados"},
    "DESK_HIST_ST_TODIAG": {"en": "To diagnose", "fr": "À diagnostiquer",
                            "de": "Zu diagnostizieren", "es": "Por diagnosticar"},
    "DESK_HIST_ST_REPAIRED": {"en": "Repaired", "fr": "Réparé", "de": "Repariert", "es": "Reparado"},
    "DESK_HIST_ST_PARTS": {"en": "Parts", "fr": "Pièces", "de": "Teile", "es": "Piezas"},
    "DESK_HIST_ST_SCRAP": {"en": "Scrap", "fr": "Rebut", "de": "Schrott", "es": "Desecho"},
    "DESK_HIST_M_PACKV": {"en": "Pack V", "fr": "Tension", "de": "Spannung", "es": "Tensión"},
    "DESK_HIST_M_CELLSPREAD": {"en": "Cell spread", "fr": "Écart cell.",
                               "de": "Zell-Diff.", "es": "Dif. celda"},
    "DESK_HIST_M_TEMPSPREAD": {"en": "Temp spread", "fr": "Écart temp.",
                               "de": "Temp-Diff.", "es": "Dif. temp"},
    "DESK_HIST_M_CYCLES": {"en": "Cycles", "fr": "Cycles", "de": "Zyklen", "es": "Ciclos"},
    "DESK_HIST_EDIT_TITLE": {"en": "Edit identity", "fr": "Modifier l'identité",
                             "de": "Identität bearbeiten", "es": "Editar identidad"},
    "DESK_HIST_F_ALIAS": {"en": "Alias / name", "fr": "Alias / nom",
                          "de": "Alias / Name", "es": "Alias / nombre"},
    "DESK_HIST_F_OWNER": {"en": "Owner (mine / customer)", "fr": "Propriétaire (moi / client)",
                          "de": "Besitzer (ich / Kunde)", "es": "Propietario (yo / cliente)"},
    "DESK_HIST_F_TAGS": {
        "en": "Tags (comma-separated)", "fr": "Étiquettes (séparées par des virgules)",
        "de": "Tags (kommagetrennt)", "es": "Etiquetas (separadas por comas)"},
    "DESK_HIST_SAVE": {"en": "Save", "fr": "Enregistrer", "de": "Speichern", "es": "Guardar"},
    "DESK_HIST_UNLOCK_ACTION": {"en": "unlock", "fr": "déblocage",
                                "de": "Entsperren", "es": "desbloqueo"},
    "DESK_HIST_HEALTH_EXPORTED": {
        "en": "Health card exported — opening…", "fr": "Fiche de santé exportée — ouverture…",
        "de": "Zustandskarte exportiert — öffne…", "es": "Ficha de salud exportada — abriendo…"},
    "DESK_HIST_CSV_EXPORTED": {
        "en": "Exported %d row(s) to CSV.", "fr": "%d ligne(s) exportée(s) en CSV.",
        "de": "%d Zeile(n) als CSV exportiert.", "es": "%d fila(s) exportada(s) a CSV."},
    "DESK_HIST_REPORT_EXPORTED": {
        "en": "Exported %d reading(s) — paste it where you choose.",
        "fr": "%d lecture(s) exportée(s) — à coller où vous voulez.",
        "de": "%d Messung(en) exportiert — beliebig einfügen.",
        "es": "%d lectura(s) exportada(s) — pégalo donde quieras."},
    "DESK_HIST_CMP_TITLE": {"en": "Compare readings", "fr": "Comparer les lectures",
                            "de": "Messungen vergleichen", "es": "Comparar lecturas"},
    "DESK_HIST_ROW_VERDICT": {"en": "Verdict", "fr": "Verdict", "de": "Urteil", "es": "Veredicto"},
    "DESK_HIST_ROW_PACKV": {"en": "Pack V", "fr": "Tension pack",
                            "de": "Pack-Spannung", "es": "Tensión pack"},
    "DESK_HIST_ROW_CELLSPREAD": {"en": "Cell spread", "fr": "Écart cellules",
                                 "de": "Zell-Differenz", "es": "Dif. celdas"},
    "DESK_HIST_ROW_TEMP": {"en": "Temp cell/board", "fr": "Temp cellule/carte",
                           "de": "Temp Zelle/Platine", "es": "Temp celda/placa"},
    "DESK_HIST_ROW_LOCKED": {"en": "Locked", "fr": "Verrouillé", "de": "Gesperrt", "es": "Bloqueado"},
    "DESK_HIST_ROW_CHGLOCK": {"en": "Charger lock", "fr": "Verrou chargeur",
                              "de": "Ladesperre", "es": "Bloqueo cargador"},
    "DESK_HIST_NO": {"en": "no", "fr": "non", "de": "nein", "es": "no"},
}
