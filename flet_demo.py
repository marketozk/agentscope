import flet as ft


def main(page: ft.Page) -> None:
    """Демо Flet: вкладки, панель прилож., туду, медиа, настройки.

    Ключевые элементы:
    - AppBar с действиями
    - Tabs: Дом, Задачи, Медиа, Настройки
    - SnackBar, AlertDialog
    - Прогресс-индикаторы
    - Единый стиль кнопок + одинаковая ширина для ровного текста
    """

    # Базовые настройки окна
    page.title = "Flet Demo — расширенный GUI"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.horizontal_alignment = ft.CrossAxisAlignment.STRETCH
    page.scroll = ft.ScrollMode.ADAPTIVE

    # Утилиты уведомлений/диалогов
    def get_color(name: str, fallback: str) -> str:
        """Безопасно получить цвет из ft.colors или ft.Colors; иначе вернуть fallback."""
        c_lower = getattr(ft, "colors", None)
        if c_lower is not None and hasattr(c_lower, name):
            return getattr(c_lower, name)
        c_upper = getattr(ft, "Colors", None)
        if c_upper is not None and hasattr(c_upper, name):
            return getattr(c_upper, name)
        return fallback

    def show_snack(msg: str) -> None:
        page.snack_bar = ft.SnackBar(ft.Text(msg))
        page.snack_bar.open = True
        page.update()

    confirm_dlg = ft.AlertDialog(modal=True)

    def confirm(title: str, message: str, on_ok) -> None:
        def close_ok(_):
            confirm_dlg.open = False
            page.update()
            on_ok()

        def close_cancel(_):
            confirm_dlg.open = False
            page.update()

        confirm_dlg.title = ft.Text(title)
        confirm_dlg.content = ft.Text(message)
        confirm_dlg.actions = [
            ft.TextButton("Отмена", on_click=close_cancel),
            ft.FilledButton("ОК", icon="check", width=120, on_click=close_ok),
        ]
        page.dialog = confirm_dlg
        confirm_dlg.open = True
        page.update()

    # Общий стиль/ширина для кнопок, чтобы текст не переносился и выглядел ровно
    BTN_WIDTH = 240

    def _btn_content(text: str, icon: str | None) -> ft.Control:
        if icon:
            return ft.Row([
                ft.Icon(name=icon, size=18),
                ft.Text(text, no_wrap=True),
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=8)
        return ft.Text(text, no_wrap=True)

    def eb(text: str, icon: str | None = None, **kwargs) -> ft.ElevatedButton:
        return ft.ElevatedButton(content=_btn_content(text, icon), width=BTN_WIDTH, **kwargs)

    def fb(text: str, icon: str | None = None, **kwargs) -> ft.FilledButton:
        return ft.FilledButton(content=_btn_content(text, icon), width=BTN_WIDTH, **kwargs)

    def ob(text: str, icon: str | None = None, **kwargs) -> ft.OutlinedButton:
        return ft.OutlinedButton(content=_btn_content(text, icon), width=BTN_WIDTH, **kwargs)

    # Состояния
    theme_switch = ft.Switch(label="Тёмная тема", value=False)
    name = ft.TextField(label="Ваше имя", autofocus=True, expand=True)
    greet_text = ft.Text(size=16)
    counter_value = ft.Text("0", size=18, weight=ft.FontWeight.BOLD)
    todo_input = ft.TextField(label="Новая задача", expand=True)
    todo_list = ft.ListView(expand=1, spacing=8, padding=8, auto_scroll=True)
    image = ft.Image(height=260, width=260, fit=ft.ImageFit.CONTAIN, visible=False, border_radius=8)
    image_scale = ft.Slider(label="Масштаб", min=0.5, max=2.0, divisions=15, value=1.0)
    linear_progress = ft.ProgressBar(width=400, value=None, visible=False)
    circular_progress = ft.ProgressRing(visible=False)

    # Тема
    def on_theme_change(e: ft.ControlEvent) -> None:
        page.theme_mode = ft.ThemeMode.DARK if theme_switch.value else ft.ThemeMode.LIGHT
        page.update()

    theme_switch.on_change = on_theme_change

    # Приветствие
    def greet_click(_):
        greet_text.value = f"Привет, {name.value}!" if name.value else "Введите имя выше и нажмите кнопку"
        page.update()
        show_snack("Готово: приветствие обновлено")

    greet_btn = eb("Поздороваться", icon="emoji_people", on_click=greet_click)

    # Счётчик
    def inc(_):
        try:
            counter_value.value = str(int(counter_value.value) + 1)
        except ValueError:
            counter_value.value = "0"
        page.update()

    counter_btn = fb("Счётчик +1", icon="add", on_click=inc)

    # Мини-туду
    def add_todo(text: str) -> None:
        text = (text or "").strip()
        if not text:
            return
        chip = ft.Chip(
            label=ft.Text(text),
            delete_icon=ft.Icon(name="close"),
        )

        def remove_chip(_):
            todo_list.controls.remove(chip)
            page.update()
            show_snack("Задача удалена")

        chip.on_delete = remove_chip
        todo_list.controls.append(chip)
        todo_input.value = ""
        page.update()
        show_snack("Задача добавлена")

    def on_todo_submit(e: ft.ControlEvent) -> None:
        add_todo(todo_input.value)

    todo_input.on_submit = on_todo_submit
    add_btn = ft.IconButton(icon="send", tooltip="Добавить задачу", on_click=lambda e: add_todo(todo_input.value))

    def clear_todos(_):
        def do_clear():
            todo_list.controls.clear()
            page.update()
            show_snack("Список очищен")
        confirm("Очистить задачи", "Вы уверены, что хотите удалить все задачи?", do_clear)

    clear_btn = ob("Очистить список", icon="delete", on_click=clear_todos)

    # Медиа: выбор файла и масштаб
    def on_file_pick(res: ft.FilePickerResultEvent) -> None:
        if res.files:
            file_path = res.files[0].path
            image.src = file_path
            image.visible = True
            image.height = int(260 * image_scale.value)
            image.width = int(260 * image_scale.value)
            page.update()

    file_picker = ft.FilePicker(on_result=on_file_pick)
    page.overlay.append(file_picker)
    pick_btn = ob("Выбрать изображение", icon="image", on_click=lambda e: file_picker.pick_files(allow_multiple=False))

    def on_scale_change(_):
        if image.visible:
            image.height = int(260 * image_scale.value)
            image.width = int(260 * image_scale.value)
            page.update()

    image_scale.on_change = on_scale_change

    # Прогресс демо
    def toggle_progress(_):
        visible = not linear_progress.visible
        linear_progress.visible = visible
        circular_progress.visible = visible
        page.update()

    progress_btn = eb("Показать прогресс", icon="hourglass_empty", on_click=toggle_progress)

    # Верхняя панель приложения
    page.appbar = ft.AppBar(
        title=ft.Text("Flet Demo"),
        center_title=False,
        bgcolor=get_color("SURFACE_VARIANT", "#ECECEC"),
        actions=[
            ft.IconButton(icon="info", tooltip="О приложении", on_click=lambda e: show_snack("Пример Flet 0.28")),
        ],
    )

    # ---------- Формы: дата/время/выпадающие списки/баннер ----------
    category_dd = ft.Dropdown(
        label="Категория",
        options=[
            ft.dropdown.Option("A"),
            ft.dropdown.Option("B"),
            ft.dropdown.Option("C"),
        ],
        value="A",
        width=BTN_WIDTH,
    )

    date_value_text = ft.Text("Дата не выбрана")
    time_value_text = ft.Text("Время не выбрано")

    def on_date_change(_):
        v = date_picker.value
        date_value_text.value = v.strftime("%Y-%m-%d") if v else "Дата не выбрана"
        page.update()

    def on_time_change(_):
        v = time_picker.value
        time_value_text.value = (f"{v.hour:02d}:{v.minute:02d}" if v else "Время не выбрано")
        page.update()

    date_picker = ft.DatePicker(on_change=on_date_change)
    time_picker = ft.TimePicker(on_change=on_time_change)
    # Помещаем диалоги в overlay, чтобы они отображались поверх
    page.overlay.extend([date_picker, time_picker])

    def open_date(_):
        date_picker.open = True
        page.update()

    def open_time(_):
        time_picker.open = True
        page.update()

    date_btn = ob("Выбрать дату", icon="event", on_click=open_date)
    time_btn = ob("Выбрать время", icon="schedule", on_click=open_time)

    # Banner (верхнее уведомление)
    banner = ft.Banner(
        bgcolor=get_color("AMBER_100", "#FFECB3"),
        leading=ft.Icon(name="notifications"),
        content=ft.Text("Это баннер-уведомление (пример)."),
        actions=[
            ft.TextButton("Закрыть", on_click=lambda e: setattr(banner, "open", False) or page.update()),
        ],
    )
    page.banner = banner

    def open_banner(_):
        banner.open = True
        page.update()

    banner_btn = eb("Показать баннер", icon="campaign", on_click=open_banner)

    forms_tab = ft.Tab(
        text="Формы",
        icon="tune",
        content=ft.Container(
            padding=16,
            content=ft.Column([
                ft.Text("Выпадающие списки", size=16, weight=ft.FontWeight.BOLD),
                category_dd,
                ft.Divider(),
                ft.Text("Дата и время", size=16, weight=ft.FontWeight.BOLD),
                ft.Row([date_btn, date_value_text], alignment=ft.MainAxisAlignment.START, spacing=16),
                ft.Row([time_btn, time_value_text], alignment=ft.MainAxisAlignment.START, spacing=16),
                ft.Divider(),
                ft.Text("Уведомления", size=16, weight=ft.FontWeight.BOLD),
                ft.Row([banner_btn]),
            ], spacing=12),
        ),
    )

    # ---------- Таблица (DataTable) с добавлением/удалением ----------
    id_field = ft.TextField(label="ID", width=120)
    title_field = ft.TextField(label="Название", expand=1)
    category_table_dd = ft.Dropdown(
        label="Категория",
        options=[ft.dropdown.Option("A"), ft.dropdown.Option("B"), ft.dropdown.Option("C")],
        value="A",
        width=160,
    )

    row_date_text = ft.Text("Дата не выбрана")
    row_date_picker = ft.DatePicker(on_change=lambda e: (
        row_date_text.__setattr__("value", row_date_picker.value.strftime("%Y-%m-%d") if row_date_picker.value else "Дата не выбрана"),
        page.update()
    ))
    page.overlay.append(row_date_picker)
    row_date_btn = ob("Дата записи", icon="event", on_click=lambda e: row_date_picker.pick_date())

    table_rows: list[ft.DataRow] = []
    table_filter: str = ""
    table_sort_key: str | None = None  # "id" | "title"
    table_sort_reverse: bool = False
    data_table: ft.DataTable | None = None

    def row_to_dict(r: ft.DataRow) -> dict:
        def _txt(c):
            return c.content.value if isinstance(c.content, ft.Text) else ""
        return {
            "id": _txt(r.cells[0]),
            "title": _txt(r.cells[1]),
            "category": _txt(r.cells[2]),
            "date": _txt(r.cells[3]),
        }

    def rebuild_table():
        rows = list(table_rows)
        if table_filter:
            needle = table_filter.lower()
            def match(r: ft.DataRow) -> bool:
                d = row_to_dict(r)
                return any(needle in (d[k] or "").lower() for k in ("id","title","category","date"))
            rows = [r for r in rows if match(r)]

        if table_sort_key:
            idx = 0 if table_sort_key == "id" else 1
            def keyf(r: ft.DataRow):
                cont = r.cells[idx].content
                return cont.value if isinstance(cont, ft.Text) else ""
            rows = sorted(rows, key=keyf, reverse=table_sort_reverse)

        if data_table is not None:
            data_table.rows = rows
            page.update()

    def on_search_change(e: ft.ControlEvent):
        nonlocal table_filter
        table_filter = (search_field.value or "").strip()
        rebuild_table()

    def add_row(_):
        rid = (id_field.value or "").strip()
        title = (title_field.value or "").strip()
        cat = category_table_dd.value
        rdate = row_date_text.value if row_date_text.value != "Дата не выбрана" else ""
        if not rid or not title:
            show_snack("Заполните ID и Название")
            return

        idx = len(table_rows)

        def on_row_select(e, i=idx):
            # Просто обновляем отображение выбранности
            table_rows[i].selected = e.control.selected
            page.update()

        row = ft.DataRow(
            cells=[
                ft.DataCell(ft.Text(rid)),
                ft.DataCell(ft.Text(title)),
                ft.DataCell(ft.Text(cat)),
                ft.DataCell(ft.Text(rdate)),
            ],
            selected=False,
            on_select_changed=on_row_select,
        )
        table_rows.append(row)
        id_field.value = ""
        title_field.value = ""
        rebuild_table()
        show_snack("Строка добавлена")

    def remove_selected(_):
        if not any(r.selected for r in table_rows):
            show_snack("Нет выбранных строк")
            return

        def do_remove():
            nonlocal table_rows
            table_rows = [r for r in table_rows if not r.selected]
            rebuild_table()
            show_snack("Удалено")

        confirm("Удалить строки", "Удалить все выделенные строки?", do_remove)

    add_row_btn = fb("Добавить запись", icon="add", on_click=add_row)
    rm_row_btn = ob("Удалить выбранные", icon="delete", on_click=remove_selected)

    # Поиск / сортировка / экспорт / очистка полей / сброс вида
    search_field = ft.TextField(label="Поиск", width=220, on_change=on_search_change)

    def sort_by_id(_):
        nonlocal table_sort_key, table_sort_reverse
        if table_sort_key == "id":
            table_sort_reverse = not table_sort_reverse
        else:
            table_sort_key = "id"
            table_sort_reverse = False
        rebuild_table()

    def sort_by_title(_):
        nonlocal table_sort_key, table_sort_reverse
        if table_sort_key == "title":
            table_sort_reverse = not table_sort_reverse
        else:
            table_sort_key = "title"
            table_sort_reverse = False
        rebuild_table()

    sort_id_btn = ob("Сортировать по ID", icon="sort", on_click=sort_by_id)
    sort_title_btn = ob("Сортировать по названию", icon="sort_by_alpha", on_click=sort_by_title)

    def export_csv(_):
        import io, csv
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow(["ID","Название","Категория","Дата"])
        if data_table is None:
            show_snack("Таблица ещё не инициализирована")
            return
        for r in data_table.rows:
            d = row_to_dict(r)
            w.writerow([d["id"], d["title"], d["category"], d["date"]])
        page.set_clipboard(out.getvalue())
        show_snack("CSV скопирован в буфер обмена")

    export_btn = ob("Экспорт CSV", icon="file_download", on_click=export_csv)

    def clear_form(_):
        id_field.value = ""
        title_field.value = ""
        page.update()

    clear_form_btn = ob("Очистить поля", icon="backspace", on_click=clear_form)

    def reset_view(_):
        nonlocal table_filter, table_sort_key, table_sort_reverse
        table_filter = ""
        table_sort_key = None
        table_sort_reverse = False
        search_field.value = ""
        rebuild_table()

    reset_view_btn = ob("Сброс вида", icon="filter_alt_off", on_click=reset_view)

    data_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("ID")),
            ft.DataColumn(ft.Text("Название")),
            ft.DataColumn(ft.Text("Категория")),
            ft.DataColumn(ft.Text("Дата")),
        ],
        rows=table_rows,
        column_spacing=24,
        heading_row_height=40,
        data_row_max_height=44,
        divider_thickness=1,
    )

    table_tab = ft.Tab(
        text="Таблица",
        icon="table_chart",
        content=ft.Container(
            padding=16,
            content=ft.Column([
                ft.Text("DataTable", size=16, weight=ft.FontWeight.BOLD),
                ft.ResponsiveRow([
                    ft.Container(id_field, col=2),
                    ft.Container(title_field, col=5),
                    ft.Container(category_table_dd, col=2),
                    ft.Container(ft.Row([row_date_btn, row_date_text], spacing=12), col=3),
                ], run_spacing=10),
                ft.Row([search_field, sort_id_btn, sort_title_btn, export_btn, clear_form_btn, reset_view_btn], spacing=10, wrap=True),
                ft.Row([add_row_btn, rm_row_btn], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                data_table,
            ], spacing=12),
        ),
    )

    # Вкладка Дом
    home_tab = ft.Tab(
        text="Дом",
        icon="home",
        content=ft.Container(
            padding=16,
            content=ft.Column([
                ft.Text("Приветствие", size=16, weight=ft.FontWeight.BOLD),
                ft.ResponsiveRow([
                    ft.Container(name, col=9),
                    ft.Container(greet_btn, col=3),
                ], run_spacing=10),
                greet_text,
                ft.Divider(),
                ft.Row([counter_btn, counter_value], spacing=16),
            ], spacing=12),
        ),
    )

    # Вкладка Задачи
    tasks_tab = ft.Tab(
        text="Задачи",
        icon="checklist",
        content=ft.Container(
            padding=16,
            content=ft.Column([
                ft.Text("Список задач", size=16, weight=ft.FontWeight.BOLD),
                ft.Row([todo_input, add_btn], alignment=ft.MainAxisAlignment.START),
                ft.Row([clear_btn]),
                todo_list,
            ], spacing=12),
        ),
    )

    # Вкладка Медиа
    media_tab = ft.Tab(
        text="Медиа",
        icon="image",
        content=ft.Container(
            padding=16,
            content=ft.Column([
                ft.Row([pick_btn]),
                image,
                image_scale,
                ft.Row([progress_btn]),
                ft.Row([linear_progress, circular_progress], spacing=24),
            ], spacing=12),
        ),
    )

    # Вкладка Настройки
    settings_tab = ft.Tab(
        text="Настройки",
        icon="settings",
        content=ft.Container(
            padding=16,
            content=ft.Column([
                ft.Text("Оформление", size=16, weight=ft.FontWeight.BOLD),
                theme_switch,
            ], spacing=12),
        ),
    )

    tabs = ft.Tabs(
        selected_index=0,
        animation_duration=200,
        tabs=[home_tab, tasks_tab, media_tab, forms_tab, table_tab, settings_tab],
        expand=1,
    )

    # Итоговая компоновка
    page.add(tabs)


if __name__ == "__main__":
    ft.app(target=main)
