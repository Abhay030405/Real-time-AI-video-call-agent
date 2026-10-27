"""Fixed lines spoken by code, not written by the AI, because they must be the same every time.

The helpline line guarantees that a crisis reply carries the numbers even if the AI leaves
them out. The age line is kind, plain and identical for everyone (V0_02 section 8).
"""

HELPLINE_LINE = (
    "If you are in immediate danger, please call 112 right now. You can also call Tele-MANAS "
    "on 14416, it is free and open any time, anywhere in India. I am here with you."
)

ADVICE_LINE = (
    "I can't advise on that. A doctor or pharmacist, a lawyer, or a financial adviser is the "
    "right person to ask, and I would not want to steer you wrong."
)

AGE_ENDING_LINE = (
    "I have really enjoyed talking with you. This space is only for adults, so I need to say "
    "goodbye here. Please look after yourself, and talk to someone you trust if anything is "
    "on your mind. Take care."
)

# When the person who seems under 18 is also in distress, the helplines come first.
AGE_ENDING_WITH_HELPLINES = HELPLINE_LINE + " " + AGE_ENDING_LINE
