import ast
from pathlib import Path
import re
import unittest
from typing import Any


PARSER_PATH = Path(__file__).resolve().parents[1] / "scripts/parse_board_textvqa_pilot.py"
SAFE_NON_LABEL_METADATA_KEYS = {"answerparseok"}


def production_helpers():
    """Compile only the production helper definitions needed by these tests."""
    tree = ast.parse(PARSER_PATH.read_text(encoding="utf-8"), filename=str(PARSER_PATH))
    wanted = {"has_label_keys", "qid_matches"}
    functions = [node for node in tree.body
                 if isinstance(node, ast.FunctionDef) and node.name in wanted]
    if {node.name for node in functions} != wanted:
        raise AssertionError("required production helper is missing")
    module = ast.fix_missing_locations(ast.Module(body=functions, type_ignores=[]))
    namespace = {
        "Any": Any,
        "re": re,
        "SAFE_NON_LABEL_METADATA_KEYS": SAFE_NON_LABEL_METADATA_KEYS,
    }
    exec(compile(module, str(PARSER_PATH), "exec"), namespace)
    return namespace["has_label_keys"], namespace["qid_matches"]


HAS_LABEL_KEYS, QID_MATCHES = production_helpers()


class ParserLabelQidContractTests(unittest.TestCase):
    def test_answer_parse_ok_accepts_only_json_booleans(self):
        self.assertFalse(HAS_LABEL_KEYS({"answer_parse_ok": True}))
        self.assertFalse(HAS_LABEL_KEYS({"answer_parse_ok": False}))
        for value in ("true", "false", 1, 0, None, [], {}):
            with self.subTest(value=value):
                self.assertTrue(HAS_LABEL_KEYS({"answer_parse_ok": value}))

    def test_nested_label_keys_remain_rejected(self):
        self.assertTrue(HAS_LABEL_KEYS({"metadata": {"reference_answers": []}}))
        self.assertTrue(HAS_LABEL_KEYS([{"nested": {"gold_response": "x"}}]))
        self.assertTrue(HAS_LABEL_KEYS({"answer_parse_ok": True, "extra": {"label": "x"}}))

    def test_integer_qid_matches(self):
        self.assertTrue(QID_MATCHES(38299, 38299))
        self.assertFalse(QID_MATCHES(38299, 37804))

    def test_float_equal_qid_is_rejected(self):
        self.assertFalse(QID_MATCHES(38299.0, 38299))

    def test_boolean_qid_is_rejected_as_integer(self):
        self.assertFalse(QID_MATCHES(True, 1))
        self.assertFalse(QID_MATCHES(False, 0))

    def test_all_json_question_id_reads_are_guarded_by_strict_helper(self):
        tree = ast.parse(PARSER_PATH.read_text(encoding="utf-8"), filename=str(PARSER_PATH))
        qid_reads = []
        strict_calls = []
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and
                    node.func.id == "qid_matches"):
                strict_calls.append(node)
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and
                    node.func.attr == "get" and node.args and
                    isinstance(node.args[0], ast.Constant) and
                    node.args[0].value == "question_id"):
                qid_reads.append(node)
            if (isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant) and
                    node.slice.value == "question_id"):
                qid_reads.append(node)

        self.assertTrue(qid_reads, "expected parser JSON question_id reads")
        guarded_ids = {id(child) for call in strict_calls for child in ast.walk(call)}
        unguarded = [read for read in qid_reads if id(read) not in guarded_ids]
        self.assertEqual(unguarded, [], "JSON question_id read bypasses qid_matches")


if __name__ == "__main__":
    unittest.main()
