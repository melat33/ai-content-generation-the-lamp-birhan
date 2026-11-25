# One command for the whole film:   make film
# Offline demo (placeholders, no keys): make demo
PY ?= python3

.PHONY: setup validate smoke film demo radio narration keyframes ambience music shots assemble test clean

setup:
	$(PY) -m pip install -r requirements.txt

validate:
	$(PY) pipeline/validate.py

smoke:
	$(PY) pipeline/smoke_test.py

narration: validate
	$(PY) pipeline/narration.py

keyframes: validate
	$(PY) pipeline/keyframes.py

shots: keyframes narration
	$(PY) pipeline/shots.py

ambience: narration
	$(PY) pipeline/ambience.py

music: narration
	$(PY) pipeline/music.py

radio: narration music
	$(PY) pipeline/radio_cut.py

assemble: shots ambience music
	$(PY) pipeline/assemble.py

# The whole pipeline from a clean clone (needs keys in .env, see README)
film: validate narration keyframes shots ambience music assemble

# Placeholders for every model stage, so the pipeline and the edit run with no keys.
demo:
	DEMO=1 $(MAKE) film

test:
	$(PY) -m pytest -q tests

clean:
	rm -rf outputs/build outputs/final
