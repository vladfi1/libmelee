"""Certain character/stage combinations cause memory issues in ffw mode."""

from typing import Set

from melee.enums import Character, Stage

# p1, p2, stage
# TODO: move into an actual csv?
bad_ffw_combinations_csv = """
FOX,FOX,YOSHIS_STORY
FOX,FALCO,YOSHIS_STORY
FOX,MARTH,YOSHIS_STORY
FOX,SHEIK,YOSHIS_STORY
FOX,CPTFALCON,YOSHIS_STORY
FOX,JIGGLYPUFF,YOSHIS_STORY
FOX,PEACH,YOSHIS_STORY
FALCO,SHEIK,YOSHIS_STORY
FALCO,CPTFALCON,YOSHIS_STORY
CPTFALCON,FOX,FINAL_DESTINATION
CPTFALCON,FOX,FOUNTAIN_OF_DREAMS
CPTFALCON,FALCO,FINAL_DESTINATION
CPTFALCON,FALCO,FOUNTAIN_OF_DREAMS
CPTFALCON,MARTH,FINAL_DESTINATION
CPTFALCON,MARTH,FOUNTAIN_OF_DREAMS
CPTFALCON,SHEIK,FINAL_DESTINATION
CPTFALCON,SHEIK,FOUNTAIN_OF_DREAMS
CPTFALCON,JIGGLYPUFF,FINAL_DESTINATION
CPTFALCON,JIGGLYPUFF,FOUNTAIN_OF_DREAMS
CPTFALCON,PEACH,FINAL_DESTINATION
CPTFALCON,PEACH,FOUNTAIN_OF_DREAMS
""".strip()

name_to_char = {c.name: c for c in Character}
name_to_stage = {s.name: s for s in Stage}

BAD_FFW_COMBINATIONS: Set[tuple[Character, Character, Stage]] = set()
BAD_FFW_COMBINATIONS_ANY_STAGE: Set[tuple[Character, Character]] = set()
for _line in bad_ffw_combinations_csv.split('\n'):
  p1, p2, stage = _line.split(',')
  c1 = name_to_char[p1]
  c2 = name_to_char[p2]
  BAD_FFW_COMBINATIONS.add((c1, c2, name_to_stage[stage]))
  BAD_FFW_COMBINATIONS_ANY_STAGE.add((c1, c2))

def is_bad_ffw_combination(
    p1: Character,
    p2: Character,
    stage: Stage,
) -> bool:
  if stage is Stage.RANDOM_STAGE:
    return (p1, p2) in BAD_FFW_COMBINATIONS_ANY_STAGE
  return (p1, p2, stage) in BAD_FFW_COMBINATIONS

# It's a bit hard to automate this check because the console object doesn't
# know what characters you'll pick.
def check_ffw_combination(
    p1: Character,
    p2: Character,
    stage: Stage,
) -> bool:
  if is_bad_ffw_combination(p1, p2, stage):
    raise ValueError(
        'The given character/stage combination is known to '
        'cause issues with fast-forward mode.')
