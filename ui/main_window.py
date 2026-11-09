from __future__ import annotations
from pathlib import Path
from PyQt6.QtWidgets import (
    QFileDialog, QMessageBox, QMainWindow, QFrame, QHBoxLayout, QVBoxLayout, QStackedWidget, QWidget
)
from PyQt6.QtCore import QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from core.constants import APP_NAME, ATTACHMENT_CUT_NOTE, PROMPT_RESERVE
from core.constants import DOCX_SUFFIX, PDF_SUFFIX, TEXT_SUFFIXES, XLSX_SUFFIX
from core.hardware import HardwareProfile
from core.gguf import read_meta
from core.monitor import UsageMonitor
from core.paths import ensure_dir
from core.errors import FukaiError, Notice
from storage.database import Database
from ui.chat_controller import ChatController
from ui.chat_view import ChatView
from ui.sidebar import Sidebar, PAGE_CHAT
from ui.properties_view import PropertiesView
from ui.settings_view import SettingsView
from ui.constants import WINDOW_MIN_SIZE, WINDOW_SIZE, PANEL_MARGIN
from ui.formatting import approx_tokens, int_text, size_text
from extensions.file_parser import Attachment
from ui.attachments import AttachmentService
from ui.model_library import ModelLibrary
from ui.settings_store import SettingsStore
from ui.model_info import ModelInfoDialog
from ui.text_preview import TextPreviewDialog
from ui.toast import Toast, ToastHost

__all__ = ["MainWindow"]


