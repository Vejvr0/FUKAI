from __future__ import annotations
from dataclasses import dataclass, field
from PyQt6.QtCore import QObject, pyqtSignal
from core.context import HistoryItem
from core.hardware import HardwareProfile
from core.llm_engine import FinishReason
from core.settings import ChatProperties, LoadParams, ModelMeta
from core.errors import FukaiError, Notice
from storage.database import Database
from ui.constants import TITLE_WORDS, NEW_CHAT_TITLE
from ui.llm_service import LlmService
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
    request_id: int | None = None
    parts: list[str] = field(default_factory=list)


class ChatController(QObject):
    busy_changed = pyqtSignal(bool)
    chat_opened = pyqtSignal(object, str, object)
    chats_changed = pyqtSignal(object)
    loading_started = pyqtSignal(str)
    loading_finished = pyqtSignal()
    turn_started = pyqtSignal(str)
    token = pyqtSignal(str)
    turn_finished = pyqtSignal(object)
    turn_rolled_back = pyqtSignal(str)
    notice = pyqtSignal(object)
    model_changed = pyqtSignal(object)


    def __init__(self, settings: SettingsStore, hardware: HardwareProfile, database: Database, llm: LlmService, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._hardware = hardware
        self._database = database
        self._llm = llm
        
        self._view = 0
        self._chat_id: int | None = None
        self._model_id: int | None = settings.current.last_model_id
        self._turn: _Turn | None = None
        self._loaded: LoadParams | None = None
        
        llm.loaded.connect(self._on_loaded)
        llm.load_failed.connect(self._on_load_failed)
        llm.token.connect(self._on_token)
        llm.finished.connect(self._on_finished)
        llm.failed.connect(self._on_failed)
    
    
    @property
    def busy(self) -> bool:
        return self._turn is not None

    
    @property
    def chat_id(self) -> int | None:
        return self._chat_id
    
    
    @property
    def model_id(self) -> int | None:
        return self._model_id
    
    
    def _visible(self, turn: _Turn) -> bool:
        if turn.view == self._view:
            return True
        return turn.chat_id is not None and turn.chat_id == self._chat_id
    
    
    def new_chat(self) -> None:
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
            self.turn_started.emit(turn.question)
            if turn.parts:
                self.token.emit("".join(turn.parts))
    
    
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
            self._emit_model()
            
    
    def send(self, text: str) -> None:
        if self.busy:
            raise RuntimeError("ChatController je zaneprázdnený - počkaj na busy_changed(False)")
        question = text.strip()
        if not question:
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
                props = self._defaults(model)
                history: list[HistoryItem] = []
            else:
                props = ChatProperties.from_dict(self._database.get_properties(self._chat_id) or {}, self._model_path(model))
                history = [HistoryItem(m["id"], m["role"], m["data"].get("text", ""), m["tokens"]) for m in self._database.get_messages(self._chat_id)]
        except FukaiError as exc:
            self.notice.emit(exc.as_notice())
            return

        self._turn = _Turn(self._view, self._chat_id, model["id"], model["title"], props, question, history)
        self.busy_changed.emit(True)
        self.turn_started.emit(question)

        if self._loaded is None or self._loaded.clamped() != props.load.clamped():
            self.loading_started.emit(model["title"])
            self._llm.load(props.load)
        else:
            self._generate()
    
    
    def stop(self) -> None:
        if self._turn is not None:
            self._llm.stop()


    def _generate(self) -> None:
        turn = self._turn
        turn.request_id = self._llm.generate(
            turn.history, turn.question,
            sampling=turn.props.sampling,
            system_prompt=turn.props.chat.system_prompt
        )
    
    
    def _on_loaded(self, notices: list[Notice]) -> None:
        self.loading_finished.emit()
        for notice in notices:
            self.notice.emit(notice)
        turn = self._turn
        self._loaded = turn.props.load
        self._database.mark_model_used(turn.model_id)
        self._generate()
    
    
    def _on_load_failed(self, error: FukaiError) -> None:
        self.loading_finished.emit()
        self._loaded = None
        self.notice.emit(error.as_notice())
        self._roll_back()


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
        new_chat = None
        if turn.chat_id is None:
            new_chat = (turn.model_id, self._title(turn.question), turn.props.to_dict())
        try:
            chat_id = self._database.add_turn(turn.chat_id, {"text": turn.question}, answer,
                                        answer_tokens=result.completion_tokens, new_chat=new_chat)
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
    def _title(question: str) -> str:
        return " ".join(question.split()[:TITLE_WORDS])
