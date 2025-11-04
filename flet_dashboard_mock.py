import random
import time
from datetime import datetime
import flet as ft


# --------- helpers ---------
PRIMARY_BG = "#121417"  # общий фон
PANEL_BG = "#1E2227"    # панели/карточки
BORDER = "#2A2F36"
TEXT = "#E6EAF0"
SUBTEXT = "#9AA4B2"
ACCENT = "#27AE60"      # зелёный для Connect/Active
WARNING = "#F2C94C"
DANGER = "#EB5757"
INFO = "#2D9CDB"
PURPLE = "#9B51E0"
BLUE = "#2F80ED"
ORANGE = "#F2994A"

BTN_H = 40
RADIUS = 8
SP = 12


def btn(label: str, color: str, icon: str | None = None, on_click=None, width: int | None = None) -> ft.Container:
    content = ft.Row(
        [ft.Icon(icon, size=18, color=TEXT) if icon else ft.Container(width=0), ft.Text(label, color=TEXT)],
        spacing=8,
        alignment=ft.MainAxisAlignment.CENTER,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )
    return ft.Container(
        content=content,
        bgcolor=color,
        padding=ft.padding.symmetric(horizontal=16),
        border_radius=RADIUS,
        height=BTN_H,
        width=width,
        alignment=ft.alignment.center,
        ink=True,
        on_click=on_click,
    )


def badge(text: str, color: str = ACCENT) -> ft.Container:
    return ft.Container(
        content=ft.Text(text, color=TEXT, size=12),
        bgcolor=color,
        padding=ft.padding.symmetric(horizontal=8, vertical=4),
        border_radius=999,
    )


