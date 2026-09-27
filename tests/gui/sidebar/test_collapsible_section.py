from PySide6.QtWidgets import QApplication, QWidget

from ovd_gui.gui.sidebar import CollapsibleSection, SectionStack


def test_toggle_hides_content_and_reports_state(application: QApplication) -> None:
    content: QWidget = QWidget()
    section: CollapsibleSection = CollapsibleSection("Model", content, is_stretched=True)
    section.show()
    states: list[bool] = []
    section.expanded_changed.connect(states.append)
    section.toggle()
    assert not section.is_expanded
    assert not section.is_stretching
    assert content.isHidden()
    section.toggle()
    assert section.is_expanded
    assert not content.isHidden()
    assert states == [False, True]


def test_folded_sections_leave_spare_height_to_stretched_ones(application: QApplication) -> None:
    sidebar: SectionStack = SectionStack()
    table_section: CollapsibleSection = sidebar.add_section("Classes", QWidget(), is_stretched=True)
    form_section: CollapsibleSection = sidebar.add_section("Model", QWidget(), is_stretched=False)
    sidebar.resize(300, 800)
    sidebar.show()
    form_section.set_expanded(False)
    for _ in range(3):
        application.processEvents()
    assert table_section.height() > sidebar.viewport().height() / 2
