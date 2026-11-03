LANGUAGES = ("ru", "en")
DEFAULT_LANG = "ru"

STRINGS = {
    "title_session": {"ru": "Сессия {date}", "en": "Session {date}"},
    "title_player": {"ru": "👤 {name} · 🕐 {span}", "en": "👤 {name} · 🕐 {span}"},
    "title_player_edit": {"ru": "✏️ Редактирование игрока {name}",
                          "en": "✏️ Editing player {name}"},
    "title_settings": {"ru": "⚙️ Настройки", "en": "⚙️ Settings"},
    "title_help": {"ru": "❓ FAQ", "en": "❓ FAQ"},
    "title_currency": {"ru": "💱 Валюта", "en": "💱 Currency"},
    "title_pay": {"ru": "💰 {name} · {money}", "en": "💰 {name} · {money}"},
    "title_time": {"ru": "🕐 {name} · {span}", "en": "🕐 {name} · {span}"},

    "hint_debt": {"ru": "Кому должен {name}? Выберите имя и пришлите сумму — "
                        "или сразу ответьте «@маша 20 такси»",
                  "en": "Who does {name} owe? Pick a name and send the amount — "
                        "or reply with “@masha 20 taxi” in one go"},
    "txt_send_debt": {"ru": "Ответьте на сообщение бота суммой, например «20 такси»",
                      "en": "Reply to the bot's message with an amount, e.g. “20 taxi”"},
    "title_debt": {"ru": "💸 {name} — долги", "en": "💸 {name} — debts"},
    "hint_player": {"ru": "Выберите, что изменить для {name}",
                    "en": "Choose what to change for {name}"},
    "hint_time": {"ru": "Укажите время игры для {name} — кнопками или ответом "
                        "на это сообщение",
                  "en": "Set the playing time for {name} — with the buttons, or by "
                        "replying to this message"},
    "hint_pay": {"ru": "Сколько заплатил {name}? Напишите ответом на это сообщение.",
                 "en": "How much did {name} pay? Send it as a reply to this message."},

    "btn_settle": {"ru": "✅ Рассчитать", "en": "✅ Calculate"},
    "btn_settle_waiting": {"ru": "⏳ Рассчитать (ждём данные всех игроков)",
                           "en": "⏳ Calculate (awaiting all player data)"},
    "btn_settings": {"ru": "⚙️ Настройки", "en": "⚙️ Settings"},
    "btn_add_player": {"ru": "＋ Игрок", "en": "＋ Player"},
    "btn_unlock": {"ru": "✏️ Исправить", "en": "✏️ Fix"},
    "btn_rename": {"ru": "✏️ Имя", "en": "✏️ Name"},
    "btn_cancel_edit": {"ru": "↩️ Отмена", "en": "↩️ Cancel"},
    "btn_recalc": {"ru": "✅ Пересчитать", "en": "✅ Recalculate"},
    "btn_recalc_waiting": {"ru": "⏳ Пересчитать (ждём данные)",
                           "en": "⏳ Recalculate (awaiting data)"},
    "btn_yes": {"ru": "Да", "en": "Yes"},
    "btn_no": {"ru": "Отмена", "en": "Cancel"},
    "btn_help": {"ru": "❓ FAQ", "en": "❓ FAQ"},
    "btn_export": {"ru": "⬇️ Скачать таблицу", "en": "⬇️ Download table"},
    "btn_currency": {"ru": "💱 Валюта", "en": "💱 Currency"},
    "btn_debt": {"ru": "Прошлый долг", "en": "Past debt"},
    "txt_debt_generic": {"ru": "долг", "en": "debt"},
    "col_name": {"ru": "имя", "en": "name"},
    "col_from": {"ru": "начал играть", "en": "started"},
    "col_to": {"ru": "закончил играть", "en": "finished"},
    "col_paid": {"ru": "внёс", "en": "paid"},
    "col_share": {"ru": "доля", "en": "share"},
    "col_balance": {"ru": "баланс", "en": "balance"},
    "btn_back": {"ru": "‹ Назад", "en": "‹ Back"},
    "btn_from": {"ru": "✏ С {time}", "en": "✏ From {time}"},
    "btn_to": {"ru": "✏ До {time}", "en": "✏ To {time}"},
    "btn_remove": {"ru": "🗑 Убрать", "en": "🗑 Remove"},
    "btn_time": {"ru": "🕐 Время", "en": "🕐 Time"},
    "btn_span_add": {"ru": "＋ Окно", "en": "＋ Window"},
    "btn_span_del": {"ru": "🗑 Убрать окно", "en": "🗑 Remove window"},
    "btn_paid": {"ru": "💰 Взнос", "en": "💰 Paid"},
    "btn_clear": {"ru": "Очистить", "en": "Clear"},
    "btn_solo_on": {"ru": "☑ Платит отдельно", "en": "☑ Settles separately"},
    "btn_solo_off": {"ru": "☐ Платит отдельно", "en": "☐ Settles separately"},
    "btn_style_plain": {"ru": "Моно", "en": "Mono"},
    "btn_style_block": {"ru": "Блок", "en": "Block"},
    "lbl_style": {"ru": "Таблицы", "en": "Tables"},
    "btn_round_exact": {"ru": "Точно", "en": "Exact"},
    "btn_round_half": {"ru": "До 0.5", "en": "To 0.5"},
    "btn_round_whole": {"ru": "Целые", "en": "Whole"},
    "btn_lang_ru": {"ru": "🇷🇺 RU", "en": "🇷🇺 RU"},
    "btn_lang_en": {"ru": "🇬🇧 EN", "en": "🇬🇧 EN"},

    "lbl_players": {"ru": "👥 ИГРОКИ", "en": "👥 PLAYERS"},
    "lbl_settle": {"ru": "💳 ПЕРЕВОДЫ", "en": "💳 TRANSFERS"},
    "lbl_subtotal": {"ru": "📊 ИТОГО", "en": "📊 TOTALS"},
    "lbl_debts": {"ru": "💸 ДОЛГИ", "en": "💸 DEBTS"},
    "lbl_owed": {"ru": "💰 К ОПЛАТЕ", "en": "💰 TO PAY"},
    "txt_own_share": {"ru": "Каждый платит свою долю сам — суммы посчитаны "
                            "по цене за час.",
                      "en": "Everyone pays their own share — amounts come from "
                            "the hourly price."},
    "txt_settled": {"ru": "рассчитана", "en": "settled"},
    "txt_stale": {"ru": "⚠️ {head} — исправлена", "en": "⚠️ {head} — corrected"},
    "txt_status_open": {"ru": "открыта {name}", "en": "opened by {name}"},
    "txt_status_open_plain": {"ru": "открыта", "en": "open"},
    "txt_status_closed": {"ru": "закрыта {name}", "en": "closed by {name}"},
    "txt_status_closed_plain": {"ru": "закрыта", "en": "closed"},
    "txt_status_editing": {"ru": "редактируется {name}", "en": "editing by {name}"},
    "txt_locked": {"ru": "Сессия рассчитана — нажмите «Исправить»",
                   "en": "Session is calculated — tap “Fix”"},
    "txt_solo_note": {"ru": "{names} — вне переводов. Разница разошлась поровну между остальными.",
                      "en": "{names} — outside transfers. The difference is spread evenly across the rest."},
    "txt_solo_over": {"ru": "переплата {money}", "en": "overpaid {money}"},
    "txt_solo_under": {"ru": "недоплата {money}", "en": "underpaid {money}"},
    "txt_solo_even": {"ru": "в расчёте", "en": "square"},
    "lbl_rate": {"ru": "Цена за час", "en": "Price per hour"},
    "txt_tap_price": {"ru": "Нажмите на цену и ответьте на это сообщение своей.",
                      "en": "Tap the price, then reply to this message with your own."},
    "lbl_language": {"ru": "Язык", "en": "Language"},
    "lbl_rounding": {"ru": "Округление", "en": "Rounding"},

    "txt_style_plain": {"ru": "Без рамки, сливается с сообщением.",
                        "en": "No frame, blends into the message."},
    "txt_style_block": {"ru": "В рамке с подсветкой, отдельно от текста.",
                        "en": "Framed and tinted, set apart from the text."},
    "txt_round_exact": {"ru": "Точные суммы, до копеек.",
                        "en": "Exact amounts, down to the cent."},
    "txt_round_half": {"ru": "Кратно 0.5 — итог всё равно сходится.",
                       "en": "Multiples of 0.5; the total still adds up."},
    "txt_round_whole": {"ru": "Целые суммы, итог всё равно сходится.",
                        "en": "Whole amounts; the total still adds up."},
    "txt_rate_line": {"ru": "{rate} {cur}/час", "en": "{rate} {cur} per hour"},
    "txt_rate_button": {"ru": "{rate} {cur}/час", "en": "{rate} {cur}/h"},
    "txt_all_square": {"ru": "Все в расчёте — никто никому не должен.", "en": "All square — nobody owes anything."},
    "txt_confirm_new": {
        "ru": "Сессия уже открыта — {players}, {money}. Закрыть и начать новую?",
        "en": "A session is already open — {players}, {money}. Close it and start a new one?",
    },
    "txt_replaced": {"ru": "⚠️ Сессия заменена", "en": "⚠️ Session replaced"},
    "btn_close_session": {"ru": "🗑 Закрыть сессию", "en": "🗑 Close session"},
    "btn_close_yes": {"ru": "🗑 Да, закрыть", "en": "🗑 Yes, close"},
    "title_close": {"ru": "🗑 Закрыть сессию?", "en": "🗑 Close the session?"},
    "txt_close_confirm": {
        "ru": "{players}, {money}. Сессия закроется без расчёта: время и взносы удалятся, "
              "а /split начнёт новую.",
        "en": "{players}, {money}. The session closes without settling: times and payments "
              "are deleted, and /split starts a new one.",
    },
    "txt_dropped": {"ru": "🗑 Сессия {date} закрыта {name} без расчёта",
                    "en": "🗑 Session {date} closed by {name} without settling"},
    "txt_send_rename": {"ru": "Ответьте на сообщение бота новым именем",
                        "en": "Reply to the bot's message with the new name"},
    "txt_players_count": {"ru": "{n} {word}", "en": "{n} players"},
    "txt_template_hint": {
        "ru": "Скопируйте таблицу, впишите свои строки и пришлите её ответом "
              "на это сообщение:",
        "en": "Copy the table, fill in your rows and send it back as a reply "
              "to this message:",
    },
    "txt_subtotal_cols": {
        "ru": "имя\tнаиграл(а)\tбаланс",
        "en": "name\tplayed\tbalance",
    },
    "txt_template_cols": {
        "ru": "имя\tвремя\tвзнос",
        "en": "name\ttime\tpaid",
    },
    "txt_sheet_failed": {"ru": "Не удалось прочитать таблицу. Откройте доступ по ссылке "
                               "(«Просмотр» для всех, у кого есть ссылка).",
                         "en": "Couldn't read the sheet. Share it by link "
                               "(anyone with the link can view)."},
    "txt_sheet_empty": {"ru": "В таблице не нашлось строк вида «имя, начало, конец».",
                        "en": "No rows shaped like “name, start, end” in that sheet."},
    "txt_incomplete": {"ru": "Сначала заполните время и взнос: {names}",
                       "en": "Fill in time and paid first: {names}"},
    "txt_waiting": {"ru": "{names} пожалуйста, заполните ваши время и взнос.",
                    "en": "{names} please fill in your time and paid amount."},
    "txt_waiting_hint": {"ru": "(Воспользуйтесь кнопками ниже или ответьте на это сообщение "
                               "командой edit, например <code>/edit 19:00-21:00 32</code>)",
                         "en": "(Use the buttons below, or reply to this message with edit "
                               "command, e.g. <code>/edit 19:00-21:00 32</code>)"},
    "txt_nothing_yet": {"ru": "Пока нечего считать.", "en": "Nothing to split yet."},
    "txt_retry": {"ru": "⚠️ Не понял — ответьте на это сообщение ещё раз.",
                  "en": "⚠️ Didn't catch that — reply to this message again."},
    "txt_send_name": {"ru": "Ответьте на сообщение бота именем или «Имя 19-21»",
                      "en": "Reply to the bot's message with a name, or “Name 19-21”"},
    "txt_send_time": {"ru": "Ответьте на сообщение бота временем, например 20:30",
                      "en": "Reply to the bot's message with a time like 20:30"},
    "txt_send_amount": {"ru": "Ответьте на сообщение бота суммой",
                        "en": "Reply to the bot's message with an amount"},
    "txt_send_rate": {"ru": "Ответьте на сообщение бота ценой за час",
                      "en": "Reply to the bot's message with the hourly price"},
    "txt_gone": {"ru": "Эта сессия пропала — отправь /split, чтобы начать новую.",
                 "en": "This session is gone — send /split to start a new one."},

    "help": {
        "ru": (
            "🏓 <b>Как это работает</b>\n\n"
            "<b>Как начать</b>\n"
            "/split — открывает пустую сессию с шаблоном таблицы: скопируйте таблицу, "
            "впишите строки, пришлите ответом, пример на скриншоте выше\n"
            "/split &lt;ссылка на Google Sheets&gt; — возьмёт таблицу оттуда, также можно "
            "просто скопировать и вставить любую таблицу напрямую текстом\n\n"
            "/add @маша 20-22 35 — добавить игрока в открытую сессию\n"
            "/edit @маша 20:30-22 — поправить того, кто уже в списке; без имени — "
            "себя, если ваш @ник есть в списке\n"
            "/panel — вернуть панель вниз, если её завалило чатом\n\n"
            "Формат для всех команд одинаковый: <b>имя время взнос</b> "
            "(пример: @player1 20:30-22:00 50)\n"
            "• <b>имя</b> — с @ или без\n"
            "• <b>время</b> — начало и конец через дефис: 21-23, 21:15-22, 21:30 - 22:30\n"
            "• <b>взнос</b> — любое число после времени; не указан — 0, ничего не вносил\n\n"
            "«-» вместо времени или взноса — игрок впишет сам "
            "(@player1 - -). Рассчитать можно, когда время и взнос есть у всех, "
            "поэтому сессию можно открыть одними именами: /split @маша @паша\n\n"
            "❗️ В группе бот читает только ответы на своё сообщение — таблицу и всё, "
            "что он просит ввести, присылайте ответом на панель; обычную переписку "
            "в чате он не видит. В личке с ботом можно просто писать.\n\n"
            "<b>Расчёт</b>\n"
            "Платим за время: все, кто на площадке в этот момент, делят стоимость поровну. "
            "Сколько столов заняли — неважно.\n\n"
            "Пока взносы не указаны, всё считается по цене за час — это удобно, если "
            "скидываетесь сразу на месте. Как только появляется хотя бы один взнос, "
            "итог считается от общей внесённой суммы, а цена за час больше ни на что "
            "не влияет, так что её можно не редактировать, даже если отличается.\n\n"
            "Точное время тоже не критично: важно лишь, кто с кем пересекался и "
            "сколько играл относительно остальных. Сдвиньте время всем на полчаса — "
            "итог не изменится.\n\n"
            "Если час стоил по-разному (например, пиковое время дороже), можно указать, "
            "за какое время платили: взнос «12.5 21:30-22:15» делят только те, кто играл "
            "в это время. Если цена весь вечер одна, указывать не нужно — итог тот же.\n\n"
            "<b>Опция «Платит отдельно»</b>\n"
            "Игрок не участвует в переводах: рассчитывается наличными, нет карты или "
            "контактов для перевода. Взнос при этом учитывается, а разница "
            "расходится поровну между остальными."
        ),
        "en": (
            "🏓 <b>How it works</b>\n\n"
            "<b>Getting started</b>\n"
            "/split — opens an empty session with a table template: copy the table, "
            "fill in the rows, send it back as a reply, see the example in the screenshot above\n"
            "/split &lt;Google Sheets link&gt; — reads the table from there; you can also "
            "just copy and paste any table straight in as text\n\n"
            "/add @masha 20-22 35 — add a player to an open session\n"
            "/edit @masha 20:30-22 — fix someone already on the list; without a name — "
            "yourself, if your @username is on it\n"
            "/panel — bring the panel back down if chat buried it\n\n"
            "The format is the same for every command: <b>name time paid</b> "
            "(example: @player1 20:30-22:00 50)\n"
            "• <b>name</b> — with or without @\n"
            "• <b>time</b> — start and end with a dash: 21-23, 21:15-22, 21:30 - 22:30\n"
            "• <b>paid</b> — any number after the time; left out, it's 0 — paid nothing\n\n"
            "“-” in place of a time or paid — the player fills it in "
            "(@player1 - -). The split can only be calculated once everyone has both, "
            "so a session can open with names alone: /split @masha @pasha\n\n"
            "❗️ In a group the bot only reads replies to its own message — send the "
            "table, and anything it asks you for, as a reply to the panel; it never "
            "sees ordinary chat. In a direct chat with the bot you can just type.\n\n"
            "<b>The split</b>\n"
            "You pay for time: everyone present at that moment splits the cost equally. "
            "The number of tables doesn't matter.\n\n"
            "Until any contribution is recorded, everything is calculated from the hourly "
            "price — handy when you all chip in on the spot. As soon as one contribution "
            "exists, the total comes from the sum actually paid, and the hourly price "
            "stops affecting anything — no need to correct it even if it's off.\n\n"
            "The exact clock times aren't critical either: what matters is who "
            "overlapped with whom, and how long each played relative to the others. "
            "Shift everyone by half an hour and the result is the same.\n\n"
            "If an hour cost different amounts (say, peak time is pricier), you can say "
            "which time a payment covered: “12.5 21:30-22:15” is shared only by whoever "
            "played then. If the price was the same all evening, there's no need — the "
            "result is identical.\n\n"
            "<b>The “Settles separately” option</b>\n"
            "A player left out of transfers: settling in cash, no card, or no contact to "
            "transfer to. Their contribution still counts, and the difference is spread "
            "evenly across everyone else."
        ),
    },
}


def t(lang: str, key: str, **kwargs) -> str:
    entry = STRINGS.get(key)
    if not entry:
        return key
    text = entry.get(lang) or entry[DEFAULT_LANG]
    return text.format(**kwargs) if kwargs else text
