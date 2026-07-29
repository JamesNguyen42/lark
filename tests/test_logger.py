import logging
from contextlib import contextmanager
from lark import Lark, logger
from unittest import TestCase, main, skipIf

from io import StringIO

try:
    import interegular
except ImportError:
    interegular = None

@contextmanager
def capture_log():
    stream = StringIO()
    orig_handler = logger.handlers[0]
    del logger.handlers[:]
    logger.addHandler(logging.StreamHandler(stream))
    yield stream
    del logger.handlers[:]
    logger.addHandler(orig_handler)

class Testlogger(TestCase):

    def test_debug(self):
        logger.setLevel(logging.DEBUG)
        collision_grammar = '''
        start: as as
        as: a*
        a: "a"
        '''
        with capture_log() as log:
            Lark(collision_grammar, parser='lalr', debug=True)

        log = log.getvalue()
        # since there are conflicts about A
        # symbol A should appear in the log message for hint
        self.assertIn("A", log)

    def test_non_debug(self):
        logger.setLevel(logging.WARNING)
        collision_grammar = '''
        start: as as
        as: a*
        a: "a"
        '''
        with capture_log() as log:
            Lark(collision_grammar, parser='lalr', debug=False)
        log = log.getvalue()
        # no log message
        self.assertEqual(log, "")

    def test_terminal_references_are_not_reported_as_unused(self):
        logger.setLevel(logging.DEBUG)
        grammar = r"""
        value: IDENTIFIER
        _IDENT_LETTER: "A".."Z"
        DECIMAL_DIGIT: "0".."9"
        IDENTIFIER: _IDENT_LETTER (_IDENT_LETTER | DECIMAL_DIGIT)+
        UNUSED: "unused"
        """
        with capture_log() as log:
            parser = Lark(grammar, start="value", parser="lalr", debug=True)

        self.assertEqual(str(parser.parse("E2BIG").children[0]), "E2BIG")
        log = log.getvalue()
        self.assertIn("UNUSED", log)
        self.assertNotIn("_IDENT_LETTER", log)
        self.assertNotIn("DECIMAL_DIGIT", log)

    def test_terminal_reference_tracking_respects_override_and_extend(self):
        logger.setLevel(logging.DEBUG)
        cases = [
            (
                """
                start: COMPOSITE
                FRAGMENT: "fragment"
                COMPOSITE: FRAGMENT
                %override COMPOSITE: "composite"
                """,
                "FRAGMENT",
            ),
            (
                """
                start: COMPOSITE
                FRAGMENT: "fragment"
                COMPOSITE: "composite"
                %extend COMPOSITE: FRAGMENT
                """,
                None,
            ),
        ]

        for grammar, expected_unused in cases:
            with self.subTest(expected_unused=expected_unused), capture_log() as log:
                Lark(grammar, parser="lalr", debug=True)

            if expected_unused is None:
                self.assertEqual(log.getvalue(), "")
            else:
                self.assertIn(expected_unused, log.getvalue())

    def test_loglevel_higher(self):
        logger.setLevel(logging.ERROR)
        collision_grammar = '''
        start: as as
        as: a*
        a: "a"
        '''
        with capture_log() as log:
            Lark(collision_grammar, parser='lalr', debug=True)
        log = log.getvalue()
        # no log message
        self.assertEqual(len(log), 0)

    @skipIf(interegular is None, "interegular is not installed, can't test regex collisions")
    def test_regex_collision(self):
        logger.setLevel(logging.WARNING)
        collision_grammar = '''
        start: A | B
        A: /a+/
        B: /(a|b)+/
        '''
        with capture_log() as log:
            Lark(collision_grammar, parser='lalr')

        log = log.getvalue()
        # since there are conflicts between A and B
        # symbols A and B should appear in the log message
        self.assertIn("A", log)
        self.assertIn("B", log)

    @skipIf(interegular is None, "interegular is not installed, can't test regex collisions")
    def test_no_regex_collision(self):
        logger.setLevel(logging.WARNING)
        collision_grammar = '''
        start: A " " B
        A: /a+/
        B: /(a|b)+/
        '''
        with capture_log() as log:
            Lark(collision_grammar, parser='lalr')

        log = log.getvalue()
        self.assertEqual(log, "")


if __name__ == '__main__':
    main()