def list_item(title: str, subtitle: str, selected=False, starred=True) -> ft.Container:
    star = ft.Icon("star", color=(ACCENT if starred else SUBTEXT), size=16)
    left_bar = ft.Container(width=4, bgcolor=ACCENT if selected else "#00000000")
    item = ft.Container(
        content=ft.Row([
            star,
            ft.Column([
                ft.Text(title, color=TEXT),
                ft.Text(subtitle, color=SUBTEXT, size=12),
            ], spacing=2, expand=True),
        ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        padding=10,
        bgcolor=PANEL_BG if selected else "#00000000",
        border=ft.border.only(bottom=ft.BorderSide(1, BORDER)),
    )
    return ft.Row([left_bar, item], spacing=0)


def action_buttons_row(apply_cb, switch_cb, stats_cb, delete_cb) -> ft.Row:
    return ft.Row([
        btn("Apply", BLUE, "done", on_click=apply_cb),
        btn("Switch", INFO, "swap_horiz", on_click=switch_cb),
        btn("Stats", ACCENT, "bar_chart", on_click=stats_cb),
        btn("Delete", DANGER, "delete", on_click=delete_cb),
    ], spacing=SP)


# --------- main app ---------

def main(page: ft.Page):
    page.title = "XPL-EX Manager (mock)"
    page.theme_mode = ft.ThemeMode.DARK
    page.window_min_width = 1100
    page.window_min_height = 700
    page.bgcolor = PRIMARY_BG
    page.padding = 10
    page.scroll = ft.ScrollMode.AUTO

    # top toolbar
    ip_field = ft.TextField(value="192.168.1.200:5555", text_style=ft.TextStyle(color=TEXT),
                            bgcolor=PANEL_BG, border_color=BORDER, cursor_color=TEXT,
                            prefix_text="IP:", prefix_style=ft.TextStyle(color=SUBTEXT),
                            height=BTN_H, width=220)

    status_dot = ft.Icon("lens", color=ACCENT, size=10)
    status_txt = ft.Text("Connected to 192.168.1.200:5555", color=TEXT)

    def copy_logs(_):
        page.set_clipboard("Dummy logs...\n" + time.strftime("[%H:%M:%S] logs copied"))
        page.snack_bar = ft.SnackBar(ft.Text("Logs copied to clipboard"))
        page.snack_bar.open = True
        page.update()

    toolbar = ft.Container(
        bgcolor=PANEL_BG,
        padding=10,
        border_radius=RADIUS,
        border=ft.border.all(1, BORDER),
        content=ft.Row([
            ft.Row([
                ft.Icon("android", color=TEXT),
                ft.Text("XPL-EX Manager", color=TEXT, weight=ft.FontWeight.BOLD),
            ], spacing=8),
            ft.Row([
                ip_field,
                btn("Connect", ACCENT, "power", on_click=lambda e: None),
                status_dot,
                status_txt,
            ], spacing=10),
            ft.Row([
                btn("Refresh", ACCENT, "refresh", on_click=lambda e: None),
                btn("Copy Logs", PANEL_BG, "content_copy", on_click=copy_logs),
                btn("Settings", PANEL_BG, "settings", on_click=lambda e: None),
            ], spacing=10),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),
    )

    # left navigation
    nav_search = ft.TextField(hint_text="Search", height=36, bgcolor=PANEL_BG, border_color=BORDER,
                              text_style=ft.TextStyle(color=TEXT), hint_style=ft.TextStyle(color=SUBTEXT))

    modules = [
        ("Deviceid", "(com.evozi.deviceid)"),
        ("Deviceinfo", "(com.liuzh.deviceinfo)"),
        ("Simplenote", "(com.automattic.simplenote)"),
        ("Whatsapp", "(com.whatsapp)"),
        ("Accessory", "(com.oneplus.accessory)"),
        ("Account", "(com.oneplus.account)"),
        ("Activation", "(com.quicinc.voice.activation)"),
        ("Activation", "(com.netflix.partner.activation)"),
        ("Android", "(com.android)"),
        ("Android", "(com.oneplus.productoverlay)"),
    ]

    nav_list = ft.ListView(expand=1, spacing=0, padding=0)
    for i, (name, pkg) in enumerate(modules):
        nav_list.controls.append(list_item(name, pkg, selected=(i == 0), starred=(i < 4)))

    left_panel = ft.Container(
        width=300,
        bgcolor=PANEL_BG,
        border=ft.border.all(1, BORDER),
        border_radius=RADIUS,
        padding=10,
        content=ft.Column([
            nav_search,
            ft.Container(height=10),
            ft.Container(expand=True, content=nav_list, bgcolor=PANEL_BG, border_radius=RADIUS),
        ], expand=True),
    )

    # main content header + quick actions
    section_title = ft.Text("Deviceid", color=TEXT, size=22, weight=ft.FontWeight.BOLD)
    section_sub = ft.Text("com.evozi.deviceid", color=SUBTEXT)

    quick_actions = ft.Row([
        btn("Launch", ACCENT, "play_arrow"),
        btn("Stop", DANGER, "stop"),
        btn("Clear", ORANGE, "delete_sweep"),
        btn("Backup", BLUE, "backup"),
        btn("Data", INFO, "storage"),
        btn("Full", PURPLE, "inventory_2"),
    ], spacing=SP)

    # configs list
    cfg_search = ft.TextField(hint_text="Search configs...", bgcolor=PANEL_BG, border_color=BORDER,
                               text_style=ft.TextStyle(color=TEXT), hint_style=ft.TextStyle(color=SUBTEXT))

    cfg_list = ft.ListView(expand=1, spacing=10, padding=0)

    def make_cfg_row(num: int) -> ft.Container:
        used = random.randint(0, 3)
        active = random.random() < 0.25
        id_text = f"79{random.randint(100000000, 999999999)}"

        status = ft.Text("Active", color=ACCENT) if active else ft.Text("", color=SUBTEXT)

        header = ft.Row([
            ft.Text(id_text, color=TEXT, weight=ft.FontWeight.BOLD),
            ft.Text(f"Used in {used} apps", color=SUBTEXT),
            status,
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        # создаём ряд заранее, чтобы замыкания могли ссылаться на него
        row = ft.Container(
            bgcolor=PANEL_BG,
            border=ft.border.all(1, BORDER),
            border_radius=RADIUS,
            padding=12,
            content=None,
        )

        def show_snack(msg: str):
            page.snack_bar = ft.SnackBar(ft.Text(msg))
            page.snack_bar.open = True
            page.update()

        def apply_cb(e):
            show_snack(f"Applied {id_text}")

        def switch_cb(e):
            show_snack(f"Switched {id_text}")

        def stats_cb(e):
            dlg = ft.AlertDialog(title=ft.Text("Stats"), content=ft.Text(f"Used in {used} apps"))
            page.dialog = dlg
            dlg.open = True
            page.update()

        def delete_cb(e):
            cfg_list.controls.remove(row)
            page.update()

        actions = action_buttons_row(apply_cb, switch_cb, stats_cb, delete_cb)

        row.content = ft.Column([
            header,
            ft.Divider(height=10, color=BORDER),
            actions,
        ], spacing=8)
        return row

    for i in range(8):
        cfg_list.controls.append(make_cfg_row(i))

    configs_panel = ft.Container(
        bgcolor=PANEL_BG,
        border=ft.border.all(1, BORDER),
        border_radius=RADIUS,
        padding=12,
        content=ft.Column([
            ft.Text("XPL-EX Configurations", color=TEXT, weight=ft.FontWeight.BOLD),
            cfg_search,
            cfg_list,
        ], spacing=10, expand=True),
    )

    # console bottom
    console_lines = [
        "[23:29:19] Starting XPL-EX first...",
        "[23:29:19] XPL-EX ready",
        "[23:29:19] Application launched",
    ]
    console_view = ft.ListView(height=120, spacing=4, padding=10, auto_scroll=True,
                               controls=[ft.Text(x, color=SUBTEXT, font_family="monospace") for x in console_lines])
    console_input = ft.TextField(hint_text=">", bgcolor=PANEL_BG, border_color=BORDER, height=36,
                                 text_style=ft.TextStyle(color=TEXT))

    def on_console_submit(e: ft.ControlEvent):
        txt = console_input.value or ""
        if txt.strip():
            console_view.controls.append(ft.Text(f"[{datetime.now().strftime('%H:%M:%S')}] {txt}", color=SUBTEXT, font_family="monospace"))
            console_input.value = ""
            page.update()

    console_input.on_submit = on_console_submit

    console_panel = ft.Container(
        bgcolor=PANEL_BG,
        border=ft.border.all(1, BORDER),
        border_radius=RADIUS,
        content=ft.Row([
            ft.Container(expand=True, content=console_view),
            ft.Container(width=240, content=console_input, padding=10),
        ], spacing=0),
    )

    # main right column
    right_column = ft.Column([
        ft.Container(
            bgcolor=PANEL_BG,
            border=ft.border.all(1, BORDER),
            border_radius=RADIUS,
            padding=12,
            content=ft.Column([
                section_title,
                section_sub,
                ft.Container(height=8),
                quick_actions,
            ], spacing=4),
        ),
        ft.Container(height=10),
        configs_panel,
        ft.Container(height=10),
        console_panel,
    ], expand=True)

    # layout: left nav + right content
    body = ft.Row([
        left_panel,
        ft.Container(width=10),
        ft.Container(expand=True, content=right_column),
    ], expand=True, vertical_alignment=ft.CrossAxisAlignment.START)

    page.add(toolbar, ft.Container(height=10), body)


if __name__ == "__main__":
    ft.app(target=main)
