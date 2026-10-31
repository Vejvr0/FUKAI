import threading, time
from core.llm_engine import LlmEngine
from core.settings import LoadParams, SamplingParams
from core.hardware import detect
from core.errors import ContextOverflowError

e = LlmEngine()
e.load(LoadParams.for_hardware("models/gemma-3-4b-it-Q4_K_M.gguf", detect(), n_ctx=256))

# 1. preplnený kontext
try:
    for _ in e.stream([{"role": "user", "content": "ovca " * 400}], SamplingParams()):
        pass
except ContextOverflowError as exc:
    print("overflow:", exc.message)        # overflow: Správa je príliš dlhá na nastavenú dĺžku kontextu.

# 2. unload počká na koniec odpovede
g = e.stream([{"role": "user", "content": "Napíš vetu o ovciach."}], SamplingParams(max_tokens=40))
next(g)                                    # generovanie beží, zámok je držaný
t = threading.Thread(target=e.unload)
t.start()
time.sleep(0.5)
print("unload čaká:", t.is_alive())        # unload čaká: True
for _ in g:
    pass                                   # dobehne → zámok sa uvoľní
t.join()
print("po odpovedi:", e.is_loaded)         # po odpovedi: False