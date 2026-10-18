QUESTION_TYPES = {"multiple_choice", "single_select", "true_false", "fill_in_blank", "matching", "open_response"}


def validate_correct_answer_shape(question):
    type_ = question["type"]
    correct_answer = question["correct_answer"]

    if type_ == "fill_in_blank" and not isinstance(correct_answer, list):
        raise ValueError(f"fill_in_blank correct_answer must be a list, got {correct_answer!r}")
    if type_ == "matching" and not isinstance(correct_answer, dict):
        raise ValueError(f"matching correct_answer must be a dict, got {correct_answer!r}")
    if type_ == "true_false" and not isinstance(correct_answer, bool):
        raise ValueError(f"true_false correct_answer must be a bool, got {correct_answer!r}")
    if type_ in ("multiple_choice", "single_select") and question["options"] is not None and correct_answer not in question["options"]:
        raise ValueError(f"correct_answer {correct_answer!r} is not among options {question['options']!r}")


def make_question(question_id, type, subject, topic, prompt, options=None, correct_answer=None, competency=None):
    if type not in QUESTION_TYPES:
        raise ValueError(f"unknown question type: {type!r}")

    question = {
        "question_id": question_id,
        "type": type,
        "subject": subject,
        "topic": topic,
        "competency": competency,
        "prompt": prompt,
        "options": options,
        "correct_answer": correct_answer,
    }
    validate_correct_answer_shape(question)
    return question


def make_exam(exam_id, child_id, subject, topic, grade, questions):
    if not questions:
        raise ValueError("an exam must have at least one question")

    return {
        "exam_id": exam_id,
        "child_id": child_id,
        "subject": subject,
        "topic": topic,
        "grade": grade,
        "questions": questions,
    }
