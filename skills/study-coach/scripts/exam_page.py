import html
import json
import random

from scripts.exam_schema import QUESTION_TYPES, validate_correct_answer_shape

_LABELS = {
    "es": {
        "true": "Verdadero", "false": "Falso", "download": "Descargar resultados", "choose": "-- elige --",
        "show_results": "Ver resultados", "practice_banner": "Práctica: esto no cuenta",
    },
    "en": {
        "true": "True", "false": "False", "download": "Download results", "choose": "-- choose --",
        "show_results": "Show my results", "practice_banner": "Practice: this doesn't count",
    },
}

_SELF_GRADING_SCRIPT = """
function normalize(value) {
  return typeof value === "string" ? value.trim().toLowerCase() : value;
}

function readAnswer(question) {
  var el = document.querySelector('[data-question-id="' + question.question_id + '"]');
  if (question.type === "fill_in_blank") {
    return el.querySelector("input").value;
  }
  if (question.type === "open_response") {
    return el.querySelector("textarea").value;
  }
  if (question.type === "matching") {
    var answer = {};
    el.querySelectorAll("select").forEach(function (select) {
      answer[select.dataset.left] = select.value;
    });
    return answer;
  }
  var checked = el.querySelector("input:checked");
  if (!checked) {
    return null;
  }
  if (question.type === "true_false") {
    return checked.value === "true";
  }
  // multiple_choice / single_select: the radio's value is the option's
  // index, mapped back to the original (correctly-typed) option value.
  return question.options[parseInt(checked.value, 10)];
}

function gradeAnswer(question, givenAnswer) {
  if (question.type === "open_response") {
    return null;
  }
  if (question.type === "fill_in_blank") {
    var accepted = question.correct_answer || [];
    return accepted.some(function (a) { return normalize(a) === normalize(givenAnswer); });
  }
  return JSON.stringify(givenAnswer) === JSON.stringify(question.correct_answer);
}
""".strip()

_DOWNLOAD_RESULTS_SCRIPT = """
function downloadResults() {
  var exam = JSON.parse(document.getElementById("exam-data").textContent);
  var results = exam.questions.map(function (question) {
    var givenAnswer = readAnswer(question);
    return {
      question_id: question.question_id,
      given_answer: givenAnswer,
      correct: gradeAnswer(question, givenAnswer),
    };
  });
  var blob = new Blob([JSON.stringify(results)], { type: "application/json" });
  var link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = exam.exam_id + "-results.json";
  link.click();
}
""".strip()

# Practice mode shares readAnswer/gradeAnswer above, but never creates a
# Blob or a downloadable file -- a practice attempt has no mechanism that
# could reach the real exam_history.json/dashboard, by construction.
_PRACTICE_RESULTS_SCRIPT = """
function showResults() {
  var exam = JSON.parse(document.getElementById("exam-data").textContent);
  var tally = {};
  exam.questions.forEach(function (question) {
    var key = question.subject + "/" + question.topic;
    if (!tally[key]) {
      tally[key] = { correct: 0, total: 0 };
    }
    var givenAnswer = readAnswer(question);
    var correct = gradeAnswer(question, givenAnswer);
    if (correct !== null) {
      tally[key].total += 1;
      if (correct) {
        tally[key].correct += 1;
      }
    }
  });
  var lines = Object.keys(tally).map(function (key) {
    return key + ": " + tally[key].correct + "/" + tally[key].total;
  });
  document.getElementById("practice-results").textContent = lines.join(", ");
}
""".strip()


def _render_multiple_choice(question, labels):
    options_html = "".join(
        f'<label><input type="radio" name="{question["question_id"]}" value="{index}"> {html.escape(str(option))}</label>'
        for index, option in enumerate(question["options"] or [])
    )
    return f'<div data-question-id="{question["question_id"]}">{options_html}</div>'


def _render_true_false(question, labels):
    options_html = "".join(
        f'<label><input type="radio" name="{question["question_id"]}" value="{value}"> {html.escape(labels[key])}</label>'
        for value, key in (("true", "true"), ("false", "false"))
    )
    return f'<div data-question-id="{question["question_id"]}">{options_html}</div>'


def _render_fill_in_blank(question, labels):
    return f'<div data-question-id="{question["question_id"]}"><input type="text"></div>'


def _render_matching(question, labels):
    pairs = question["correct_answer"] or {}
    right_values = list(pairs.values())
    shuffled = right_values[:]
    random.shuffle(shuffled)
    placeholder = f'<option value="" selected disabled>{html.escape(labels["choose"])}</option>'
    selects_html = ""
    for left in pairs:
        options_html = placeholder + "".join(f'<option value="{html.escape(str(v))}">{html.escape(str(v))}</option>' for v in shuffled)
        selects_html += f'<label>{html.escape(str(left))} <select data-left="{html.escape(str(left))}">{options_html}</select></label>'
    return f'<div data-question-id="{question["question_id"]}">{selects_html}</div>'


def _render_open_response(question, labels):
    return f'<div data-question-id="{question["question_id"]}"><textarea></textarea></div>'


_RENDERERS = {
    "multiple_choice": _render_multiple_choice,
    "single_select": _render_multiple_choice,
    "true_false": _render_true_false,
    "fill_in_blank": _render_fill_in_blank,
    "matching": _render_matching,
    "open_response": _render_open_response,
}


def render_exam_html(exam, language="es", mode="exam"):
    if mode not in ("exam", "practice"):
        raise ValueError(f"unknown mode: {mode!r}")

    labels = _LABELS[language]
    question_blocks = []
    for question in exam["questions"]:
        if question["type"] not in QUESTION_TYPES or question["type"] not in _RENDERERS:
            raise ValueError(f"unknown question type: {question['type']!r}")
        validate_correct_answer_shape(question)
        prompt = html.escape(question["prompt"])
        question_blocks.append(f"<p>{prompt}</p>{_RENDERERS[question['type']](question, labels)}")

    questions_html = "".join(question_blocks)
    # Escape "</" so a question's own text can never prematurely close the
    # #exam-data script tag; \/ is a valid JSON escape, so json.loads still
    # round-trips to the exact original exam dict.
    exam_json = json.dumps(exam).replace("</", "<\\/")

    if mode == "practice":
        banner_html = f'<h2 id="practice-banner">{html.escape(labels["practice_banner"])}</h2>'
        action_html = f'<button onclick="showResults()">{html.escape(labels["show_results"])}</button><div id="practice-results"></div>'
        script = _SELF_GRADING_SCRIPT + "\n\n" + _PRACTICE_RESULTS_SCRIPT
        title = f'{html.escape(exam["exam_id"])} ({html.escape(labels["practice_banner"])})'
    else:
        banner_html = ""
        action_html = f'<button onclick="downloadResults()">{html.escape(labels["download"])}</button>'
        script = _SELF_GRADING_SCRIPT + "\n\n" + _DOWNLOAD_RESULTS_SCRIPT
        title = html.escape(exam["exam_id"])

    return f"""<!doctype html>
<html lang="{language}">
<head><meta charset="utf-8"><title>{title}</title></head>
<body>
<script type="application/json" id="exam-data">{exam_json}</script>
{banner_html}
{questions_html}
{action_html}
<script>{script}</script>
</body>
</html>"""
