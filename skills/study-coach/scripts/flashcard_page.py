import html
import json

_LABELS = {
    "es": {"got_it": "La sé", "missed_it": "No la sé", "download": "Descargar resultados", "points": "Puntos", "streak": "Racha"},
    "en": {"got_it": "Got it", "missed_it": "Missed it", "download": "Download results", "points": "Points", "streak": "Streak"},
}

_FLASHCARD_SCRIPT = """
var marks = {};

function flip(cardId) {
  document.querySelector('[data-card-id="' + cardId + '"]').classList.toggle("flipped");
}

function mark(cardId, result) {
  marks[cardId] = result;
  var points = 0;
  var streak = 0;
  var bestStreak = 0;
  Object.values(marks).forEach(function (r) {
    if (r === "correct") {
      points += 1;
      streak += 1;
      bestStreak = Math.max(bestStreak, streak);
    } else {
      streak = 0;
    }
  });
  document.getElementById("points-display").textContent = points;
  document.getElementById("streak-display").textContent = bestStreak;
}

function downloadResults() {
  var deck = JSON.parse(document.getElementById("deck-data").textContent);
  var results = Object.keys(marks).map(function (cardId) {
    return { card_id: cardId, result: marks[cardId] };
  });
  var blob = new Blob([JSON.stringify(results)], { type: "application/json" });
  var link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = deck.deck_id + "-results.json";
  link.click();
}
""".strip()


def _render_card(card, labels):
    prompt = html.escape(card["prompt"])
    answer = html.escape(card["answer"])
    card_id = card["card_id"]
    return (
        f'<div class="card" data-card-id="{card_id}" onclick="flip(\'{card_id}\')">'
        f'<div class="front">{prompt}</div><div class="back">{answer}</div></div>'
        f'<button onclick="mark(\'{card_id}\', \'correct\')">{html.escape(labels["got_it"])}</button>'
        f'<button onclick="mark(\'{card_id}\', \'incorrect\')">{html.escape(labels["missed_it"])}</button>'
    )


def render_flashcard_html(deck, language="es"):
    labels = _LABELS[language]
    cards_html = "".join(_render_card(card, labels) for card in deck["cards"])
    # Escape "</" so a card's own text can never prematurely close the
    # #deck-data script tag; \/ is a valid JSON escape, so json.loads still
    # round-trips to the exact original deck dict.
    deck_json = json.dumps(deck).replace("</", "<\\/")

    return f"""<!doctype html>
<html lang="{language}">
<head><meta charset="utf-8"><title>{html.escape(deck["deck_id"])}</title></head>
<body>
<script type="application/json" id="deck-data">{deck_json}</script>
<p>{html.escape(labels["points"])}: <span id="points-display">0</span> | {html.escape(labels["streak"])}: <span id="streak-display">0</span></p>
{cards_html}
<button onclick="downloadResults()">{html.escape(labels["download"])}</button>
<script>{_FLASHCARD_SCRIPT}</script>
</body>
</html>"""
