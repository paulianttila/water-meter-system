from typing import Callable

from nicegui import ui

from .step_draw_rois_base import DrawRoisBaseStep


class DrawRefsStep(DrawRoisBaseStep):
    def __init__(
        self,
        name: str,
        name_template: str,
        spinner=None,
        get_image_func: Callable[[], None] = None,
        set_image_func: Callable[[], None] = None,
        set_rois_to_svg_func: Callable[[], str] = None,
        show_temp_draw_in_svg_func: Callable[[], str] = None,
    ) -> None:
        super().__init__(
            name,
            name_template,
            spinner,
            get_image_func,
            set_image_func,
            self.draw_roi_func,
            set_rois_to_svg_func,
            show_temp_draw_in_svg_func,
        )

    def draw_roi_func(
        self,
        x: int,
        y: int,
        w: int,
        h: int,
        color: str,
        text: str,
    ):
        style = f"stroke-width:3;stroke:{color};fill-opacity:0;stroke-opacity:0.9"
        style2 = f"font-size:10;fill:{color};"
        return (
            f'<text x="{x}" y="{y-7}" text-anchor="left" style="{style2}">{text}</text>'
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" style="{style}" />'
        )

    def select_all_rois(self):
        state = self.select_all.value
        for roi in self.rois:
            roi.enabled = state

    def add_roi(self):
        for roi in self.rois:
            roi.enabled = False
        super().add_roi()

    async def show(self, stepper, first_step=False, last_step=False):
        with ui.step(self.name):
            with ui.grid(columns="2fr 2fr 2fr 2fr 2fr 2fr").classes("w-full gap-2"):
                self.select_all = ui.checkbox(
                    "Show", on_change=self.select_all_rois
                ).tooltip("Show all")
                ui.label("Name")
                ui.label("X-position")
                ui.label("Y-position")
                ui.label("Width")
                ui.label("Height")
            self.container = ui.row().classes("w-full")
            with ui.row():
                ui.button(icon="add", on_click=self.add_roi).tooltip(
                    "Add reference point"
                )
                ui.button(icon="cancel", on_click=self.remove_roi).bind_enabled_from(
                    self, "container", lambda x: len(list(x)) > 0
                ).tooltip("Remove last reference point")
            super().add_navigator(stepper, first_step, last_step)
