from __future__ import annotations
from dataclasses import dataclass, field, replace
from PyQt6.QtCore import QObject, pyqtSignal
from core.context import HistoryItem, with_attachments
from core.hardware import HardwareProfile
from core.llm_engine import FinishReason
from core.settings import ChatProperties, LoadParams, ModelMeta
from core.errors import FukaiError, Notice
from storage.database import Database
from ui.constants import TITLE_WORDS, NEW_CHAT_TITLE
from ui.llm_service import LlmService
from ui.web_service import WebService
from ui.workers import GenerationResult
from ui.settings_store import SettingsStore

__all__ = ["ChatController"]


@dataclass
class _Turn:
    view: int
    chat_id: int | None
    model_id: int
    model_title: str
    props: ChatProperties
    question: str
    history: list[HistoryItem]
    attachments: list = field(default_factory=list)
    request_id: int | None = None
    parts: list[str] = field(default_factory=list)
    loading: bool = False
    web_job: int | None = None
    web_query: str | None = None
    sources: list = field(default_factory=list)
    web_status: str = ""                    # posledný priebeh - pre návrat do chatu počas hľadania


class ChatController(QObject):
    busy_changed = pyqtSignal(bool)
    chat_opened = pyqtSignal(object, str, object)
    chats_changed = pyqtSignal(object)
    loading_started = pyqtSignal(str)
    loading_finished = pyqtSignal()
    turn_started = pyqtSignal(str, object, bool)     # otázka, prílohy, web
    token = pyqtSignal(str)
    turn_finished = pyqtSignal(object)
    turn_rolled_back = pyqtSignal(str)
    notice = pyqtSignal(object)
    model_changed = pyqtSignal(object)
    web_progress = pyqtSignal(str)


    def __init__(self, settings: SettingsStore, hardware: HardwareProfile, database: Database, llm: LlmService, web: WebService, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._hardware = hardware
        self._database = database
        self._llm = llm
        self._web = web
        
        self._view = 0
        self._chat_id: int | None = None
        self._model_id: int | None = settings.current.last_model_id
        self._turn: _Turn | None = None
        self._loaded: LoadParams | None = None
        self._draft: ChatProperties | None = None
        
        llm.loaded.connect(self._on_loaded)
        llm.load_failed.connect(self._on_load_failed)
        llm.token.connect(self._on_token)
        llm.finished.connect(self._on_finished)
        llm.failed.connect(self._on_failed)
        
        web.progress.connect(self._on_web_progress)
        web.ready.connect(self._on_web_ready)
        web.failed.connect(self._on_web_failed)
    
    
    @property
    def busy(self) -> bool:
        return self._turn is not None

    
    @property
    def chat_id(self) -> int | None:
        return self._chat_id
    
    
    @property
    def model_id(self) -> int | None:
        return self._model_id


    @property
    def turn_chat_id(self) -> int | None:
        return self._turn.chat_id if self._turn is not None else None
    
    
    def _visible(self, turn: _Turn) -> bool:
        if turn.view == self._view:
            return True
        return turn.chat_id is not None and turn.chat_id == self._chat_id
    
    
    def new_chat(self) -> None:
        if self._chat_id is not None:
            self._draft = None
        self._view += 1
        self._chat_id = None
        self._model_id = self._settings.current.last_model_id
        self.chat_opened.emit(None, NEW_CHAT_TITLE, [])
        self._emit_model()
    
    
    def open_chat(self, chat_id: int) -> None:
        chat = self._database.get_chat(chat_id)
        
        if chat is None:
            self.notice.emit(Notice.warning("Chat už neexistuje."))
            self.chats_changed.emit(None)
            return
        self._view += 1
        self._chat_id = chat_id
        self._model_id = chat["model_id"]
        self.chat_opened.emit(chat_id, chat["title"], self._database.get_messages(chat_id))
        self._emit_model()
        
        turn = self._turn
        if turn is not None and turn.chat_id == chat_id:
            self.turn_started.emit(turn.question, [{"title": a.title} for a in turn.attachments],
                                   turn.web_query is not None)
            if turn.parts:
                self.token.emit("".join(turn.parts))
            elif turn.web_status:
                self.web_progress.emit(turn.web_status)
    
    
    def select_model(self, model_id: int) -> None:
        if self.busy:
            raise RuntimeError("model sa počas generovania meniť nedá")
        model = self._database.get_model(model_id)
        if model is None:
            raise ValueError(f"model {model_id} neexistuje")
        if model_id == self._model_id:
            return
        try:
            if self._chat_id is not None:
                self._database.set_model(self._chat_id, model_id, self._defaults(model).to_dict())
            self._draft = None
            self._model_id = model_id
            self._settings.update(last_model_id=model_id)
        except FukaiError as exc:
            self.notice.emit(exc.as_notice())
        self._emit_model()
    
    
    def release_model(self, model_id: int) -> None:
        if self.busy:
            raise RuntimeError("model sa počas generovania mazať nedá")
        model = self._database.get_model(model_id)
        if model is not None and self._loaded is not None and self._loaded.model_path == self._model_path(model):
            self._llm.unload()
            self._loaded = None
    
    
    def model_deleted(self, model_id: int) -> None:
        if self._settings.current.last_model_id == model_id:
            try:
                self._settings.update(last_model_id=None)
            except FukaiError as exc:
                self.notice.emit(exc.as_notice())
        if self._model_id == model_id:
            self._model_id = None
            self._draft = None
            self._emit_model()
            
    
    def properties(self) -> ChatProperties | None:
        model = self._database.get_model(self._model_id) if self._model_id is not None else None
        if model is None:
            return None
        if self._chat_id is None:
            if self._draft is None:
                self._draft = self._defaults(model)
            return self._draft
        return ChatProperties.from_dict(
            self._database.get_properties(self._chat_id) or {}, self._model_path(model)
        )


    def web_search(self) -> bool:
        """Stav prepínača Web v zobrazenom chate (sticky, §7.2). Bez modelu nie sú vlastnosti → vypnutý."""
        props = self.properties()
        return props is not None and props.chat.web_search


    def set_web_search(self, on: bool) -> bool:
        """Zapíše prepínač do vlastností chatu, v novom chate do draftu. False = niet kam
        zapísať (chat bez modelu). Počas ťahu sa nemení - zapisoval by sa do vlastností,
        ktoré ťah už má prečítané, a nový chat by vznikol so starými."""
        if self.busy:
            raise RuntimeError("prepínač webu sa počas generovania meniť nedá")
        props = self.properties()
        if props is None:
            return False
        if props.chat.web_search != on:
            self.apply_properties(replace(props, chat=replace(props.chat, web_search=on)))
        return True


    def apply_properties(self, props: ChatProperties) -> None:
        if self._chat_id is None:
            self._draft = props
            return
        self._database.set_properties(self._chat_id, props.to_dict())


    def send(self, text: str, attachments: list | None = None) -> None:
        if self.busy:
            raise RuntimeError("ChatController je zaneprázdnený - počkaj na busy_changed(False)")
        question = text.strip()
        attachments = list(attachments or ())
        if not question and not attachments:
            return
        model = self._database.get_model(self._model_id) if self._model_id is not None else None
        if model is None:
            self.notice.emit(Notice.warning(
                "Najprv vyber model.",
                hint="Model sa vyberá tlačidlom v riadku na písanie.")
            )
            return

        try:
            if self._chat_id is None:
                props = self._draft or self._defaults(model)
                history: list[HistoryItem] = []
            else:
                props = ChatProperties.from_dict(self._database.get_properties(self._chat_id) or {}, self._model_path(model))
                history = self._history(self._chat_id)
        except FukaiError as exc:
            self.notice.emit(exc.as_notice())
            return

        turn = _Turn(self._view, self._chat_id, model["id"], model["title"], props, question, history, attachments)
        self._turn = turn
        # Hľadanie a načítanie modelu bežia naraz, generuje sa až keď sú hotové obe.
        if question and props.chat.web_search and self._settings.current.web_search_enabled:
            turn.web_query = question
            turn.web_job = self._web.search(question)
        self.busy_changed.emit(True)
        self.turn_started.emit(question, [{"title": item.title} for item in attachments],
                               turn.web_query is not None)

        if self._loaded is None or self._loaded.clamped() != props.load.clamped():
            turn.loading = True
            self.loading_started.emit(model["title"])
            self._llm.load(props.load)
        else:
            self._generate_when_ready()
    
    
    def stop(self) -> None:
        turn = self._turn
        if turn is None:
            return
        if turn.request_id is not None:
            self._llm.stop()
        elif not turn.loading:
            self._roll_back()


    def _history(self, chat_id: int) -> list[HistoryItem]:
        files = self._database.get_attachments(chat_id, content=True)
        history = []
        for message in self._database.get_messages(chat_id):
            text = message["data"].get("text", "")
            attached = [(row["title"], row["content"]) for row in files.get(message["id"], ())]
            history.append(HistoryItem(message["id"], message["role"], with_attachments(text, attached), message["tokens"]))
        return history
    
    
    def _generate_when_ready(self) -> None:
        turn = self._turn
        if turn is None or turn.loading or turn.web_job is not None or turn.request_id is not None:
            return
        self._generate()


    def _generate(self) -> None:
        turn = self._turn
        turn.request_id = self._llm.generate(
            turn.history, with_attachments(turn.question, [(a.title, a.text) for a in turn.attachments]),
            sampling=turn.props.sampling,
            system_prompt=turn.props.chat.system_prompt,
            web=[(s.n, s.title, s.url, s.text) for s in turn.sources]
        )
    
    
    def _on_loaded(self, notices: list[Notice]) -> None:
        self.loading_finished.emit()
        for notice in notices:
            self.notice.emit(notice)
        turn = self._turn
        if turn is None:
            self._loaded = None
            return
        turn.loading = False
        self._loaded = turn.props.load
        self._database.mark_model_used(turn.model_id)
        self._generate_when_ready()
    
    
    def _on_load_failed(self, error: FukaiError) -> None:
        self.loading_finished.emit()
        self._loaded = None
        self.notice.emit(error.as_notice())
        self._roll_back()
        
    
    def _web_turn(self, job_id: int) -> _Turn | None:
        turn = self._turn
        return turn if turn is not None and turn.web_job == job_id else None
    
    
    def _on_web_progress(self, job_id: int, text: str) -> None:
        turn = self._web_turn(job_id)
        if turn is None:
            return
        turn.web_status = text
        if self._visible(turn):
            self.web_progress.emit(text)


    def _web_done(self, turn: _Turn) -> None:
        turn.web_job = None
        turn.web_status = ""
        if self._visible(turn):
            self.web_progress.emit("")      # stav v bubline zmizne, ďalej čaká už len na model
    
    
    def _on_web_ready(self, job_id: int, sources: list) -> None:
        turn = self._web_turn(job_id)
        if turn is None:
            return
        self._web_done(turn)
        turn.sources = list(sources)
        self._generate_when_ready()
    
    
    def _on_web_failed(self, job_id: int, error: FukaiError) -> None:
        turn = self._web_turn(job_id)
        if turn is None:
            return
        self._web_done(turn)
        self.notice.emit(error.as_notice())
        self._generate_when_ready()


    def _on_token(self, request_id: int, piece: str) -> None:
        turn = self._turn
        if turn is None or turn.request_id != request_id:
            return
        turn.parts.append(piece)
        if self._visible(turn):
            self.token.emit(piece)
    
    
    def _on_finished(self, request_id: int, result: GenerationResult) -> None:
        turn = self._turn
        if turn is None or turn.request_id != request_id:
            return
        try:
            self._database.set_message_tokens(result.counted)
        except FukaiError as exc:
            self.notice.emit(exc.as_notice())

        if result.finish_reason is FinishReason.STOPPED or not result.text:
            self._roll_back()
            return

        answer = {
            "text": result.text,
            "model_id": turn.model_id,
            "model": turn.model_title,
            "finish_reason": result.finish_reason.value,
            "stats": {
                "prompt_tokens": result.prompt_tokens,
                "completion_tokens": result.completion_tokens,
                "first_token_s": result.first_token_s,
                "total_s": result.total_s,
                "tokens_per_s": result.tokens_per_s,
            },
            "dropped": result.dropped,
        }
        # Ukladá sa len dopyt a zdroje, ktoré model naozaj dostal - text stránok žije len v ťahu
        # (rozhodnutie autora). Otázka nesie príznak pre čip „Web“, aj keď hľadanie zlyhalo.
        used = set(result.web_used)
        if used:
            answer["web"] = {
                "query": turn.web_query,
                "sources": [{"n": s.n, "title": s.title, "url": s.url} for s in turn.sources if s.n in used],
            }
        question_data = {"text": turn.question}
        if turn.web_query is not None:
            question_data["web"] = True
        files = [{"title": item.title, "content": item.text} for item in turn.attachments]
        new_chat = None
        if turn.chat_id is None:
            new_chat = (turn.model_id, self._title(turn), turn.props.to_dict())
        try:
            chat_id = self._database.add_turn(turn.chat_id, question_data, answer,
                                        answer_tokens=result.completion_tokens, new_chat=new_chat,
                                        attachments=files)
        except FukaiError as exc:
            self.notice.emit(exc.as_notice())
            self._roll_back()
            return

        visible = self._visible(turn)
        if visible and turn.chat_id is None:
            self._chat_id = chat_id
        self._turn = None
        self.busy_changed.emit(False)
        if visible:
            self.turn_finished.emit(answer)
        if turn.sources and not result.web_used and visible:
            self.notice.emit(Notice.info(
                "Výsledky z webu sa do kontextu nezmestili.",
                hint="Odpoveď je bez nich. Zväčši kontext vo Vlastnostiach alebo zníž maximálny počet tokenov odpovede.")
            )
        if result.dropped and visible:
            self.notice.emit(Notice.info(
                "Staršie správy sa do kontextu modelu nezmestili.",
                hint=f"Vynechaných správ: {len(result.dropped)}.")
            )
        self.chats_changed.emit(self._chat_id)
    
    
    def _on_failed(self, request_id: int, error: FukaiError) -> None:
        turn = self._turn
        if turn is None or turn.request_id != request_id:
            return
        self.notice.emit(error.as_notice())
        self._roll_back()


    def _roll_back(self) -> None:
        turn, self._turn = self._turn, None
        if turn is not None and turn.web_job is not None:
            self._web.cancel(turn.web_job)
        self.busy_changed.emit(False)
        if turn is not None and self._visible(turn):
            self.turn_rolled_back.emit(turn.question)
            
    
    def _model_path(self, model: dict):
        return self._settings.current.models_dir / model["path"]
    
    
    def _emit_model(self) -> None:
        model = self._database.get_model(self._model_id) if self._model_id is not None else None
        self.model_changed.emit(model)


    def _defaults(self, model: dict) -> ChatProperties:
        meta = ModelMeta.from_dict(model["meta"]) if model.get("meta") else None
        return ChatProperties.defaults_for(self._model_path(model), self._hardware, meta=meta)


    @staticmethod
    def _title(turn: _Turn) -> str:
        title = " ".join(turn.question.split()[:TITLE_WORDS])
        if title:
            return title
        return turn.attachments[0].title if turn.attachments else NEW_CHAT_TITLE