class MainWindow(QMainWindow):
    theme_changed = pyqtSignal(str)


    def __init__(self, settings: SettingsStore, hardware: HardwareProfile, database: Database, controller: ChatController, library: ModelLibrary, monitor: UsageMonitor, attachments: AttachmentService) -> None:
        super().__init__()
        self._controller = controller
        self._attachments = attachments
        self._loading_toast: Toast | None = None
        self._import_toast: Toast | None = None
        self._library = library
        self._settings = settings
        self._hardware = hardware
        self._database = database
        self._chats: dict[int, dict] = {}

        current = settings.current
        
        self.setWindowTitle(APP_NAME)
        self.resize(*WINDOW_SIZE)
        self.setMinimumSize(*WINDOW_MIN_SIZE)
        
        self._sidebar = Sidebar()
        self._chat = ChatView(hardware, monitor)
        self._properties_page = PropertiesView(hardware)
        self._settings_page = SettingsView()
        self._settings_page.model_info_requested.connect(self._on_model_info)
        
        self._pages = QStackedWidget()
        self._pages.addWidget(self._chat)
        self._pages.addWidget(self._properties_page)
        self._pages.addWidget(self._settings_page)
        
        panel = QFrame()
        panel.setObjectName("panel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.addWidget(self._pages)
        
        right = QVBoxLayout()
        right.setContentsMargins(PANEL_MARGIN, PANEL_MARGIN, PANEL_MARGIN, PANEL_MARGIN)
        right.addWidget(panel)
        
        central = QWidget()
        central.setObjectName("central")
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._sidebar)
        layout.addLayout(right, 1)
        self.setCentralWidget(central)
        
        self._sidebar.page_changed.connect(self._pages.setCurrentIndex)
        self._sidebar.new_chat_request.connect(controller.new_chat)
        self._sidebar.chat_selected.connect(controller.open_chat)
        self._sidebar.chat_rename_requested.connect(self._on_rename_chat)
        self._sidebar.chat_delete_requested.connect(self._on_delete_chat)
        self._sidebar.set_token_source(database.content_tokens)
        controller.chat_opened.connect(self._on_chat_opened)
        controller.chats_changed.connect(self._on_chats_changed)
        controller.notice.connect(self.show_notice)
        controller.loading_started.connect(self._on_loading_started)
        controller.loading_finished.connect(self._on_loading_finished)
        
        composer = self._chat.composer
        composer.set_model_source(library.models)
        composer.send_requested.connect(self._on_send)
        composer.stop_requested.connect(controller.stop)
        composer.model_selected.connect(controller.select_model)
        controller.busy_changed.connect(composer.set_busy)
        controller.model_changed.connect(composer.set_model)
        controller.turn_started.connect(composer.begin_turn)
        controller.turn_started.connect(self._chat.begin_turn)
        controller.web_progress.connect(self._chat.set_web_status)
        self._chat.messages.preview_requested.connect(self._on_history_preview)
        controller.token.connect(self._chat.append_token)
        controller.turn_finished.connect(self._chat.finish_turn)
        controller.turn_rolled_back.connect(lambda _question: self._chat.roll_back())
        controller.turn_finished.connect(composer.end_turn)
        controller.turn_rolled_back.connect(composer.roll_back)
        controller.loading_started.connect(lambda _title: composer.set_loading(True))
        controller.loading_finished.connect(lambda: composer.set_loading(False))
        
        composer.add_model_requested.connect(self._on_add_model)
        composer.delete_model_requested.connect(self._on_delete_model)
        composer.set_features(current.attachments_enabled, current.web_search_enabled)
        composer.attach_requested.connect(self._on_attach)
        composer.files_dropped.connect(self.add_attachments)
        composer.attachments.preview_requested.connect(self._on_preview)
        attachments.ready.connect(self._on_attachment_ready)
        attachments.failed.connect(self._on_attachment_failed)
        composer.web_toggled.connect(self._on_web_toggled)
        controller.model_changed.connect(lambda _model: self._sync_web())
        library.import_progress.connect(self._on_import_progress)
        library.import_finished.connect(self._on_import_finished)
        library.import_failed.connect(self._on_import_failed)
        library.import_cancelled.connect(self._on_import_cancelled)

        properties_page = self._properties_page
        properties_page.opened.connect(self._on_properties_opened)
        properties_page.apply_requested.connect(self._on_apply_properties)
        controller.busy_changed.connect(properties_page.set_busy)
        controller.model_changed.connect(self._on_model_for_properties)

        settings_page = self._settings_page
        settings_page.theme_changed.connect(self._on_theme_changed)
        settings_page.attachments_changed.connect(self._on_attachments_changed)
        settings_page.websearch_changed.connect(self._on_websearch_changed)
        settings_page.open_folder_requested.connect(self._on_open_folder)
        settings_page.opened.connect(self._on_settings_opened)
        settings_page.set_value(current.theme, current.web_search_enabled, current.attachments_enabled)
        settings_page.set_models_dir(current.models_dir)
        
        self._toast = ToastHost(self)
        self.apply_theme(settings.current.theme)
        self.reload_chats()
        controller.new_chat()
        

    def apply_theme(self, theme: str) -> None:
        self._sidebar.set_theme(theme)
        self._chat.set_theme(theme)
        self._properties_page.set_theme(theme)
        self._settings_page.set_theme(theme)
        
    
    def reload_chats(self) -> None:
        chats = self._database.list_chats()
        self._chats = {chat["id"]: chat for chat in chats}
        self._sidebar.set_chats(chats)
    
           
    def show_notice(self, notice: Notice, *, persistent: bool = False, progress: bool = False) -> Toast:
        return self._toast.show_notice(notice, persistent=persistent, progress=progress)
    
    
    def _show_page(self, page: int) -> None:
        self._sidebar.show_page(page)
        self._pages.setCurrentIndex(page)
    
    
    def _on_chat_opened(self, chat_id: int | None, title: str, messages: list[dict]) -> None:
        self._sidebar.select_chat(chat_id)
        self._chat.set_title(title)
        self._chat.show_messages(messages)
        self._chat.composer.end_turn()
        self._show_page(PAGE_CHAT)
        self._chat.composer.focus_input()


    def _on_chats_changed(self, selected: int | None) -> None:
        self.reload_chats()
        self._sidebar.select_chat(selected)
        if selected is not None and selected == self._controller.chat_id:
            self._chat.set_title(self._chats[selected]["title"])

    def _on_rename_chat(self, chat_id: int, title: str) -> None:
        try:
            self._database.rename_chat(chat_id, title)
        except FukaiError as exc:
            self.show_notice(exc.as_notice())
        self._on_chats_changed(self._controller.chat_id)


    def _on_delete_chat(self, chat_id: int) -> None:
        if self._controller.turn_chat_id == chat_id:
            self.show_notice(Notice.info(
                "Počas odpovede sa chat zmazať nedá.",
                hint="Najprv zastav generovanie tlačidlom v riadku na písanie."
            ))
            return
        try:
            self._database.delete_chat(chat_id)
        except FukaiError as exc:
            self.show_notice(exc.as_notice())
            return
        if self._controller.chat_id == chat_id:
            self.reload_chats()
            self._controller.new_chat()
        else:
            self._on_chats_changed(self._controller.chat_id)


    def _on_loading_started(self, model_title: str) -> None:
        notice = Notice.info("Načítavam model…", hint=f"{model_title} - prvé načítanie môže trvať aj desiatky sekúnd.")
        self._loading_toast = self.show_notice(notice, persistent=True)


    def _on_loading_finished(self) -> None:
        if self._loading_toast is not None:
            self._loading_toast.dismiss()
            self._loading_toast = None
    
    
    def _on_add_model(self) -> None:
        if self._library.importing:
            self.show_notice(Notice.info(
                "Import modelu už prebieha.",
                hint="Počkaj, kým sa dokončí, alebo ho zruš krížikom v jeho hlásení."
            ))
            return
        path, _ = QFileDialog.getOpenFileName(self, "Pridať model", str(Path.home()), "Modely GGUF (*.gguf)")
        if path:
            self.import_model(Path(path))
    
    
    def import_model(self, source: Path) -> None:
        try:
            existing = self._library.start_import(source)
        except FukaiError as exc:
            self.show_notice(exc.as_notice())
            return
        if existing is not None:
            self.show_notice(Notice.info("Tento model už v knižnici je.", hint=source.stem))
            self._select_imported(existing)
            return
        notice = Notice.info(f"Importujem {source.stem}", hint="Pripravujem kópiu…")
        self._import_toast = self.show_notice(notice, progress=True)
        self._import_toast.closed.connect(self._on_import_toast_closed)
    
    
    def _on_import_toast_closed(self, _toast: Toast) -> None:
        self._import_toast = None
        self._library.cancel_import()
    
    
    def _on_import_progress(self, copied: int, total: int) -> None:
        if self._import_toast is not None:
            mb = 1024 * 1024
            self._import_toast.set_progress(copied / total if total else 1.0, f"{size_text(copied / mb)} z {size_text(total / mb)}")
    
    
    def _close_import_toast(self) -> None:
        toast, self._import_toast = self._import_toast, None
        if toast is not None:
            toast.dismiss()
    
    
    def _on_import_finished(self, model_id: int, title: str) -> None:
        self._close_import_toast()
        self.show_notice(Notice.info("Model je pridaný do knižnice.", hint=title))
        self._select_imported(model_id)
        self._refresh_found_models()
    
    
    def _on_import_failed(self, error: FukaiError) -> None:
        self._close_import_toast()
        self.show_notice(error.as_notice())
    
    
    def _on_import_cancelled(self) -> None:
        self._close_import_toast()
        self.show_notice(Notice.info("Import modelu bol zrušený."))
    
    
    def _select_imported(self, model_id: int) -> None:
        if not self._controller.busy:
            self._controller.select_model(model_id)
    
    
    def _on_delete_model(self, model_id: int) -> None:
        model = next((m for m in self._library.models() if m["id"] == model_id), None)
        if model is None or not self._confirm_delete(model):
            return
        if self._controller.busy:
            self.show_notice(Notice.info("Počas odpovede sa model zmazať nedá."))
            return
        try:
            self._controller.release_model(model_id)
            self._library.delete_model(model_id)
        except FukaiError as exc:
            self.show_notice(exc.as_notice())
            return
        self._controller.model_deleted(model_id)
        self.show_notice(Notice.info("Model je zmazaný.", hint=model["title"]))
        self._refresh_found_models()
    
    
    def _confirm_delete(self, model: dict) -> bool:
        path = self._library.model_path(model)
        if path.is_symlink():
            text = f"Model „{model['title']}“ sa odstráni z knižnice. Zmaže sa len odkaz, pôvodný súbor zostane."
        elif model["size_mb"] is None:
            text = f"Model „{model['title']}“ sa odstráni zo zoznamu. Jeho súbor už na disku nie je."
        else:
            text = f"Model „{model['title']}“ sa odstráni z knižnice a jeho súbor sa zmaže z disku."
            
        box = QMessageBox(QMessageBox.Icon.Question, "Zmazať model", text, parent=self)
        box.setInformativeText("Chaty s týmto modelom zostanú - pred ďalšou správou v nich vyberieš iný model.")
        delete = box.addButton("Zmazať", QMessageBox.ButtonRole.DestructiveRole)
        cancel = box.addButton("Zrušiť", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(cancel)
        box.exec()
        return box.clickedButton() is delete


    def _on_theme_changed(self, theme: str) -> None:
        if theme == self._settings.current.theme:
            return
        try:
            self._settings.update(theme=theme)
        except FukaiError as exc:
            self.show_notice(exc.as_notice())
            self._settings_page.set_value(
                self._settings.current.theme,
                self._settings.current.web_search_enabled,
                self._settings.current.attachments_enabled
            )
            return
        self.theme_changed.emit(theme)


    def _on_attachments_changed(self, enabled: bool) -> None:
        if self._save_settings(attachments_enabled=enabled):
            self._chat.composer.set_features(enabled, self._settings.current.web_search_enabled)


    def _on_websearch_changed(self, enabled: bool) -> None:
        if self._save_settings(web_search_enabled=enabled):
            self._chat.composer.set_features(self._settings.current.attachments_enabled, enabled)
            self._sync_web()


    def _save_settings(self, **change) -> bool:
        try:
            self._settings.update(**change)
        except FukaiError as exc:
            self.show_notice(exc.as_notice())
            return False
        return True


    def _on_model_info(self, model: dict) -> None:
        try:
            meta = read_meta(self._library.model_path(model))
        except FukaiError as exc:
            self.show_notice(exc.as_notice())
            return
        ModelInfoDialog(model, meta, self._settings.current.theme, self).exec()


    def _on_properties_opened(self) -> None:
        self._refresh_properties()


    def _on_model_for_properties(self, _model: dict | None) -> None:
        if not self._properties_page.isHidden():
            self._refresh_properties()


    def _refresh_properties(self) -> None:
        chat_id = self._controller.chat_id
        try:
            props = self._controller.properties()
            chat = self._database.get_chat(chat_id) if chat_id is not None else None
        except FukaiError as exc:
            self.show_notice(exc.as_notice())
            props, chat = None, None
        model_id = self._controller.model_id
        model = next((m for m in self._library.models() if m["id"] == model_id), None)
        self._properties_page.load(
            props,
            chat_title=chat["title"] if chat is not None else None,
            model=model,
        )


    def _on_apply_properties(self, props) -> None:
        try:
            self._controller.apply_properties(props)
        except FukaiError as exc:
            self.show_notice(exc.as_notice())
            self._refresh_properties()
            return
        self._properties_page.confirm_applied()


    def _on_settings_opened(self) -> None:
        for notice in self._library.scan_folder():
            self.show_notice(notice)
        self._settings_page.set_models_dir(self._settings.current.models_dir)
        self._refresh_found_models()


    def _refresh_found_models(self) -> None:
        self._settings_page.set_models(self._library.models())


    def _on_open_folder(self) -> None:
        path = self._settings.current.models_dir
        try:
            ensure_dir(path)
        except OSError as exc:
            self.show_notice(Notice.warning(
                "Priečinok s modelmi sa nepodarilo otvoriť.",
                hint=str(path),
                detail=f"{type(exc).__name__}: {exc}"
            ))
            return
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path))):
            self.show_notice(Notice.warning(
                "Priečinok s modelmi sa nepodarilo otvoriť",
                hint=str(path)
            ))


    def _on_attach(self) -> None:
        patterns = " ".join(f"*{suffix}" for suffix in sorted(TEXT_SUFFIXES | {PDF_SUFFIX, XLSX_SUFFIX, DOCX_SUFFIX}))
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Pridať prílohu", str(Path.home()),
            f"Podporované súbory ({patterns});;Všetky súbory (*)"
        )
        self.add_attachments([Path(path) for path in paths])


    def add_attachments(self, paths: list[Path]) -> None:
        bar = self._chat.composer.attachments
        for path in paths:
            bar.add(self._attachments.extract(path), path.name)


    def _on_attachment_ready(self, job_id: int, item: Attachment) -> None:
        """Rozpočet sa kontroluje až tu - pred extrakciou sa nedá vedieť, koľko z neho
        príloha zje. Tokeny sú odhad (`dĺžka / 4`), presne ich spočíta až `build_prompt`."""
        bar = self._chat.composer.attachments
        budget = self._attachment_budget()
        cost = approx_tokens(item.text)
        if budget is not None and cost > budget:
            item = self._trim(item, budget)
            if item is None:
                bar.remove(job_id)
                self.show_notice(Notice.warning(
                    "Na prílohu už v kontexte nezostalo miesto.",
                    hint="Zväčši kontext vo Vlastnostiach alebo odober inú prílohu."
                ))
                return
            self.show_notice(Notice.warning(
                "Príloha sa do kontextu nezmestila celá, orezal som ju.",
                hint=f"{item.title}: z ~{int_text(cost)} tokenov zostalo ~{int_text(approx_tokens(item.text))}. "
                     "Celý text dostaneš, keď zväčšíš kontext vo Vlastnostiach a prílohu pridáš znova."
            ))
        bar.set_ready(job_id, item)


    @staticmethod
    def _trim(item: Attachment, budget: int) -> Attachment | None:
        """Oreže text na rozpočet. Ukladá sa to, čo naozaj pôjde modelu, takže náhľad
        ukazuje presne to, čo model dostane. Zvyšok sa po zväčšení kontextu nevráti sám -
        prílohu treba pridať znova."""
        room = budget * 4 - len(ATTACHMENT_CUT_NOTE)         # odhad tokenu je dĺžka / 4
        if room <= 0:
            return None
        cut = item.text[:room]
        end = cut.rfind("\n")
        return Attachment(item.title, (cut[:end] if end > room // 2 else cut) + ATTACHMENT_CUT_NOTE, True)


    def _on_send(self, text: str) -> None:
        bar = self._chat.composer.attachments
        if bar.pending():
            self.show_notice(Notice.info("Počkaj, kým sa príloha spracuje."))
            return
        self._controller.send(text, bar.attachments())


    def _on_attachment_failed(self, job_id: int, error: FukaiError) -> None:
        self._chat.composer.attachments.remove(job_id)
        self.show_notice(error.as_notice())


    def _on_history_preview(self, attachment_id: int) -> None:
        """Text príloh sa pri otvorení chatu nenačítava (12a), dotiahne sa až tu."""
        try:
            row = self._database.get_attachment(attachment_id)
        except FukaiError as exc:
            self.show_notice(exc.as_notice())
            return
        if row is not None:
            TextPreviewDialog(row["title"], row["content"], self._settings.current.theme, self).exec()


    def _on_preview(self, item) -> None:
        TextPreviewDialog(item.title, item.text, self._settings.current.theme, self).exec()


    def _attachment_budget(self) -> int | None:
        try:
            props = self._controller.properties()
        except FukaiError as exc:
            self.show_notice(exc.as_notice())
            return None
        if props is None:
            return None
        budget = props.load.n_ctx - props.sampling.max_tokens - PROMPT_RESERVE
        if props.chat.system_prompt:
            budget -= approx_tokens(props.chat.system_prompt)
        question = self._chat.composer.text()
        if question:
            budget -= approx_tokens(question)
        for ready in self._chat.composer.attachments.attachments():
            budget -= approx_tokens(ready.text)
        return budget


    def _sync_web(self) -> None:
        """Tlačidlo Web ukazuje vlastnosť zobrazeného chatu (sticky, §7.2). Po výmene modelu
        sa vlastnosti resetujú (§7.1), takže sa vypne aj prepínač."""
        if not self._settings.current.web_search_enabled:
            return
        try:
            on = self._controller.web_search()
        except FukaiError as exc:
            self.show_notice(exc.as_notice())
            on = False
        self._chat.composer.set_web(on)


    def _on_web_toggled(self, on: bool) -> None:
        try:
            stored = self._controller.set_web_search(on)
        except FukaiError as exc:
            self.show_notice(exc.as_notice())
            stored = False
        if not stored:
            if on:
                self.show_notice(Notice.info("Najprv vyber model.",
                                             hint="Hľadanie na webe je vlastnosť chatu - bez modelu ho nemá kam uložiť."))
            self._sync_web()
