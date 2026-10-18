import html
import json

from scripts.exam_schema import QUESTION_TYPES

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
  return checked ? checked.value : null;
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


def _render_multiple_choice(question):
    options_html = "".join(
        f'<label><input type="radio" name="{question["question_id"]}" value="{html.escape(str(option))}"> {html.escape(str(option))}</label>'
        for option in (question["options"] or [])
    )
    return f'<div data-question-id="{question["question_id"]}">{options_html}</div>'


def _render_true_false(question):
    options_html = "".join(
        f'<label><input type="radio" name="{question["question_id"]}" value="{value}"> {label}</label>'
        for value, label in (("true", "True"), ("false", "False"))
    )
    return f'<div data-question-id="{question["question_id"]}">{options_html}</div>'


def _render_fill_in_blank(question):
    return f'<div data-question-id="{question["question_id"]}"><input type="text"></div>'


def _render_matching(question):
    pairs = question["correct_answer"] or {}
    right_values = list(pairs.values())
    selects_html = ""
    for left in pairs:
        options_html = "".join(f'<option value="{html.escape(str(v))}">{html.escape(str(v))}</option>' for v in right_values)
        selects_html += f'<label>{html.escape(str(left))} <select data-left="{html.escape(str(left))}">{options_html}</select></label>'
    return f'<div data-question-id="{question["question_id"]}">{selects_html}</div>'


def _render_open_response(question):
    return f'<div data-question-id="{question["question_id"]}"><textarea></textarea></div>'


_RENDERERS = {
    "multiple_choice": _render_multiple_choice,
    "single_select": _render_multiple_choice,
    "true_false": _render_true_false,
    "fill_in_blank": _render_fill_in_blank,
    "matching": _render_matching,
    "open_response": _render_open_response,
}


def render_exam_html(exam):
    question_blocks = []
    for question in exam["questions"]:
        if question["type"] not in QUESTION_TYPES or question["type"] not in _RENDERERS:
            raise ValueError(f"unknown question type: {question['type']!r}")
        prompt = html.escape(question["prompt"])
        question_blocks.append(f"<p>{prompt}</p>{_RENDERERS[question['type']](question)}")

    questions_html = "".join(question_blocks)
    exam_json = json.dumps(exam)

    return f"""<!doctype html>
<html>
<head><meta charset="utf-8"><title>{html.escape(exam["exam_id"])}</title></head>
<body>
<script type="application/json" id="exam-data">{exam_json}</script>
{questions_html}
<button onclick="downloadResults()">Download results</button>
<script>{_SELF_GRADING_SCRIPT}</script>
</body>
</html>"""
