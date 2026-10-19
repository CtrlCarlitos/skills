import html
import json

_LABELS = {
    "es": {"got_it": "La sé", "missed_it": "No la sé", "download": "Descargar resultados", "points": "Puntos", "streak": "Racha"},
    "en": {"got_it": "Got it", "missed_it": "Missed it", "download": "Download results", "points": "Points", "streak": "Streak"},
}

_STYLE = ".card .back{display:none} .card.flipped .back{display:block} .card.flipped .front{display:none}"

_FLASHCARD_SCRIPT = """
var marksByIndex = {};
var points = 0;
var streak = 0;

function mark(index, cardId, result) {
  marksByIndex[index] = { cardId: cardId, result: result };
  if (result === "correct") {
    points += 1;
    streak += 1;
  } else {
    streak = 0;
  }
  document.getElementById("points-display").textContent = points;
  document.getElementById("streak-display").textContent = streak;
}

function downloadResults() {
  var deck = JSON.parse(document.getElementById("deck-data").textContent);
  // A resurfaced card can appear more than once (one DOM index per
  // appearance); a miss on any appearance marks that card_id incorrect
  // overall, since that is the signal resurfacing exists to catch.
  var aggregated = {};
  Object.keys(marksByIndex).forEach(function (index) {
    var entry = marksByIndex[index];
    if (aggregated[entry.cardId] !== "incorrect") {
      aggregated[entry.cardId] = entry.result;
    }
  });
  var results = Object.keys(aggregated).map(function (cardId) {
    return { card_id: cardId, result: aggregated[cardId] };
  });
  var blob = new Blob([JSON.stringify({ deck_id: deck.deck_id, results: results })], { type: "application/json" });
  var link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = deck.deck_id + "-results.json";
  link.click();
}
""".strip()


def _render_card(card, labels, index):
    prompt = html.escape(card["prompt"])
    answer = html.escape(card["answer"])
    card_id = card["card_id"]
    return (
        f'<div class="card" data-card-id="{card_id}" data-card-index="{index}" onclick="this.classList.toggle(\'flipped\')">'
        f'<div class="front">{prompt}</div><div class="back">{answer}</div></div>'
        f'<button onclick="mark({index}, \'{card_id}\', \'correct\')">{html.escape(labels["got_it"])}</button>'
        f'<button onclick="mark({index}, \'{card_id}\', \'incorrect\')">{html.escape(labels["missed_it"])}</button>'
    )


def render_flashcard_html(deck, language="es"):
    labels = _LABELS[language]
    cards_html = "".join(_render_card(card, labels, index) for index, card in enumerate(deck["cards"]))
    # Escape "</" so a card's own text can never prematurely close the
    # #deck-data script tag; \/ is a valid JSON escape, so json.loads still
    # round-trips to the exact original deck dict.
    deck_json = json.dumps(deck).replace("</", "<\\/")

    return f"""<!doctype html>
<html lang="{language}">
<head><meta charset="utf-8"><title>{html.escape(deck["deck_id"])}</title><style>{_STYLE}</style></head>
<body>
<script type="application/json" id="deck-data">{deck_json}</script>
<p>{html.escape(labels["points"])}: <span id="points-display">0</span> | {html.escape(labels["streak"])}: <span id="streak-display">0</span></p>
{cards_html}
<button onclick="downloadResults()">{html.escape(labels["download"])}</button>
<script>{_FLASHCARD_SCRIPT}</script>
</body>
</html>"""
